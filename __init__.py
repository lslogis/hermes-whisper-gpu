"""GPU speech-to-text for Hermes' local Whisper.

Windows: ctranslate2 (faster-whisper) is built for CUDA 12 and preloads every DLL in its own folder. Without cuBLAS 12 /
cuDNN 9 Hermes silently falls back to CPU, and every Hermes update rebuilds the venv. The DLLs are restored from NVIDIA's
PyPI wheels, pinned and SHA-256 verified.
macOS: faster-whisper has no Metal backend, so transcription goes to a local MLX server (OpenAI-compatible
/audio/transcriptions, e.g. oMLX) and falls back to Hermes' CPU Whisper when the server is unreachable.
"""
import hashlib, importlib.util, json, logging, sys, threading, urllib.request, uuid, zipfile
from pathlib import Path
from urllib.parse import urlparse

PYPI = "https://files.pythonhosted.org/packages/"
WHEELS = (  # (url, sha256, DLL name prefix, DLL name suffix)
    (PYPI + "20/e2/fc9a0e985249d873150276d5afb02e39a66817fedbf1a385724393e505ed/"
     "nvidia_cublas_cu12-12.9.2.10-py3-none-win_amd64.whl",
     "623f43027d40d44ceadf0043f002bd25cf353e8f13ce90b9a87057019f560661", "cublas", "64_12.dll"),
    (PYPI + "c5/ee/baebebf270df5a57830e40879b4016de47ca43961095cf18b7749452150f/"
     "nvidia_cudnn_cu12-9.26.0.51-py3-none-win_amd64.whl",
     "010abb90f513fc6e2b6e9278d56f594b87922fff80737434ab415da609db8311", "cudnn", "64_9.dll"),
)
NEEDED = ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll")
_lock = threading.Lock()


def _target():
    spec = importlib.util.find_spec("ctranslate2")
    return Path(spec.origin).parent if spec and spec.origin else None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _cache(url):
    from hermes_constants import get_hermes_home
    return get_hermes_home() / "cache" / "whisper-gpu" / url.rsplit("/", 1)[1]


def _wheel(url, sha):
    path = _cache(url)
    if path.exists() and _sha256(path) == sha:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        while block := r.read(1 << 20):
            f.write(block)
    if _sha256(part) != sha:
        part.unlink()
        raise RuntimeError(f"SHA-256 mismatch for {path.name}; nothing installed")
    part.replace(path)
    return path


def missing():
    t = _target()
    return None if t is None else [n for n in NEEDED if not (t / n).exists()]


def install():
    t = _target()
    if t is None:
        return "ctranslate2 not installed: run `hermes pm install --extra voice` first"
    with _lock:
        for url, sha, prefix, suffix in WHEELS:
            with zipfile.ZipFile(_wheel(url, sha)) as z:
                for info in z.infolist():
                    name = info.filename.rsplit("/", 1)[-1]  # basename only: no path from the archive is used
                    if name.startswith(prefix) and name.endswith(suffix) and not (t / name).exists():
                        (t / name).write_bytes(z.read(info))
    return f"GPU DLLs installed in {t}"


def _restore():
    try:
        install()
    except Exception as e:
        logging.getLogger(__name__).warning("whisper-gpu: restore failed: %s", e)


def _cli(args):
    if args.whisper_gpu == "install":
        print(install())
    else:
        m = missing()
        print("ctranslate2 not installed" if m is None else f"missing: {', '.join(m)}" if m else "ok: GPU DLLs present")


def _setup(parser):
    parser.add_subparsers(dest="whisper_gpu").add_parser("install", help="download (verified) and install the DLLs")
    parser.set_defaults(func=_cli)


def _mlx_provider(url, default_model):
    from agent.transcription_provider import TranscriptionProvider
    if urlparse(url).hostname not in ("127.0.0.1", "localhost", "::1") and not url.startswith("https://"):
        raise ValueError(f"whisper-gpu: {url} must be loopback or https (audio would travel in clear text)")

    class MLXServer(TranscriptionProvider):
        name = "whisper-gpu"

        def transcribe(self, file_path, *, model=None, language=None, **extra):
            b = uuid.uuid4().hex
            fields = {"model": model or default_model, **({"language": language} if language else {})}
            body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                            for k, v in fields.items())
            body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="audio{Path(file_path).suffix}"'
                     f"\r\n\r\n").encode() + Path(file_path).read_bytes() + f"\r\n--{b}--\r\n".encode()
            req = urllib.request.Request(url.rstrip("/") + "/audio/transcriptions", body,
                                         {"Content-Type": f"multipart/form-data; boundary={b}"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return {"success": True, "transcript": json.loads(r.read())["text"].strip(), "provider": self.name}
            except Exception as e:
                from tools.transcription_tools import transcribe_audio_local_fallback
                return {**transcribe_audio_local_fallback(file_path), "fallback_reason": str(e)[:200]}

    return MLXServer()


def register(ctx):
    # Plugins load before the first transcription imports ctranslate2, so DLLs restored here are used without a
    # restart. Cached wheels restore in seconds; a first-time download runs in the background.
    if sys.platform == "win32":
        if missing():
            if all(_cache(url).exists() for url, *_ in WHEELS):
                _restore()
            else:
                threading.Thread(target=_restore, daemon=True).start()
        ctx.register_cli_command(name="whisper-gpu", help="GPU speech-to-text DLLs (status / install)",
                                 setup_fn=_setup, handler_fn=_cli)
    elif sys.platform == "darwin":
        ctx.register_transcription_provider(_mlx_provider(ctx.get_config("endpoint", "http://127.0.0.1:8000/v1"),
                                                          ctx.get_config("whisper_model", "whisper-large-v3-turbo")))
