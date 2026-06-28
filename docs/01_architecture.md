# アーキテクチャ（コード探索の地図）

本ドキュメントは、4 層構成と現行ファイルの責務・依存方向を 1 枚にまとめた地図である。コード全体を読まずに全体像を把握し、目的のコードへ最短で到達するために使う。本プロジェクトのドキュメント・規約は DRY・最小コンテキスト・疎結合の原則に沿って配置を分離しており（全 docs の索引・読み順は `docs/00_documentation-map.md`）、依存方向・例外翻訳・ロギングの設計制約そのものは本ドキュメントで再掲せず、`.claude/rules/` の該当ファイルを相対パス参照で示す。

## プロジェクトの位置づけ

`mcp-base` という名称と現行実態には次の関係がある。本セクションがこの位置づけの正本であり、他ドキュメントは本セクションを参照する。

- **現行実態**: Clean Architecture 4 層で構成された Streamlit 製の greeting CRUD アプリ。MySQL の `greetings` テーブルに対する作成・参照・更新・削除を Web 画面から行う。MCP（Model Context Protocol）サーバー本体の機能はまだ存在しない。本ドキュメント群は現行実態を正とし、MCP ツール一覧等は記載しない。
- **将来構想**: 本プロジェクトを MCP サーバーとして実装する構想がある。その際、現行の Streamlit 画面は「MCP サーバーの管理画面」（想定機能: ユーザー追加・稼働状況確認・各種設定）という位置づけに移行する見込みである。管理画面の具体仕様は本体機能が未実装のため記載しない。

名称 `mcp-base` は将来構想に由来し、現行実態（Streamlit greeting CRUD）との乖離はこの構想段階であることに起因する。

## 4 層構成と依存方向

依存は外側から内側へ一方向に向かう。内側（`domain`・`usecase`）は外側（`interface_adapter`・`infrastructure`・framework）を知らない。

```
interface_adapter ──→ usecase ──→ domain
                          ↑
infrastructure ───────────┘  (usecase のポートと domain に依存)
```

- `interface_adapter` → `usecase` → `domain`
- `infrastructure` → `usecase`（ポート）・`domain`
- 層をまたぐ具象の生成・結線は合成ルート `src/app.py` に集約する。

依存方向の制約本文は `.claude/rules/05-architecture.md` を参照。

## 各層の責務マップ

| 層 | 主要ファイル | 責務 |
|---|---|---|
| domain | `src/domain/greeting_record.py` | `GreetingRecord`（id・message を持つ不変エンティティ）。永続化・表示・framework 非依存の純 Python。 |
| usecase | `src/usecase/manage_greetings_usecase.py` | `ManageGreetingsUseCase`。一覧・作成・更新・削除のオーケストレーションと入力の最小バリデーション（空文字禁止・最大長 `MAX_MESSAGE_LENGTH`）。正常系完了を INFO で記録。 |
| usecase | `src/usecase/greeting_crud_port.py` | `GreetingCrudPort`（ABC）。永続化への抽象インターフェース。usecase 側で定義・所有し、infrastructure が実装する（依存性逆転）。 |
| usecase | `src/usecase/errors.py` | ポート境界の業務例外。基底 `GreetingError` と `GreetingNotFoundError`／`InvalidGreetingError`／`RepositoryError`。 |
| usecase | `src/usecase/authorize_admin_usecase.py` | `AuthorizeAdminUseCase`。管理者 Email との完全一致＋`email_verified` ガードで認可可否を判定する純粋ロジック。Streamlit・infrastructure 実装に依存せず副作用を持たない（正規化はせずバイト単位一致）。 |
| interface_adapter | `src/interface_adapter/greeting_crud_controller.py` | `GreetingCrudController`。UI 入力を usecase 呼び出しへ変換し、結果を表示用 DTO `GreetingView` へ整形。業務例外を画面提示用例外へ翻訳し、操作失敗を記録（利用者起因＝WARNING／システム障害＝ERROR）。 |
| interface_adapter | `src/interface_adapter/greeting_crud_view.py` | `render_crud`。Streamlit による一覧・作成・更新・削除の画面描画。controller のみに依存し、原因別にエラーを出し分ける。 |
| interface_adapter | `src/interface_adapter/errors.py` | 画面提示用例外。基底 `OperationError` と `InvalidOperationError`（利用者起因）／`SystemFailureError`（システム障害）。 |
| interface_adapter | `src/interface_adapter/auth_gate_view.py` | `render_auth_gate`。Streamlit ネイティブ OIDC API（`st.login`／`st.user`／`st.logout`）を呼び、未ログイン／認可不成立／認可成立の 3 分岐を描画。`st.user` から認可入力（`email`／`email_verified`）を取り出して usecase に委譲し、認可成立時のみ CRUD 描画を呼ぶ。認証イベントを記録（Email はマスクして出力）。 |
| infrastructure | `src/infrastructure/mysql_greeting_crud_repository.py` | `MySQLGreetingCrudRepository`。`GreetingCrudPort` の MySQL 具象実装。PyMySQL＋コネクションプールで CRUD を行い、ドライバ固有例外を業務例外へ翻訳。SQL は `_GreetingSQL` に集約。 |
| infrastructure | `src/infrastructure/config.py` | `MySQLConfig`（接続設定）と `AuthConfig`（認可判定に用いる管理者 Email）を環境変数から構築。必須値欠如は `ConfigError` で起動失敗（fail-fast）。管理者 Email は `MySQLConfig.password` と同じく `repr=False` 相当で平文を漏らさない。 |
| infrastructure | `src/infrastructure/email_mask.py` | `mask_email`。認証イベントログ向けに Email のローカル部を部分マスク（`a***@example.com` 形式）。標準ライブラリのみで実装し、機微情報非出力の横断規約に従う。 |
| infrastructure | `src/infrastructure/logging_config.py` | `configure_logging`。ログのレベル・フォーマット・出力先を初期化。合成ルートから 1 回だけ呼ぶ。 |

各層の固有制約は `.claude/rules/10-domain.md`・`.claude/rules/20-usecase.md`・`.claude/rules/30-infrastructure.md`・`.claude/rules/40-interface-adapter.md` を参照。

## 合成ルート

`src/app.py` が DI 配線の集約点（合成ルート）であり、`streamlit run src/app.py` の起動エントリポイント。

- `MySQLConfig.from_env()` から `MySQLGreetingCrudRepository` を構築し、`ManageGreetingsUseCase` → `GreetingCrudController` の順に注入する。
- `AuthConfig.from_env()` から管理者 Email を読み `AuthorizeAdminUseCase` を構築。`render_crud` を直接呼ばず認証ゲート view `render_auth_gate` 越しに描画し、認可成立時のみ CRUD を描く。マスク関数 `mask_email`（infrastructure）はここから注入し、interface_adapter が infrastructure を直接 import しない依存方向を保つ。
- リポジトリ（接続プール）は `@st.cache_resource` でプロセス内 1 回だけ構築し再利用する。
- 設定不備（MySQL 接続設定・認証設定いずれの `ConfigError` も）は捕捉せず起動を失敗させる（fail-fast）。認可されない状態で CRUD を描画させない。描画中の想定外例外は最上位で 1 回だけ捕捉し、ログ記録と汎用メッセージ表示に落とす。

合成ルートの制約本文は `.claude/rules/50-composition-root.md` を参照。

## 横断的責務の所在

| 関心 | 設計制約の所在 |
|---|---|
| 依存方向・型設計 | `.claude/rules/05-architecture.md` |
| 例外翻訳（層境界での変換） | `.claude/rules/05-architecture.md`（横断）／各層ルール（層固有の例外型） |
| ロギング（記録責務の分担） | `.claude/rules/05-architecture.md`（横断）／各層ルール |

例外は層境界で翻訳する（infrastructure のドライバ例外 → usecase の `GreetingError` 系 → interface_adapter の `OperationError` 系）。失敗の記録は呼び出し側上位（controller）が、正常系完了は usecase が担い、二重記録しない。詳細な制約は上表の各ファイルを参照。

## 関連ドキュメント

- ドメインモデルと MySQL スキーマの詳細: `docs/04_data-design.md`
- 全 docs の索引・読み順: `docs/00_documentation-map.md`
