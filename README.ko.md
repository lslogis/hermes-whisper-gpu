# whisper-gpu — Hermes 플러그인

[English](README.md) · **한국어** · [日本語](README.ja.md)

[Hermes Agent](https://github.com/NousResearch/hermes-agent)의 로컬 Whisper 음성 인식을 GPU로 돌리고, Hermes를
업데이트해도 그 상태를 유지합니다. 플러그인 하나로 두 플랫폼을 지원합니다.

## 요구 사항

| | 필요한 것 |
|---|---|
| **Windows** (64비트) | CUDA 12를 지원하는 드라이버(528.33 이상)가 설치된 NVIDIA GPU. CUDA 툴킷이나 cuDNN은 따로 설치하지 않아도 됩니다. |
| **macOS** | Apple silicon(M1 이상)과 Whisper 모델을 올린 로컬 MLX 서버. [MACOS.ko.md](MACOS.ko.md) 참고. Intel Mac에서는 MLX가 돌지 않습니다. |

Linux, NVIDIA 드라이버가 없는 Windows, Intel Mac에서는 아무 동작도 하지 않습니다.

Windows에서는 GPU 세대에 맞춰 `compute_type`을 고르세요([CTranslate2](https://opennmt.net/CTranslate2/quantization.html)).
`int8_float16`과 `float16`은 compute capability 7.0 이상(GTX 16 / RTX 20 시리즈 이후)이 필요합니다. 6.1(GTX 10
시리즈)이면 `int8`을 쓰세요. CTranslate2가 지원되는 형식으로 알아서 바꾸므로 `auto`는 언제나 안전합니다.

측정값(`large-v3-turbo`, 한국어 음성):

| 기기 | 플러그인 없이 | 플러그인 사용 |
|---|---|---|
| Windows, RTX 5080, 클립 5개 | CPU 20.4초 | CUDA 1.1초 |
| macOS, M4 Max, 클립 1개 | CPU 약 4초 | MLX 0.3초 |

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
```

| 파일 | 역할 |
|---|---|
| `__init__.py` | `windows.py`나 `macos.py` 중 하나만 불러옵니다. 다른 OS에서는 아무것도 실행하지 않습니다 |
| `windows.py` | faster-whisper에 필요한 CUDA 12 DLL을 복구합니다 |
| `macos.py` | 음성을 로컬 MLX 서버로 보내고, 실패하면 CPU로 대체합니다. [MACOS.ko.md](MACOS.ko.md) 참고 |

## Windows

faster-whisper의 엔진인 `ctranslate2`의 Windows 휠은 **CUDA 12**용으로 빌드되어 있고, 자기 패키지 폴더에 있는 DLL을
모두 불러옵니다. CUDA 13만 있거나 툴킷이 없는 PC에는 `cublas64_12.dll` / `cudnn64_9.dll`이 없어서, Hermes는 아무
안내 없이 CPU로 돌아갑니다. 게다가 Hermes를 업데이트하면 venv가 새로 만들어져 손으로 복사해 둔 DLL이 사라집니다.

- Hermes가 플러그인을 불러올 때 `ctranslate2` 옆의 DLL 세 개를 확인하고, 없는 것을 복구합니다. 플러그인은 첫 음성
  인식이 `ctranslate2`를 불러오기 전에 로드되므로 재시작이 필요 없습니다. 검증된 휠 캐시가 있으면 몇 초면 끝나고,
  처음 받는 경우(약 1.3GB)에는 백그라운드에서 내려받습니다.
- `hermes whisper-gpu`는 상태를 보여 주고, `hermes whisper-gpu install`은 바로 설치합니다.

```
hermes pm install --extra voice
hermes config set stt.local.model large-v3-turbo
hermes config set stt.local.device auto
hermes config set stt.local.compute_type int8_float16
hermes config set stt.local.unload_after_idle_seconds 300
```

## 보안

- **출처 고정.** DLL은 PyPI에 있는 NVIDIA 휠 두 개에서만 가져오며, 정확한 URL(`nvidia-cublas-cu12 12.9.2.10`,
  `nvidia-cudnn-cu12 9.26.0.51`)과 **SHA-256**으로 고정되어 있습니다. 해시가 맞지 않는 휠은 지우고 아무것도 설치하지
  않습니다. 휠은 `<HERMES_HOME>/cache/whisper-gpu`에 캐시됩니다(약 1.3GB).
- **압축 파일 안의 경로를 믿지 않습니다.** `cublas*64_12.dll`과 `cudnn*64_9.dll`만 파일 이름 그대로 `ctranslate2` 폴더에
  풀어 넣습니다(zip-slip 방지). 이미 있는 DLL은 덮어쓰지 않습니다.
- **음성은 로컬에 머뭅니다(macOS).** 엔드포인트는 루프백이나 `https://`여야 하며, 그 밖의 주소는 로드할 때 거부합니다.
- HTTPS 다운로드만 사용하고, 셸이나 subprocess, 인증 정보, 원격 측정이 없으며, 표준 라이브러리만 씁니다.

더 새로운 NVIDIA 휠로 바꾸려면 `windows.py`의 `WHEELS`를 `https://pypi.org/pypi/<package>/<version>/json`에 나온 URL과
`sha256`으로 바꾸세요.

## 라이선스

MIT. 플러그인이 내려받는 NVIDIA 라이브러리에는 NVIDIA의 라이선스 조건이 적용됩니다.
