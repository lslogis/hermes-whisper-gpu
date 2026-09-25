# macOS での whisper-gpu

[English](MACOS.md) · [한국어](MACOS.ko.md) · **日本語**

Hermes のローカル Whisper は faster-whisper で、Metal バックエンドがないため Mac では常に CPU で動きます。このプラグインは
音声認識プロバイダー `whisper-gpu` を登録します。音声を Mac の GPU で動く**ローカル MLX サーバー**に送り、サーバーに
接続できないときは Hermes の CPU Whisper で代行します。

Apple シリコン(M1 以降)が必要です。Intel Mac では MLX が動きません。M4 Max と `whisper-large-v3-turbo` での実測値は、
クリップ 1 本あたり CPU 約 4 秒、MLX 0.3 秒です。

## 1. ローカル MLX サーバー

OpenAI 互換の `POST /v1/audio/transcriptions` を提供するサーバーなら何でも使えます。[oMLX](https://github.com/jundot/omlx) に
[`mlx-community/whisper-large-v3-turbo`](https://huggingface.co/mlx-community/whisper-large-v3-turbo) を oMLX のモデル
フォルダー(`~/.omlx/models/mlx-community/whisper-large-v3-turbo`)に置いて検証しました。

この MLX 変換版にはプロセッサーとトークナイザーのファイルが含まれておらず、oMLX が読み込めません。
[`openai/whisper-large-v3-turbo`](https://huggingface.co/openai/whisper-large-v3-turbo) から次のファイルを同じフォルダーに
コピーしてください: `preprocessor_config.json`、`tokenizer.json`、`tokenizer_config.json`、`special_tokens_map.json`、
`vocab.json`、`merges.txt`、`added_tokens.json`、`normalizer.json`、`generation_config.json`。

確認:

```
curl http://127.0.0.1:8000/v1/audio/transcriptions -F model=whisper-large-v3-turbo -F file=@clip.mp3
```

サーバーが常駐モデルを 1 つに制限している場合は、その制限が音声モデルを数えないようにしてください。そうしないと、音声を
認識するたびにチャットモデルがアンロードされます。

## 2. Hermes との接続

```
hermes plugins install lslogis/hermes-whisper-gpu
hermes plugins enable whisper-gpu
hermes config set stt.provider whisper-gpu
```

既定値です。環境が異なる場合だけ変更してください。

```
hermes config set plugins.entries.whisper-gpu.settings.endpoint http://127.0.0.1:8000/v1
hermes config set plugins.entries.whisper-gpu.settings.whisper_model whisper-large-v3-turbo
```

代行用の CPU モデルも設定しておいてください: `hermes config set stt.local.model large-v3-turbo`。

## 動作

- MLX サーバーが応答した場合、結果の `provider` は `whisper-gpu`、代行した場合は `local` です。代行した結果には
  `fallback_reason`(例: `Connection refused`)が付きます。
- エンドポイントはループバック(`127.0.0.1`、`localhost`、`::1`)か `https://` でなければなりません。ほかのホストへの
  平文 HTTP はプラグインの読み込み時に拒否するので、音声が暗号化されずにネットワークを通ることはありません。
- MLX 変換版は CPU モデルと句読点や分かち書きが異なることがあります(例: 韓国語の「헤르메스에요」と「헤르메스예요」)。
