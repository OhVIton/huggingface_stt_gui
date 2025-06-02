   # 音声文字起こしプレイグラウンド (Speech-to-Text Playground) - uv & ポート58080対応

   このプロジェクトは、Hugging FaceのSpeech-to-Textモデルを利用して、音声ファイルから文字起こしを行うWebアプリケーションです。
   ユーザーはWebインターフェースを通じて音声ファイルをアップロードし、使用するHugging Faceモデルを動的に指定できます。選択されたモデル名はブラウザのLocalStorageに保存されます。
   文字起こし処理は非同期で行われ、ユーザーはタスクIDを使って進捗状況を確認できます。文字起こし結果は画面で確認したり、テキストファイルとしてダウンロードしたりすることができます。
   利用可能なGPU（NVIDIA CUDAまたはApple Silicon MPS）があれば、自動的に活用して処理を高速化します。
   バックグラウンド処理にはCeleryを使用し、メッセージブローカー/結果バックエンドとしてRedisを利用します。Redisの起動にはDocker Composeを使用することを推奨します。
   Python環境の管理とパッケージのインストールには `uv` を使用します。

   ## 主な機能

   -   音声ファイルのアップロード
   -   動的なHugging Faceモデル選択 (LocalStorage保存)
   -   Celeryによる非同期文字起こし処理
   -   タスクIDによる進捗確認と結果表示
   -   GPUアクセラレーション (CUDA/MPS)
   -   文字起こし結果のTXTダウンロード

   ## フォルダ構成


speech_to_text_playground/
├── app.py                   # Flaskアプリケーション本体
├── templates/
│   └── index.html           # WebページのHTMLテンプレート
├── compose.yml              # Docker Compose設定ファイル (Redis用)
└── README.md                # このファイル


## 必要なもの

-   Python 3.8 以降 (uvが推奨するバージョンに合わせてください)
-   `uv` (高速なPythonパッケージインストーラおよびリゾルバ)
    -   インストール: [uv公式サイトのインストール手順](https://github.com/astral-sh/uv#installation) を参照してください。 (例: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
-   Docker および Docker Compose (Redisをコンテナで実行する場合)
-   `ffmpeg`: より広範な音声フォーマットをサポートするために推奨。

## セットアップ手順

1.  **リポジトリのクローンまたはファイルのダウンロード**:
    プロジェクトファイルを配置します。

2.  **Python仮想環境の作成と有効化 (`uv` を使用)**:
    プロジェクトのルートディレクトリで以下のコマンドを実行します。
    ```bash
    uv venv
    source .venv/bin/activate  # Linux/macOSの場合
    # .venv\Scripts\activate    # Windowsの場合
    ```
    これにより、`.venv` という名前の仮想環境が作成されます。

3.  **必要なPythonライブラリのインストール (`uv` を使用)**:
    仮想環境を有効化した後、以下のコマンドを実行します。
    ```bash
    uv pip install Flask torch torchaudio transformers celery redis eventlet
    ```
    -   **GPUユーザー向け注意**: PyTorchがGPUをサポートするバージョンでインストールされるように、必要に応じて `uv pip install` コマンドを調整してください (例: CUDAバージョン指定など。PyTorch公式サイトを参照)。

4.  **Redisサーバーの準備**:
    Celeryのメッセージブローカーおよび結果バックエンドとしてRedisが必要です。
    **Docker Composeを使用する場合 (推奨):**
    プロジェクトのルートディレクトリ（`compose.yml` がある場所）で以下のコマンドを実行してRedisコンテナを起動します。
    ```bash
    docker-compose up -d
    ```
    停止する場合は `docker-compose down` を実行します。

    **手動でインストールする場合:**
    [Redis公式サイト](https://redis.io/docs/getting-started/installation/) の手順に従ってRedisをインストールし、サーバーを起動してください。

## アプリケーションの実行方法

1.  **Redisサーバーの起動**:
    上記「Redisサーバーの準備」セクションに従って、Redisサーバーが実行中であることを確認してください。

2.  **Celeryワーカーの起動**:
    プロジェクトのルートディレクトリで、**新しいターミナルを開き**、仮想環境を有効化 (`source .venv/bin/activate` など) してから、以下のコマンドを実行してCeleryワーカーを起動します。
    ```bash
    uv run celery -A app.celery_app worker -l info -P eventlet
    ```
    または、単に `celery` コマンドがパスにあれば以下でも可:
    ```bash
    celery -A app.celery_app worker -l info -P eventlet
    ```

3.  **Flaskアプリケーションの起動**:
    プロジェクトのルートディレクトリで、**さらに別の新しいターミナルを開き**、仮想環境を有効化してから、以下のコマンドを実行してFlask Webサーバーを起動します。
    `app.py` 内でポート `58080` が指定されているため、`uv run` でスクリプトを実行します。
    ```bash
    uv run python app.py
    ```
    または、`app.py` に実行権限を付与している場合 (Linux/macOS):
    ```bash
    chmod +x app.py
    uv run ./app.py
    ```
    これにより、Flaskアプリケーションが `0.0.0.0:58080` で起動します。

4.  **アクセス**:
    ウェブブラウザを開き、アドレスバーに `http://127.0.0.1:58080/` または `http://localhost:58080/` と入力してアクセスします。

## 注意事項

-   **uvのインストール**: `uv` がシステムにインストールされていない場合は、先にインストールが必要です。
-   **環境変数**: `app.py` 内のCelery設定は、環境変数 `CELERY_BROKER_URL` と `CELERY_RESULT_BACKEND` を参照できます。
-   **モデルのロード時間**: 新しいモデルを指定した場合、バックエンドでモデルのダウンロードとロードに時間がかかることがあります。
