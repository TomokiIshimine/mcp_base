---
name: proposal-design-cycle
description: 「draft で提案レポートを書く → ユーザーが実ファイルでレビュー → 修正要望なら revise で書き直す → 承認後に apply で設計書本体を書く」という設計サイクルの契約を定める How スキル。設計係（draft / apply / revise の 3 モードを持つ 1 種類のサブエージェント）と、オーケストレーター（メイン側の承認ゲート）の 2 役の責務とインターフェースを規定する。設計サイクルを伴うワークフローを設計・実装する場面で参照する。
---

# proposal-design-cycle — 提案レビュー駆動の 3 モード設計サイクル契約

## 適用場面

調査結果や入力情報を起点に、設計書（または計画書・仕様書等）をユーザー承認のもとで作る一連の流れを採用するワークフローで参照する。bootstrap-docs / create-workflow / bootstrap-project / improve-workflow がこの契約を採用している。

本契約は **設計係（draft / apply / revise の 3 モードを持つ 1 種類のサブエージェント）** と **メイン（オーケストレーター）** の 2 役の責務を規定する。各ワークフローは差分点（ドメイン固有入力・設計書本体の見出しテンプレ・approval ゲートの配置など）だけを埋めれば、本契約のとおりに動く。

## 構成する 2 役

- **設計係**（designer）: 1 種類のサブエージェントが 3 モード（draft / apply / revise）を持つ。`AskUserQuestion` は呼ばない。
- **オーケストレーター**（メイン）: 各モードへの起動と、ユーザー承認ゲート（1 通の `AskUserQuestion`）を担う。

## 設計係の契約

### モード一覧

| mode | 入力（共通入力に追加） | 出力 |
|---|---|---|
| `draft` | `proposal-path`（必須）／ `revision-hint`（任意、再 draft 時のみ） | proposal を Write |
| `apply` | `proposal-path` ／ `output-path` | 設計書本体を Write |
| `revise` | `proposal-path` または `design-doc-path`（**XOR 必須**）／ `modification-request` | 該当ファイルを Edit |

共通入力（ドメイン固有入力）の名前と意味は各ワークフローが決める（例: `survey-report-path` / `stack-analysis-path` / `target-resolution-path` / `improvement-request` 等）。

### proposal の構造（draft が Write する内容）

draft は以下 2 つの H2 のみで proposal を構成する。`## ヒアリング項目` セクションは **設けない**（旧来の Q3-X 個別ヒアリング方式は本契約では廃止）。

- `## 提案サマリ` — メインが限定 Read してユーザーへの概要提示に用いる短い要約。
  - 提案の核となる選択を箇条書きで列挙し、各項目に **推奨値と根拠** を 1 行ずつ添える。
  - `revision-hint` を経ている場合は冒頭に「前回からの主な変更点」を併記する。
- `## 提案された設計書スケルトン` — apply で Write される設計書本体のドラフト案。各設計係はここに、apply で展開する設計書本体テンプレ（ドメイン固有の見出し構成）に沿って推奨値を一通り並べる。

### apply の責務

`<proposal-path>` の `## 提案された設計書スケルトン` と入力情報を統合し、設計書本体テンプレ（各設計係が固有差分として規定する見出し構成）に展開して `<output-path>` に Write する。proposal はメインが approval ゲートでユーザー承認を取得済みの前提（本契約のオーケストレーター契約による）。

apply モード内で再度ユーザー判断を取り直す `AskUserQuestion` は **発火しない**。proposal で承認された内容を機械的に展開するのが apply の責務。

### revise の責務

入力された対象パス（`<proposal-path>` または `<design-doc-path>`、XOR）を、`<modification-request>` の意図に従って Edit する。`<modification-request>` は複数論点を含む自由記述でよい。

整合チェック失敗時の中断ポリシー（`/workflow-orchestration` 参照）に従い、`<proposal-path>` と `<design-doc-path>` の両方が同時に渡された／どちらも渡されなかった場合は、`Edit` を一切行わず不整合内容を出力レポートに列挙して終了する。

revise が proposal を対象にした場合: `## 提案サマリ` ／ `## 提案された設計書スケルトン` の各セクションを対象に Edit する。
revise が design-doc を対象にした場合: 設計書本体の各セクション（各設計係が固有差分として規定）を対象に Edit する。

### 設計係が AskUserQuestion を呼ばないこと

すべてのユーザー対話はメインが担う。設計係は `ToolSearch` で `AskUserQuestion` のスキーマをロードする手順も持たない。proposal や設計書本体に「ユーザーに問うべき論点」が残る場合でも、設計係は **問わずに推奨値で proposal を埋める**（推奨値であることと根拠は `## 提案サマリ` で明示する）。

### 設計係が決めること（ワークフロー固有差分）

- (a) ドメイン固有入力の名前と意味
- (b) proposal の `## 提案サマリ` に列挙する論点項目とその粒度
- (c) `## 提案された設計書スケルトン` の中身（設計書本体テンプレに沿った推奨値の並べ方）
- (d) apply で展開する設計書本体の見出しテンプレ
- (e) revise で許容するセクション境界
- (f) `/context-engineering` から逸脱した提案を含む場合の `## ⚠️ /context-engineering からの逸脱` セクションの有無と書き方

## オーケストレーター（メイン）の契約

### approval ゲートの手順（1 通の AskUserQuestion で承認 or 修正要望取得）

設計係が `mode: "draft"` または `mode: "apply"` で Write した中間生成物（`<target>` ＝ proposal または design-doc）に対し、メインは以下の手順でユーザー承認を取得する。

1. **限定 Read**: `<target>` の **ユーザー概要提示用の固定見出し** のみ Read する（本文全読は禁止）。proposal の場合は `## 提案サマリ`、design-doc の場合は各ワークフローが固定見出しテーブルで指定した見出し。
2. **`AskUserQuestion` を 1 通発火**:
   - 質問文に `<target>` の **絶対パス** を必ず含め、ユーザーが実ファイルを開いてレビューできる状態にする。
   - `options`: `[{label: "承認", description: <承認時の挙動>}, {label: "修正要望あり", description: <修正要望時の挙動>}]`
3. 「承認」が選ばれた場合: 次ステップへ進む（proposal の承認なら apply、design-doc の承認なら後続ステップ）。
4. 「修正要望あり」が選ばれた場合:
   - 続けて `AskUserQuestion`（**自由記述スロット 1 件**）で `<modification-request>` を取得する。質問文に「複数論点をまとめて記述してよい」旨を明示する。
   - 設計係を `mode: "revise"` で再起動する。引数:
     - 対象パスキー: `proposal-path` または `design-doc-path`（`<target>` の種類に応じて XOR）
     - `modification-request`: 上記で取得した自由記述
     - その他のドメイン固有入力: 同 ステップで使ったものをそのまま再利用
   - 戻り値（`<target>` と同じ絶対パス）を保持して **手順 1 に戻る**。
5. **反復上限なし**（ユーザーが承認するまで継続）。

### approval ゲートを設置する位置

各ワークフローは以下のいずれかを採用する（採用判断はワークフロー設計者の裁量）。

- **draft 直後の 1 段ゲート**: proposal の承認のみ取得し、apply 後は確認なしで後続ステップへ進む。bootstrap-docs / bootstrap-project が採用。
- **draft 直後 + apply 直後の 2 段ゲート**: proposal を要件定義として承認、design-doc を設計として承認、それぞれ独立した実ファイルレビューを経る。create-workflow / improve-workflow が採用。

### `decisions.yaml` は使用しない

本契約は `decisions.yaml` を介した hearing フェーズを **持たない**。ユーザーの判断はすべて approval ゲートの「承認 / 修正要望（自由記述）」に集約される。

ただし、各ワークフローが固有要件で `decisions.yaml` 相当の意思決定記録を別目的で必要とする場合（例: ワークフロー固有の構造的選択を後段サブが Read する必要がある等）は、本契約の外で別ステップとして実装してよい。その場合も approval ゲートは本契約の手順を維持する。

### 限定 Read 契約

メインが `<target>` を Read してよい範囲は、各ワークフローの「限定 Read 契約の固定見出しテーブル」に列挙された見出しのみ。本契約はカラム規約と「本文全読禁止」の規範のみを規定し、見出しの実値は各ワークフローの責任範囲（`/workflow-orchestration` の限定 Read 契約と同一の規範）。

## ワークフロー設計者が決めること

本契約を採用するワークフローは、以下を自分で定義する。

- (a) 設計係のドメイン固有入力（`survey-report-path` / `stack-analysis-path` 等）の名前と意味
- (b) proposal の `## 提案サマリ` に列挙する論点項目（設計係プロンプトに記述）
- (c) `## 提案された設計書スケルトン` の中身（設計書本体の見出しテンプレと推奨値の並べ方、設計係プロンプトに記述）
- (d) approval ゲートを 1 段にするか 2 段にするか（draft 直後のみ／apply 直後にも設けるか）
- (e) approval ゲートの限定 Read 対象（proposal の `## 提案サマリ` 以外に design-doc 用の見出しを設ける場合の指定）
- (f) 反復上限の上書き（標準は「ユーザーが承認するまで」だが、業務要件で上限を設けたい場合）

## 既存 How スキルとの組み合わせ方

本契約は他の 3 スキルと役割分担する。境界は次のとおり。

| 領域 | 担当スキル | 本スキルが扱うか |
|---|---|---|
| 設計係の 3 モード（draft / apply / revise）と proposal の構造 | `proposal-design-cycle`（本スキル） | 扱う |
| approval ゲートの手順（1 通の AskUserQuestion で承認 or 修正要望取得） | `proposal-design-cycle`（本スキル） | 扱う |
| メインのオーケストレーション全般（限定 Read 契約・絶対パス引き回し・サブエージェント実行モード・戻り値形式 等） | `/workflow-orchestration` | 扱わない |
| `AskUserQuestion` 1 通の質問本文・選択肢の組み立て作法 | `/user-hearing` | 扱わない |
| 観点別レビュアー／再生成 author の契約・PASS/FAIL ループ手順 | `/multi-aspect-review` | 扱わない |
| プロンプト本文の文体（簡潔・明快・一意） | `/prompt-engineering` | 扱わない |

各スキルの説明と本スキルの説明が食い違う場合は、各スキル本体を真実の源泉として優先する。

## このスキル自身のポリシー

- **設計係のプロンプトに転写禁止**: 各設計係は本契約の手順を再掲せず、定義側からは「`/proposal-design-cycle` の設計係契約に従う」と参照する形で再利用する。設計係に書くのは固有差分（ドメイン固有の見出しテンプレ等）のみ。
- **ヒアリング項目方式は廃止**: 旧来の `## ヒアリング項目` 配下に Q3-X を列挙し、メインが各 Q を `AskUserQuestion` で順次発火する方式は本契約では使わない。proposal を読めば全提案が分かる構造で代替し、ユーザー対話は approval ゲートの 1 通（＋修正要望時の自由記述 1 通）に集約する。
- **契約変更時の波及確認**: 本スキルの契約を変更する場合は、参照している全ワークフロー（bootstrap-docs / create-workflow / bootstrap-project / improve-workflow / 他）の整合性を確認する。
