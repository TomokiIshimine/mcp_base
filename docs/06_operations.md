# 運用手順

ローカルでの起動・停止、MySQL の準備、環境変数、コード検査・テストの実行手順をまとめる。プロジェクトの位置づけ（mcp-base の名称と現行実態の関係）は `docs/01_architecture.md` の「プロジェクトの位置づけ」を参照。データベースのスキーマ・ドメインモデルは `docs/04_data-design.md` を参照。

操作はすべて `Makefile` のターゲット経由で実行する。各ターゲットの実体は `docker compose` コマンドで、アプリ・MySQL・検査ツールは Docker 上で動作する。`make help` で全ターゲットの一覧を表示できる。

## 前提環境

- Python 3.12
- uv（ローカル `.venv` の作成・編集時フック・エディタ補完に使用）
- Docker / Docker Compose（アプリ・MySQL・検査ツールの実行基盤）

## 初期セットアップ

すべての `docker compose` 系ターゲットは `.env` を必須とする（`.env` が無いと `_require-env` がエラーで停止する）。最初に `.env.example` をコピーする。

```sh
cp .env.example .env
```

`.env` の各変数は「環境変数」節を参照。コピー直後の既定値は Docker Compose 上での起動を想定した値になっている。

## アプリケーションの起動と停止

MySQL（`db`）と Streamlit アプリ（`app`）をまとめて起動する。`app` は `db` のヘルスチェック成功後に起動する。

| ターゲット | 動作 |
|---|---|
| `make build` | Docker イメージをビルドする |
| `make run` | MySQL + Streamlit を前面起動する。`http://localhost:8501` で接続。`Ctrl-C` で停止 |
| `make up` | 同じ構成をバックグラウンド起動する |
| `make down` | コンテナを停止・削除する（ボリュームは残す） |
| `make logs` | コンテナのログを追従表示する |
| `make ps` | コンテナの状態を表示する |
| `make clean` | コンテナ・ボリューム・ローカルキャッシュを削除する（DB データも消える） |

初回起動例:

```sh
cp .env.example .env
make run
```

`make run` はビルドを含むため、`make build` を個別に実行しなくてよい。

## ローカル開発環境の準備

アプリ実行・検査は Docker で完結するが、エディタ補完と編集時フック（後述）はホスト上の `.venv` を直接使う。`.venv` を一度だけ用意する。

```sh
make setup
```

`make setup` は `uv sync --frozen` を実行し、`uv.lock` に厳密一致する dev 依存込みの `.venv` を作成する。

## 環境変数

`.env` で設定する。`docker-compose.yml` は資格情報を直書きせず `.env` から補間するため、必須変数が未設定なら compose コマンドは起動時に失敗する。

| 変数 | 既定値（`.env.example`） | 必須 | 用途 |
|---|---|---|---|
| `MYSQL_HOST` | `db` | 任意（未設定時 `127.0.0.1`） | アプリの接続先ホスト |
| `MYSQL_PORT` | `3306` | 任意（未設定時 `3306`） | アプリの接続先ポート |
| `MYSQL_USER` | `app` | 必須 | アプリ用 DB ユーザー |
| `MYSQL_PASSWORD` | `app_password` | 必須 | アプリ用 DB パスワード |
| `MYSQL_DATABASE` | `app_db` | 必須 | データベース名 |
| `MYSQL_ROOT_PASSWORD` | `root_password` | 必須 | `db` コンテナの初期化・ヘルスチェック用（compose のみで使用） |
| `LOG_LEVEL` | `INFO` | 任意 | ログ出力レベル（`DEBUG` / `INFO` / `WARNING` / `ERROR`。未設定・不正値は `INFO`） |

接続先ホストは用途で異なる点に注意する。

- Docker Compose 上で起動する場合（`make run` 等）: `MYSQL_HOST=db` / `MYSQL_PORT=3306`（コンテナ間はサービス名 `db` で通信）。`.env.example` の既定値はこの構成。
- ホストから直接 Streamlit を動かす場合: `.env` を使わず `MYSQL_HOST` を未設定（既定 `127.0.0.1`）にするか、`MYSQL_HOST=127.0.0.1` / `MYSQL_PORT=3307` に書き換える（`3307` は compose が publish するホスト側ポート）。

## MySQL（Docker）

`db` サービスは `mysql:8.4` を使用する。

- ポート公開: ホスト `3307` → コンテナ `3306`（既存 MySQL との衝突回避）。コンテナ間は `db:3306` で通信する。
- データ永続化: 名前付きボリューム `db_data`。`make clean` で削除される。
- 初期化: `db/init/` をコンテナの初期化ディレクトリにマウントする。`db/init/01_schema.sql` が初回起動時に実行され、`greetings` テーブルを作成し初期行を投入する。テーブル定義の詳細は `docs/04_data-design.md` を参照。

疎通確認:

```sh
make db-check
```

`SELECT 1;` を `db` コンテナ内の MySQL に対して実行する。

## コード検査・テスト

検査ツール（ruff・mypy・pytest 等）は dev 依存を含む `tooling` サービス上で実行する。`.env` が必須。

| ターゲット | 動作 |
|---|---|
| `make fmt` | ruff でコードを整形する |
| `make lint` | ruff で静的検査する |
| `make typecheck` | mypy で静的型検査する（`src` 配下） |
| `make test` | pytest で軽量テスト（DB 不要）を実行する |
| `make audit` | pip-audit で依存ライブラリの既知脆弱性を検査する |
| `make security` | bandit でセキュリティ検査する |

`make test` の既定実行は `-m 'not integration'` で、実 MySQL を要するテストを除外する（軽量・DB 不要）。

## 統合テスト

実 MySQL を必要とするテストは `@pytest.mark.integration` で分離されており、既定の `make test` からは除外される。明示的に実行する。

```sh
make test-integration
```

`make test-integration` は `db` を起動してヘルスチェック完了まで待機し、`pytest -m integration --no-cov` を実行する。`integration` マーカーは `pyproject.toml` の `[tool.pytest.ini_options]` で定義済み。

## 編集時の自動整形・検査フック

`.py` ファイルを編集すると、PostToolUse フック `.claude/hooks/format-and-check.sh` が編集対象 1 ファイルに対して次を順に実行する。

1. ruff check --fix（自動修正可能な lint を修正・書き戻し）
2. ruff format（整形・書き戻し）
3. ruff check（残った lint を報告）
4. mypy（`src` 配下のファイルのみ型検査）

フックはホストの `.venv` のツールを直接使う。`make setup` で `.venv` を用意していない場合は何もせず終了する（フェイルセーフ）。修正できない問題が残った場合は内容を報告して編集の修正を促す。
