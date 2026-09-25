# whisper-gpu — Hermes plugin

GPU speech-to-text for [Hermes Agent](https://github.com/NousResearch/hermes-agent)'s local Whisper, on Windows
and macOS, kept working across Hermes updates.

| | Without | With |
|---|---|---|
| Windows, RTX 5080, `large-v3-turbo` (5 Korean clips) | CPU 20.4 s | CUDA 1.1 s |
| macOS, M4 Max, `large-v3-turbo` (one clip) | CPU ≈4 s | MLX 0.3 s |

## Windows

`ctranslate2` (faster-whisper's engine) ships Windows wheels built for **CUDA 12** and loads every DLL in its own
package folder. A PC with only CUDA 13, or no toolkit, has no `cublas64_12.dll` / `cudnn64_9.dll`, so Hermes falls
back to CPU without saying so. Hermes updates rebuild the venv and remove any DLLs copied in by hand.

- On `on_session_start` the plugin checks the three DLLs next to `ctranslate2` and installs any that are missing in
  a background thread. They take effect on the next Hermes start.
- `hermes whisper-gpu` shows the status; `hermes whisper-gpu install` installs now.

```
hermes pm install --extra voice
hermes config set stt.local.model large-v3-turbo
hermes config set stt.local.device auto
hermes config set stt.local.compute_type int8_float16
hermes config set stt.local.unload_after_idle_seconds 300
```

## macOS

faster-whisper has no Metal backend. The plugin registers the STT provider `whisper-gpu`, which sends audio to a
local MLX server's OpenAI-compatible `/audio/transcriptions` (tested with [oMLX](https://github.com/jundot/omlx) and
`mlx-community/whisper-large-v3-turbo`). If the server is unreachable it falls back to Hermes' built-in CPU Whisper
and reports `fallback_reason`.

```
hermes config set stt.provider whisper-gpu
hermes config set plugins.entries.whisper-gpu.settings.endpoint http://127.0.0.1:8000/v1   # default
hermes config set plugins.entries.whisper-gpu.settings.whisper_model whisper-large-v3-turbo # default
```

oMLX note: MLX Whisper conversions may lack the processor files. Copy `preprocessor_config.json`, `tokenizer.json`,
`tokenizer_config.json`, `special_tokens_map.json`, `vocab.json`, `merges.txt`, `added_tokens.json`,
`normalizer.json` and `generation_config.json` from `openai/whisper-large-v3-turbo` into the model folder.

## Install

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
```

## Security

- **Pinned sources (Windows).** DLLs come only from two NVIDIA wheels on PyPI, pinned by exact URL
  (`nvidia-cublas-cu12 12.9.2.10`, `nvidia-cudnn-cu12 9.26.0.51`) and **SHA-256**. A wheel that does not match is
  deleted and nothing is installed. Wheels are cached in `<HERMES_HOME>/cache/whisper-gpu` (≈1.3 GB).
- **No path from the archive is trusted.** Only `cublas*64_12.dll` and `cudnn*64_9.dll` are extracted, by basename,
  into the `ctranslate2` folder (no zip-slip). Existing DLLs are never overwritten.
- **Audio stays local (macOS).** The endpoint must be loopback or `https://`; anything else is refused at load.
- HTTPS downloads only, no shell or subprocess, no credentials, no telemetry, standard library only.

To move to newer NVIDIA wheels, update `WHEELS` in `__init__.py` with the URL and `sha256` from
`https://pypi.org/pypi/<package>/<version>/json`.

## License

MIT. The NVIDIA libraries it downloads are covered by NVIDIA's own license terms.
