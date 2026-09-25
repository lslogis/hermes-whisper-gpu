# whisper-gpu — Hermes プラグイン

[English](README.md) · [한국어](README.ko.md) · **日本語**

[Hermes Agent](https://github.com/NousResearch/hermes-agent) のローカル Whisper 音声認識を GPU で動かし、Hermes を
アップデートしてもその状態を保ちます。1 つのプラグインで 2 つのプラットフォームに対応します。

## 動作要件

| | 必要なもの |
|---|---|
| **Windows**(64 ビット) | CUDA 12 対応ドライバー(528.33 以降)が入った NVIDIA GPU。CUDA Toolkit や cuDNN を別途インストールする必要はありません。 |
| **macOS** | Apple シリコン(M1 以降)と、Whisper モデルを載せたローカル MLX サーバー。[MACOS.ja.md](MACOS.ja.md) を参照。Intel Mac では MLX が動きません。 |

Linux、NVIDIA ドライバーのない Windows、Intel Mac では何もしません。

Windows では GPU の世代に合わせて `compute_type` を選んでください([CTranslate2](https://opennmt.net/CTranslate2/quantization.html))。
`int8_float16` と `float16` には compute capability 7.0 以上(GTX 16 / RTX 20 シリーズ以降)が必要です。6.1(GTX 10
シリーズ)なら `int8` を使ってください。CTranslate2 は対応する型に自動で切り替えるので、`auto` なら常に安全です。

実測値(`large-v3-turbo`、韓国語の音声):

| マシン | プラグインなし | プラグインあり |
|---|---|---|
| Windows、RTX 5080、クリップ 5 本 | CPU 20.4 秒 | CUDA 1.1 秒 |
| macOS、M4 Max、クリップ 1 本 | CPU 約 4 秒 | MLX 0.3 秒 |

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
```

| ファイル | 役割 |
|---|---|
| `__init__.py` | `windows.py` か `macos.py` のどちらか一方だけを読み込みます。ほかの OS では何も実行しません |
| `windows.py` | faster-whisper が必要とする CUDA 12 の DLL を復元します |
| `macos.py` | 音声をローカル MLX サーバーに送り、失敗したら CPU で代行します。[MACOS.ja.md](MACOS.ja.md) を参照 |

## Windows

faster-whisper のエンジンである `ctranslate2` の Windows 版ホイールは **CUDA 12** 向けにビルドされており、自分のパッケージ
フォルダーにある DLL をすべて読み込みます。CUDA 13 しかない PC や Toolkit のない PC には `cublas64_12.dll` /
`cudnn64_9.dll` がないため、Hermes は何も知らせずに CPU で動きます。さらに Hermes をアップデートすると venv が作り直され、
手でコピーした DLL は消えます。

- Hermes がプラグインを読み込むときに `ctranslate2` の隣にある 3 つの DLL を確認し、足りないものを復元します。プラグインは
  最初の音声認識が `ctranslate2` を読み込む前にロードされるので、再起動は不要です。検証済みのホイールキャッシュがあれば
  数秒で終わり、初回のダウンロード(約 1.3GB)はバックグラウンドで行います。
- `hermes whisper-gpu` で状態を表示し、`hermes whisper-gpu install` ですぐにインストールします。

```
hermes pm install --extra voice
hermes config set stt.local.model large-v3-turbo
hermes config set stt.local.device auto
hermes config set stt.local.compute_type int8_float16
hermes config set stt.local.unload_after_idle_seconds 300
```

## セキュリティ

- **取得元を固定。** DLL は PyPI 上の NVIDIA ホイール 2 つからだけ取得し、正確な URL(`nvidia-cublas-cu12 12.9.2.10`、
  `nvidia-cudnn-cu12 9.26.0.51`)と **SHA-256** で固定しています。ハッシュが一致しないホイールは削除し、何もインストール
  しません。ホイールは `<HERMES_HOME>/cache/whisper-gpu` にキャッシュされます(約 1.3GB)。
- **アーカイブ内のパスは信用しません。** `cublas*64_12.dll` と `cudnn*64_9.dll` だけを、ファイル名のまま `ctranslate2`
  フォルダーに展開します(zip-slip 対策)。既存の DLL は上書きしません。
- **音声はローカルに留まります(macOS)。** エンドポイントはループバックか `https://` でなければならず、それ以外は
  ロード時に拒否します。
- HTTPS ダウンロードのみを使い、シェルや subprocess、認証情報、テレメトリーはなく、標準ライブラリだけを使います。

新しい NVIDIA ホイールに切り替えるときは、`windows.py` の `WHEELS` を `https://pypi.org/pypi/<package>/<version>/json`
にある URL と `sha256` に書き換えてください。

## ライセンス

MIT。プラグインがダウンロードする NVIDIA のライブラリには NVIDIA のライセンス条件が適用されます。
