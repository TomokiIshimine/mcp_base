# mcp-base

Clean Architecture 4 層で構成された Streamlit 製の greeting CRUD アプリ。MySQL に永続化した挨拶レコード（greeting）を Web 画面から作成・参照・更新・削除する。

名称 `mcp-base` は将来 MCP（Model Context Protocol）サーバーとして実装する構想に由来する。現行実態（Streamlit greeting CRUD）との関係と将来構想は `docs/01_architecture.md` の「プロジェクトの位置づけ」を参照。

## 前提環境

- Python 3.12
- uv
- Docker / Docker Compose

各ツールのバージョン・用途の詳細は `docs/06_operations.md` の「前提環境」を参照。

## セットアップと起動

アプリ・MySQL は Docker 上で動作する。操作はすべて `Makefile` のターゲット経由で実行する（`make help` で一覧を表示）。

1. 環境変数ファイルを用意する（compose は `.env` から接続情報を補間するため必須）。

   ```sh
   cp .env.example .env
   ```

2. アプリと MySQL を起動する。ブラウザで http://localhost:8501 を開く（停止は Ctrl-C）。

   ```sh
   make run
   ```

ローカルで編集時フック・エディタ補完を使う場合は、dev 依存込みの `.venv` を作成する。

```sh
make setup
```

環境変数の詳細・統合テスト・コード検査など運用手順の全体は `docs/06_operations.md` を参照。

## 主要ドキュメント

ドキュメント体系全体の索引・読み順・責務境界は `docs/00_documentation-map.md` に集約している。まずここを起点に必要なドキュメントへ辿る。

- `docs/00_documentation-map.md` — docs 体系全体の索引・責務境界・更新ポリシー。
- `docs/01_architecture.md` — 4 層構成と現行ファイルの責務・依存方向の地図、プロジェクトの位置づけ。
- `docs/06_operations.md` — 起動・停止、MySQL 準備、環境変数、検査・テストの運用手順。
