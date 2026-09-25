# whisper-gpu on macOS

**English** · [한국어](MACOS.ko.md) · [日本語](MACOS.ja.md)

Hermes' local Whisper is faster-whisper, which has no Metal backend, so on a Mac it always runs on the CPU. This
plugin registers the speech-to-text provider `whisper-gpu`, which sends audio to a **local MLX server** on the Mac's
GPU and falls back to Hermes' CPU Whisper when that server is unreachable.

Needs Apple silicon (M1 or later; MLX does not run on Intel Macs). Measured on an M4 Max with
`whisper-large-v3-turbo`: CPU ≈4 s per clip, MLX 0.3 s.

## 1. A local MLX server

Any server with an OpenAI-compatible `POST /v1/audio/transcriptions` works. Tested with
[oMLX](https://github.com/jundot/omlx) and
[`mlx-community/whisper-large-v3-turbo`](https://huggingface.co/mlx-community/whisper-large-v3-turbo) placed in the
oMLX model folder (`~/.omlx/models/mlx-community/whisper-large-v3-turbo`).

That MLX conversion ships without the processor and tokenizer files, and oMLX refuses to load it. Copy these from
[`openai/whisper-large-v3-turbo`](https://huggingface.co/openai/whisper-large-v3-turbo) into the same folder:
`preprocessor_config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `vocab.json`,
`merges.txt`, `added_tokens.json`, `normalizer.json`, `generation_config.json`.

Check it:

```
curl http://127.0.0.1:8000/v1/audio/transcriptions -F model=whisper-large-v3-turbo -F file=@clip.mp3
```

If your server keeps only one model resident, make sure that cap does not count audio models. Otherwise every
transcription evicts your chat model.

## 2. Point Hermes at it

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
hermes config set stt.provider whisper-gpu
```

Defaults, change only if yours differ:

```
hermes config set plugins.entries.whisper-gpu.settings.endpoint http://127.0.0.1:8000/v1
hermes config set plugins.entries.whisper-gpu.settings.whisper_model whisper-large-v3-turbo
```

Keep a CPU model for the fallback: `hermes config set stt.local.model large-v3-turbo`.

## Behaviour

- Result `provider` is `whisper-gpu` when the MLX server answered, `local` when it fell back; a fallback carries
  `fallback_reason` (for example `Connection refused`).
- The endpoint must be loopback (`127.0.0.1`, `localhost`, `::1`) or `https://`. Plain HTTP to another host is
  refused when the plugin loads, so audio never crosses the network unencrypted.
- The MLX conversion may differ from the CPU model in punctuation and spacing (e.g. "헤르메스에요" vs "헤르메스예요").
