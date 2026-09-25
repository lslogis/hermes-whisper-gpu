# macOS에서 whisper-gpu 쓰기

[English](MACOS.md) · **한국어** · [日本語](MACOS.ja.md)

Hermes의 로컬 Whisper는 faster-whisper인데, Metal 백엔드가 없어서 Mac에서는 항상 CPU로 돕니다. 이 플러그인은 음성
인식 공급자 `whisper-gpu`를 등록합니다. 음성을 Mac GPU에서 도는 **로컬 MLX 서버**로 보내고, 서버에 연결할 수 없으면
Hermes의 CPU Whisper로 대신 처리합니다.

Apple silicon(M1 이상)이 필요합니다. Intel Mac에서는 MLX가 돌지 않습니다. M4 Max와 `whisper-large-v3-turbo`로 측정한 값은
클립 하나당 CPU 약 4초, MLX 0.3초입니다.

## 1. 로컬 MLX 서버

OpenAI 호환 `POST /v1/audio/transcriptions`를 제공하는 서버면 무엇이든 됩니다. [oMLX](https://github.com/jundot/omlx)에
[`mlx-community/whisper-large-v3-turbo`](https://huggingface.co/mlx-community/whisper-large-v3-turbo)를 oMLX 모델 폴더
(`~/.omlx/models/mlx-community/whisper-large-v3-turbo`)에 넣어서 시험했습니다.

이 MLX 변환본에는 프로세서와 토크나이저 파일이 빠져 있어서 oMLX가 불러오지 못합니다.
[`openai/whisper-large-v3-turbo`](https://huggingface.co/openai/whisper-large-v3-turbo)에서 다음 파일을 같은 폴더로
복사하세요: `preprocessor_config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`,
`vocab.json`, `merges.txt`, `added_tokens.json`, `normalizer.json`, `generation_config.json`.

확인:

```
curl http://127.0.0.1:8000/v1/audio/transcriptions -F model=whisper-large-v3-turbo -F file=@clip.mp3
```

서버가 모델을 하나만 올려 두도록 제한되어 있다면, 그 제한이 음성 모델은 세지 않게 하세요. 그렇지 않으면 음성을 인식할
때마다 대화 모델이 내려갑니다.

## 2. Hermes 연결

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
hermes config set stt.provider whisper-gpu
```

기본값입니다. 사용하는 환경과 다를 때만 바꾸세요.

```
hermes config set plugins.entries.whisper-gpu.settings.endpoint http://127.0.0.1:8000/v1
hermes config set plugins.entries.whisper-gpu.settings.whisper_model whisper-large-v3-turbo
```

대체 처리용 CPU 모델도 설정해 두세요: `hermes config set stt.local.model large-v3-turbo`.

## 동작

- MLX 서버가 응답하면 결과의 `provider`는 `whisper-gpu`이고, 대체 처리했으면 `local`입니다. 대체 처리한 결과에는
  `fallback_reason`(예: `Connection refused`)이 붙습니다.
- 엔드포인트는 루프백(`127.0.0.1`, `localhost`, `::1`)이나 `https://`여야 합니다. 다른 호스트로 가는 평문 HTTP는
  플러그인을 불러올 때 거부하므로, 음성이 암호화되지 않은 채 네트워크를 지나가지 않습니다.
- MLX 변환본은 CPU 모델과 문장부호나 띄어쓰기가 다를 수 있습니다(예: "헤르메스에요"와 "헤르메스예요").
