"""Windows: keep faster-whisper on CUDA across Hermes updates.

ctranslate2 is built for CUDA 12 and preloads every DLL in its own folder. Without cuBLAS 12 / cuDNN 9 Hermes silently
falls back to CPU, and every Hermes update rebuilds the venv. The DLLs are restored from NVIDIA's PyPI wheels, pinned
and SHA-256 verified.
"""
import hashlib, importlib.util, logging, threading, urllib.request, zipfile
from pathlib import Path

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


def register(ctx):
    # Plugins load before the first transcription imports ctranslate2, so DLLs restored here are used without a
    # restart. Cached wheels restore in seconds; a first-time download runs in the background.
    if missing():
        if all(_cache(url).exists() for url, *_ in WHEELS):
            _restore()
        else:
            threading.Thread(target=_restore, daemon=True).start()
    ctx.register_cli_command(name="whisper-gpu", help="GPU speech-to-text DLLs (status / install)",
                             setup_fn=_setup, handler_fn=_cli)
