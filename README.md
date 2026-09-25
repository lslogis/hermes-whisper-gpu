# whisper-gpu — Hermes plugin

GPU speech-to-text for [Hermes Agent](https://github.com/NousResearch/hermes-agent)'s local Whisper, kept working
across Hermes updates. One plugin, two platforms:

| | Without | With |
|---|---|---|
| Windows, RTX 5080, `large-v3-turbo`, 5 Korean clips | CPU 20.4 s | CUDA 1.1 s |
| macOS, M4 Max, `large-v3-turbo`, one clip ([MACOS.md](MACOS.md)) | CPU ≈4 s | MLX 0.3 s |

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
```

| File | Role |
|---|---|
| `__init__.py` | Loads `windows.py` or `macos.py`; nothing runs on other systems |
| `windows.py` | Restores the CUDA 12 DLLs faster-whisper needs |
| `macos.py` | Sends audio to a local MLX server, CPU fallback — see [MACOS.md](MACOS.md) |

## Windows

`ctranslate2` (faster-whisper's engine) ships Windows wheels built for **CUDA 12** and loads every DLL in its own
package folder. A PC with only CUDA 13, or no toolkit, has no `cublas64_12.dll` / `cudnn64_9.dll`, so Hermes falls
back to CPU without saying so. Hermes updates rebuild the venv and remove any DLLs copied in by hand.

- When Hermes loads the plugin it checks the three DLLs next to `ctranslate2` and restores any that are missing.
  Plugins load before the first transcription imports `ctranslate2`, so no restart is needed: from the verified
  wheel cache this takes a few seconds; a first-time download (≈1.3 GB) runs in the background.
- `hermes whisper-gpu` shows the status; `hermes whisper-gpu install` installs now.

```
hermes pm install --extra voice
hermes config set stt.local.model large-v3-turbo
hermes config set stt.local.device auto
hermes config set stt.local.compute_type int8_float16
hermes config set stt.local.unload_after_idle_seconds 300
```

## Security

- **Pinned sources.** DLLs come only from two NVIDIA wheels on PyPI, pinned by exact URL
  (`nvidia-cublas-cu12 12.9.2.10`, `nvidia-cudnn-cu12 9.26.0.51`) and **SHA-256**. A wheel that does not match is
  deleted and nothing is installed. Wheels are cached in `<HERMES_HOME>/cache/whisper-gpu` (≈1.3 GB).
- **No path from the archive is trusted.** Only `cublas*64_12.dll` and `cudnn*64_9.dll` are extracted, by basename,
  into the `ctranslate2` folder (no zip-slip). Existing DLLs are never overwritten.
- **Audio stays local (macOS).** The endpoint must be loopback or `https://`; anything else is refused at load.
- HTTPS downloads only, no shell or subprocess, no credentials, no telemetry, standard library only.

To move to newer NVIDIA wheels, update `WHEELS` in `windows.py` with the URL and `sha256` from
`https://pypi.org/pypi/<package>/<version>/json`.

## License

MIT. The NVIDIA libraries it downloads are covered by NVIDIA's own license terms.
