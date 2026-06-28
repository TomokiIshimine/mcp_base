# CLAUDE.md

Claude Code の全エージェント（メイン・サブエージェント）が共通して参照する基盤コンテキスト。常に薄く保ち、詳細・手順・規約本文は各ドキュメントと `.claude/rules/` へパス参照で逃がす。本ファイルのパスはプロジェクトルートからの相対パスで記す。

## プロジェクト目的

`mcp-base` は Clean Architecture 4 層で構成された Streamlit 製の greeting CRUD アプリ。MySQL に永続化した挨拶レコード（greeting）を Web 画面から作成・参照・更新・削除する。名称と現行実態（Streamlit greeting CRUD）の関係、将来の MCP サーバー化構想の正本は `docs/01_architecture.md` の「プロジェクトの位置づけ」にある。

## 設計原則

ドキュメント・規約・コンテキストの配置は次の 3 原則に従う（優先順位順）。

1. DRY: 同じ情報は 1 箇所にのみ置き、他からはパス参照する。
2. 最小コンテキスト: 必要なものを必要なときにのみロードする。本ファイルは常時ロードのため最小に保つ。
3. 疎結合: 各ドキュメント・規約・エージェントは独立して変更可能に保つ。

## 技術スタック概要

- 言語/ランタイム: Python 3.12、uv（ローカル `.venv`）。
- UI: Streamlit。永続化: MySQL（PyMySQL）。
- 実行基盤: Docker / Docker Compose。操作は `Makefile` のターゲット経由。
- 検査: ruff（format / lint）・mypy（strict）・bandit。

## ディレクトリ構成（主要 2 階層）

```
src/                   アプリ本体（Clean Architecture 4 層）
  domain/              ドメインモデル
  usecase/             ユースケース・ポート・業務例外
  interface_adapter/   Streamlit 画面・controller・画面提示用例外
  infrastructure/      MySQL リポジトリ・設定・ロギング初期化
  app.py               合成ルート（DI 配線・起動エントリポイント）
tests/                 テスト
db/                    MySQL 初期化資材
docs/                  設計ドキュメント（索引は docs/00_documentation-map.md）
.claude/rules/         コーディング規約（層別 00〜60）
tasks/                 作業中の中間生成物
```

## ドキュメントと規約の所在

- ドキュメント索引（読み順・責務境界・更新ポリシー）: `@docs/00_documentation-map.md`。docs/* への入口はここに集約しており、まずここから辿る。索引ハブは全エージェントが常に持つため自動ロード（`@`）で参照する。
- アーキテクチャ地図（4 層・主要ファイル・依存方向・プロジェクトの位置づけ）: `docs/01_architecture.md`。
- 利用者向け入口（概要・セットアップ・起動）: `README.md`。
- コーディング規約（実装上の制約・How）: `.claude/rules/`（常時ロードの共通規約 `.claude/rules/00-common.md` と層別 05〜60）。規約本文は本ファイルに再掲しない。

専門領域の仕様・設計・運用・受入条件は docs/*、コードの書き方は `.claude/rules/` に置く。本ファイルにすべてを書かず、各層の入口（上記パス）から辿る。
