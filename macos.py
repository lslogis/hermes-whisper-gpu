"""macOS: transcribe on a local MLX server; faster-whisper has no Metal backend.

Registers the STT provider `whisper-gpu`: audio goes to an OpenAI-compatible /audio/transcriptions endpoint (e.g. oMLX)
and falls back to Hermes' CPU Whisper when the server is unreachable.
"""
import json, urllib.request, uuid
from pathlib import Path
from urllib.parse import urlparse


def _provider(url, default_model):
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
    ctx.register_transcription_provider(_provider(ctx.get_config("endpoint", "http://127.0.0.1:8000/v1"),
                                                  ctx.get_config("whisper_model", "whisper-large-v3-turbo")))
