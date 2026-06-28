# データ設計（greeting レコード）

greeting レコードのドメインモデルと MySQL 永続化スキーマ、両者の対応関係を正本として定義する。属性・型・制約の真実源はコード（`src/domain/greeting_record.py`・`db/init/01_schema.sql`・`src/usecase/manage_greetings_usecase.py`）であり、本ドキュメントはその地図である。永続化実装の書き方（マッピング・例外翻訳・SQL 集約等の規約）は `.claude/rules/30-infrastructure.md` を参照する。

## ドメインモデル

`GreetingRecord`（`src/domain/greeting_record.py`）は id を伴う不変の挨拶エンティティ。`@dataclass(frozen=True)` で生成後は変更不可。永続化・表示の都合を持たない純 Python オブジェクト。

| 属性 | 型 | 役割 |
|---|---|---|
| `id` | `int` | 永続化で採番される識別子（MySQL の `AUTO_INCREMENT` 値）|
| `message` | `str` | 挨拶メッセージ本文 |

`message` の値制約（不変条件）は `GreetingRecord` 自体では検証せず、`src/usecase/manage_greetings_usecase.py` の `ManageGreetingsUseCase._require_message` が作成・更新の入口で保証する。

| 制約 | 内容 |
|---|---|
| 空文字禁止 | 前後空白を除去（`strip`）した結果が空ならエラー |
| 最大長 | `MAX_MESSAGE_LENGTH = 255`（Unicode コードポイント数を `len()` で判定）|
| 正規化 | 前後空白を除去した文字列を保存する |

## MySQL テーブル定義

`greetings` テーブル（`db/init/01_schema.sql`）。MySQL 初回起動時に初期化スクリプトとして実行される。

| カラム | 型 | 制約 |
|---|---|---|
| `id` | `INT` | `AUTO_INCREMENT` / `PRIMARY KEY` |
| `message` | `VARCHAR(255)` | `NOT NULL` |

- 文字セット: `DEFAULT CHARSET = utf8mb4`、照合順序: `COLLATE = utf8mb4_unicode_ci`。`VARCHAR(255)` を「255 文字」としてサーバ既定に左右されず確定させ、アプリ側の文字数判定と意味を一致させるため `utf8mb4` を明示する。
- 初期データ: スクリプトは `message = 'Hello, World from MySQL'` の行を 1 件投入する。

## ドメイン ⇄ 永続化表現の対応

`src/infrastructure/mysql_greeting_crud_repository.py` がドメインオブジェクトと SQL 行の相互変換を担う。SQL は同モジュールの `_GreetingSQL` に集約されている。

| `GreetingRecord` | `greetings` カラム |
|---|---|
| `id` | `id` |
| `message` | `message` |

| 操作 | SQL | id の扱い | 戻り値 |
|---|---|---|---|
| 一覧 | `SELECT id, message FROM greetings ORDER BY id` | 既存値を読む | `list[GreetingRecord]`（id 昇順）|
| 作成 | `INSERT INTO greetings (message) VALUES (%s)` | DB が採番（`lastrowid`）| 採番済み `GreetingRecord` |
| 更新 | `UPDATE greetings SET message = %s WHERE id = %s` | id で対象特定 | なし（影響 0 行は対象不在）|
| 削除 | `DELETE FROM greetings WHERE id = %s` | id で対象特定 | なし（影響 0 行は対象不在）|

- 作成時は `id` を SQL に渡さず、`AUTO_INCREMENT` が採番した `lastrowid` を `GreetingRecord.id` に充てる。
- 一覧取得は `DictCursor` でカラム名アクセスし、列順への暗黙依存を避ける。

## 文字数制約の二重定義と同期

`message` の最大長 255 は 2 箇所に物理的に分かれて存在し、共有できないため手動同期が必要。

- アプリ側の真実源: `src/usecase/manage_greetings_usecase.py` の `MAX_MESSAGE_LENGTH = 255`（DB 到達前に弾く第一の関門）。
- DB 側の最終防壁: `db/init/01_schema.sql` の `message VARCHAR(255)`（アプリ検証をすり抜けた入力を制約違反として弾く）。

一方を変更したら必ずもう一方も同じ値へ同期させる。DB 制約に当たった入力は infrastructure 層が利用者向けエラーへ翻訳する（翻訳の規約は `.claude/rules/30-infrastructure.md`）。

## 接続設定・環境変数の所在

greeting レコードの永続先となる MySQL の接続設定は、`src/infrastructure/config.py` の `MySQLConfig` が環境変数から読み取り、infrastructure 層に閉じる。これが接続設定の真実源。データ設計上の要点は、どの環境変数が「永続化される greeting がどこに保存されるか」を決めるか。

- 接続先データベースの特定（`MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_DATABASE`）: `greetings` テーブルが置かれる MySQL インスタンスとスキーマを決める。`MYSQL_DATABASE` が異なれば別のデータ集合を読み書きする。
- 永続化の到達可否（`MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`）: 資格情報と接続先 DB 名は必須で、未設定時は `ConfigError` で起動を止める（fail-fast）。これらが揃わない限り greeting の読み書きは一切成立しない。

各環境変数の要否・既定値の一覧、および `.env` の設定値・MySQL/Docker の起動を含む具体的な手順は `docs/06_operations.md` を参照する（本ドキュメントでは一覧を再掲しない）。
