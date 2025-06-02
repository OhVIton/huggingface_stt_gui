# 音声文字起こしプレイグラウンド (Speech-to-Text Playground) - uv & Taskfile対応

このプロジェクトは、Hugging FaceのSpeech-to-Textモデルを利用して、音声ファイルから文字起こしを行うWebアプリケーションです。
ユーザーはWebインターフェースを通じて音声ファイルをアップロードし、使用するHugging Faceモデルを動的に指定できます。選択されたモデル名はブラウザのLocalStorageに保存されます。
文字起こし処理は非同期で行われ、ユーザーはタスクIDを使って進捗状況を確認できます。文字起こし結果は画面で確認したり、テキストファイルとしてダウンロードしたりすることができます。
利用可能なGPU（NVIDIA CUDAまたはApple Silicon MPS）があれば、自動的に活用して処理を高速化します。
バックグラウンド処理にはCeleryを使用し、メッセージブローカー/結果バックエンドとしてRedisを利用します。Redisの起動にはDocker Composeを使用することを推奨します。
Python環境の管理とパッケージのインストールには `uv` を、タスクの実行には `Task` ([taskfile.dev](https://taskfile.dev/)) を使用します。

## 主な機能

-   音声ファイルのアップロード
-   動的なHugging Faceモデル選択 (LocalStorage保存)
-   Celeryによる非同期文字起こし処理
-   タスクIDによる進捗確認と結果表示
-   GPUアクセラレーション (CUDA/MPS)
-   文字起こし結果のTXTダウンロード

## フォルダ構成

```
speech_to_text_playground/
├── app.py                   # Flaskアプリケーション本体
├── templates/
│   └── index.html           # WebページのHTMLテンプレート
├── compose.yml              # Docker Compose設定ファイル (Redis用)
├── Taskfile.yml             # Taskランナー設定ファイル
└── README.md                # このファイル
``


## 必要なもの

-   Python 3.8 以降 (uvが推奨するバージョンに合わせてください)
-   `uv` (高速なPythonパッケージインストーラおよびリゾルバ)
    -   インストール: [uv公式サイトのインストール手順](https://github.com/astral-sh/uv#installation) を参照 (例: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
-   `Task` (Go言語製のタスクランナー/ビルドツール)
    -   インストール: [Task公式サイトのインストール手順](https://taskfile.dev/installation/) を参照 (例: `go install github.com/go-task/task/v3/cmd/task@latest` またはバイナリダウンロード)
-   Docker および Docker Compose (Redisをコンテナで実行する場合)
-   `ffmpeg`: より広範な音声フォーマットをサポートするために推奨。

## セットアップ手順

1.  **リポジトリのクローンまたはファイルのダウンロード**:
    プロジェクトファイルを配置します。

2.  **`uv` と `Task` のインストール**:
    上記の「必要なもの」セクションのリンクを参照して、`uv` と `Task` をシステムにインストールしてください。

3.  **Python環境のセットアップと依存関係のインストール**:
    プロジェクトのルートディレクトリで以下のコマンドを実行します。
    ```bash
    task setup
    ```
    これにより、`uv` を使用して `.venv` という名前の仮想環境が作成され、必要なPythonライブラリがインストールされます。

4.  **Redisサーバーの準備**:
    **Docker Composeを使用する場合 (推奨):**
    プロジェクトのルートディレクトリで以下のコマンドを実行してRedisコンテナを起動します。
    ```bash
    task redis:up
    ```
    または直接 `docker-compose up -d` を実行します。
    停止する場合は `task redis:down` または `docker-compose down` を実行します。

    **手動でインストールする場合:**
    [Redis公式サイト](https://redis.io/docs/getting-started/installation/) の手順に従ってRedisをインストールし、サーバーを起動してください。

## アプリケーションの実行方法 (Taskfileを使用)

1.  **Redisサーバーの起動**:
    ```bash
    task redis:up
    ```
    (既に起動している場合は不要です)

2.  **開発環境全体の起動 (推奨)**:
    プロジェクトのルートディレクトリで、仮想環境を有効化 (`source .venv/bin/activate` など。Taskfile内のコマンドは `uv run` を使用するため多くの場合自動で仮想環境を利用しますが、明示的な有効化が確実です) してから、以下のコマンドを実行します。
    ```bash
    task default
    ```
    これは `task redis:up` を実行し、次に `task dev:all` (実質的に `task web`) を実行します。
    `dev:all` は現在、Flaskアプリをフォアグラウンドで起動します。**Celeryワーカーは別途 `task worker` で起動する必要があります。**

    **個別のコンポーネント起動:**
    各コンポーネントを別々のターミナルで監視したい場合は、以下のように個別に起動します。
    各コマンドは、プロジェクトのルートディレクトリで、仮想環境を有効化 (`source .venv/bin/activate` など) してから実行してください。

    * **Celeryワーカーの起動**:
        (新しいターミナルを開いて)
        ```bash
        task worker
        ```
    * **Flaskアプリケーションの起動**:
        (さらに別の新しいターミナルを開いて)
        ```bash
        task web
        ```
        これにより、Flaskアプリケーションが `http://localhost:58080` で起動します。

3.  **アクセス**:
    ウェブブラウザを開き、アドレスバーに `http://127.0.0.1:58080/` または `http://localhost:58080/` と入力してアクセスします。

## 利用可能なTaskfileコマンド

プロジェクトのルートディレクトリで `task --list` を実行すると、利用可能なすべてのタスクとその説明が表示されます。

-   `task setup`: Python仮想環境のセットアップと依存関係のインストール。
-   `task redis:up`: Redisサーバーを起動 (Docker Compose)。
-   `task redis:down`: Redisサーバーを停止 (Docker Compose)。
-   `task worker`: Celeryワーカーをフォアグラウンドで起動。
-   `task web`: Flask Webアプリケーションをフォアグラウンドで起動 (ポート58080)。
-   `task default`: 開発に必要なサービスを起動 (Redisを起動し、Flaskアプリを起動。ワーカーは別途起動)。
-   `task dev:all`: `task web` と同じ (ワーカーは別途起動)。
-   `task logs:redis`: Redisコンテナのログを表示。
-   `task clean`: 仮想環境とRedisデータをクリーンアップ。
-   `task lint`: (プレースホルダー) リンターを実行。

## 注意事項

-   **`uv` と `Task` のパス**: `uv` と `task` コマンドがシステムのPATHに通っていることを確認してください。
-   **仮想環境**: `task` コマンドを実行する前に、`task setup` で作成された仮想環境 (`source .venv/bin/activate` など) を有効化することが推奨されます。
-   **環境変数**: `app.py` 内のCelery設定は、環境変数 `CELERY_BROKER_URL` と `CELERY_RESULT_BACKEND` を参照できます。
-   **モデルのロード時間**: 新しいモデルを指定した場合、バックエンドでモデルのダウンロードとロードに時間がかかることがあります。
