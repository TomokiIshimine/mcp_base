---
name: develop
description: 機能追加・改修の要件 1 件から、調査 → 要件定義 → 設計 → 改善ループ（実装＋並列コードレビュー＋動作確認）→ ドキュメント更新 → PR 作成までを一貫実行する汎用開発ワークフロー。ブランチ作成・コミット・push・PR 作成という不可逆な git 操作を伴うため、ユーザーが `/develop` を明示的に呼び出したときにのみ起動する（モデル自動判断では発火しない）。
argument-hint: <requirement>（追加・改修したい機能の自然文。複数行・空文字可）
disable-model-invocation: true
---

# develop — 汎用開発ワークフロー

## 目的

機能追加・改修内容 `<requirement>`（自然文・複数行・空文字許容）を起点に、調査 → 要件定義 → 設計 → 改善ループ（実装＋並列コードレビュー＋動作確認）→ ドキュメント更新 → PR 作成を一貫実行する。要件 1 件から PR まで定型的に進めたい場面で使う。

「数行の小さな修正」から「新規パッケージのインストールを伴う機能追加」までを対象とする汎用フローであり、特定の開発規模や新規パッケージ導入の有無に依存しない。

## 実行前提

- **起動方法とトリガー条件**: ユーザーが `/develop <requirement>` を明示的に呼び出したときにのみ起動する。`<requirement>` は追加・改修したい機能の自然文（複数行・空文字可）。
- **`disable-model-invocation: true`**: 本フローはブランチ作成・コミット・push・PR 作成という不可逆な git 操作を伴う重量級フローである。モデルの自主判断による誤起動を防ぐため明示呼び出し専用とし、Claude Code が自律的に発火することはない。
- メインは作業開始前に `ToolSearch`（`query: "select:AskUserQuestion"`, `max_results: 1`）でスキーマを 1 度だけロードし、以降のヒアリングで再利用する。

### プロジェクト固有情報（埋め込み済み・実行時に再調査しない）

本フローは以下のプロジェクト固有情報を所与として扱う。develop 実行時のメイン・サブエージェントは下表の正本パスを所与として読み、これらを再調査・再ヒアリングしない（権威ある事実の正本は各パス側にあり、本表では再掲せず参照のみを置く）。`<requirement>` に直接関連する変動情報のみを実行時に調査・ヒアリングする。

| 項目 | 正本（所与として読む。追加調査しない） |
|---|---|
| アーキテクチャ概要 | Clean Architecture 4 層構成。正本は `docs/01_architecture.md`（4 層・依存方向・合成ルート `src/app.py` への結線集約を含む）。 |
| 既存規約 | コーディング規約の正本は `.claude/rules/`（常時ロード `00-common.md` ＋層別 05〜60）。検査ツール・ユビキタス言語・新規ファイル作成手順もここに従う。PostToolUse フック `format-and-check.sh` が `Edit|Write|MultiEdit` で発火する点のみ本フロー固有の前提として保持する。 |
| 領域分割の前提 | 単一領域（backend/frontend/infra の物理分割なし）。分割軸は Clean Architecture の「層」のみで、層は単一 coder 内で扱える。 |
| 動作確認手段 | 正本は `develop-runner` の埋め込み手段（Step 5 工程 2 から参照）。本表・Step 5 では手段本体を再掲しない。 |
| ドキュメント所在 | 正本は `docs/00_documentation-map.md`（docs/* 索引）／`README.md`／`CLAUDE.md`／`.claude/rules/`。 |

## 共通契約への準拠

- **メイン側の作法は `/workflow-orchestration` の契約に従う**。横断的なメインの作法（限定 Read 契約・絶対パス引き回し・サブエージェント実行モード・戻り値形式・整合チェック失敗時の中断ポリシー・メインがしないこと）は本スキルに **再掲しない**。出典は `/workflow-orchestration` を参照すること。
- **設計サイクルと承認ゲートの作法は `/proposal-design-cycle` の契約に従う**（本フローは Step 3・Step 4 に設計サイクルを含む）。設計係の 3 モード（draft / apply / revise）の責務・proposal の構造・approval ゲートの 1 通 `AskUserQuestion` 手順・修正要望時の revise 起動も本スキルに **再掲しない**。出典は `/proposal-design-cycle` を参照すること。
  - 本フローの設計係（`develop-requirements-author` / `develop-design-author`）はヒアリング論点を最終メッセージ（戻り値）で返し proposal ファイルを Write しない運用であるため、`/proposal-design-cycle` の proposal 構造のうち「論点列挙」部分は戻り値で代替する。承認ゲート自体（要件定義書 `03_requirements.md` ／ 設計書 `04_design.md` を実ファイルとしてユーザーがレビューし承認 or 修正要望）は `/proposal-design-cycle` のオーケストレーター契約どおりに運用する。
- 以下では本ワークフロー固有の差分（限定 Read 契約の固定見出しテーブル・反復制御の差分・自スキル内の Step 構成）のみを列挙する。

### 限定 Read 契約（固定見出しテーブル — 本フロー固有）

メインが各中間生成物から Read してよいのは下表の見出しのみ。本文全読は禁止。

| 用途 | 対象ファイル | 抜粋する見出し |
|---|---|---|
| Step 3 承認ゲートのユーザー概要提示 | `<workdir>/03_requirements.md` | `## 要件サマリ` |
| Step 4 承認ゲートのユーザー概要提示 | `<workdir>/04_design.md` | `## 設計サマリ` / `## 領域定義` |
| Step 5 実装ディスパッチ時の領域定義参照 | `<workdir>/04_design.md` | `## 領域定義` |

- 要件定義・設計の論点（ヒアリング項目）は設計係が最終メッセージ（戻り値）で返すためファイル化しない。メインは戻り値をそのまま `/user-hearing` の作法で発火する。
- コードレビュー結果・動作確認結果の PASS/FAIL 判定は各サブエージェントの戻り値（`<絶対パス> PASS|FAIL`）で受け取る。FAIL レポート本文は Read せず、再実装時は FAIL レポートの絶対パス群を `develop-coder` に引数として渡す（本文 Read はしない）。

## Step 1 — 作業準備（主体: メイン）

- 入力: `<requirement>`。
- 手順:
  1. `<requirement>` を確定する。**空文字の場合はまず `AskUserQuestion`（自由記述スロット）で開発したい機能・改修内容の本文をユーザーから取得し、それを `<requirement>` として保持する**（以降の Step 2〜7 はこの本文を参照するため、空のまま先へ進めない）。続いて確定した `<requirement>` の要約をケバブケース化して `<task-slug>` を導出する（`^[a-z0-9-]+$`・3〜40 文字）。slug は要件本文から導出し、slug 取得のためだけの単独ヒアリングは行わない。
  2. `<base-branch>`（現在ブランチ）を確認する。未コミット変更がある場合は `AskUserQuestion` で「中止／そのまま派生／一時停止（ユーザーのコミット完了後に再開）」を、未コミット変更ファイル数を質問文に含めて確認する。
  3. `workflow-init` を `workflow-name: <task-slug>` で起動し、`<workdir>`（絶対パス）を受領する。git 操作はメイン側で完結し `workflow-init` には渡さない。
  4. `<base-branch>` から作業ブランチを派生作成する。既定の作業ブランチ名は `<task-slug>` とし、確定した実ブランチ名を `<work-branch>` として保持する。同名既存時は `AskUserQuestion` で「既存ブランチへ切替／別名で作成／中止」を確認し、別名で作成・既存ブランチへ切替を選んだ場合は実際に使用するブランチ名で `<work-branch>` を更新する（Step 7 の push・PR head はこの `<work-branch>` を使う。`<task-slug>` は `<workdir>` 命名に使った値として別に保持する）。
- 出力（内部保持）: `<task-slug>` / `<work-branch>`（実際の作業ブランチ名。既定は `<task-slug>`）/ `<base-branch>` / `<workdir>`（絶対パス）。
- 制約: git 操作はメイン側で完結。業務ロジックには立ち入らない。

## Step 2 — `<requirement>` 関連コードの調査（主体: `develop-surveyor`）

- メインが `develop-surveyor` を 1 体起動する。
  - 引数: `<requirement>` / `<workdir>`。
  - 戻り値: `<workdir>/02_survey.md`（絶対パス 1 行）。
- 責務: `<requirement>` に直接関連する既存実装・影響範囲・関連ドキュメントのみを調査。プロジェクト構造・既存規約・動作確認手段・領域分割は埋め込み済みのため調査対象に含めない。

## Step 3 — 要件定義（論点抽出 → ヒアリング → ドキュメント化 → 承認）

1. **論点抽出**: メインが `develop-requirements-author`（論点列挙モード）を起動する。
   - 引数: `<workdir>/02_survey.md` / `<requirement>`。
   - 戻り値: 仕様上の論点（最終メッセージ・ファイル化しない）。埋め込み済み項目・コードレビュー観点は論点に含まれない。
2. **ヒアリング**: メインが戻り値を受け取り、`/user-hearing` の作法で各 Q を順次 `AskUserQuestion` で発火し、回答を `<workdir>/03_decisions.yaml` に記録する。論点が無く質問が発生しない場合も、空（または「論点なし」を明示した）`<workdir>/03_decisions.yaml` を必ず作成してから次の Write モードへ進む（Write モードは decisions ファイルの存在で起動が決まるため、未作成だと論点列挙モードへ誤分類される）。
3. **要件定義書 Write**: メインが `develop-requirements-author`（Write モード）を再起動する。
   - 引数: `<requirement>` / `<workdir>/02_survey.md` / `<workdir>/03_decisions.yaml`（`<requirement>` を必ず渡す。decisions が副次的論点しか含まない・空の場合でも、ユーザーが本来求めた機能・受入条件を要件定義書へ反映できるようにするため）。
   - 戻り値: `<workdir>/03_requirements.md`。
4. **承認**: メインが `/proposal-design-cycle` のオーケストレーター契約に従い approval ゲートを実施する。限定 Read で `03_requirements.md` の `## 要件サマリ` のみ提示し、1 通の `AskUserQuestion`（承認／修正要望）。修正要望時は `develop-requirements-author` を revise 起動（`design-doc-path: <workdir>/03_requirements.md` ＋ `modification-request`）し、承認まで反復する。
- 出力: `<workdir>/03_decisions.yaml` / `<workdir>/03_requirements.md`。

## Step 4 — 設計（ベストプラクティス調査 →（必要なら）パッケージ選定 → 設計論点抽出 → ヒアリング → ドキュメント化 → 承認）

1. **ベストプラクティス調査**: メインが `develop-best-practice-researcher` を起動する。
   - 引数: `<workdir>/03_requirements.md` / `<workdir>/02_survey.md`。
   - 戻り値: `<workdir>/04_best-practices.md`。
   - 責務: 設計判断の質を高めることを主目的に、論点ごとに一次情報を Web 調査。新規パッケージ／ライブラリ選定は論点に応じた一例であり常に行う前提にしない（「新規導入不要」という結論もありうる）。
2. **設計論点抽出**: メインが `develop-design-author`（論点列挙モード）を起動する。
   - 引数: `<workdir>/03_requirements.md` / `<workdir>/02_survey.md` / `<workdir>/04_best-practices.md`。
   - 戻り値: 設計不明点の論点（最終メッセージ・ファイル化しない）。各論点にベストプラクティス調査の出典参照が添えられる。新規パッケージ採否が論点になった場合はそれも含む（不要な要件では採否論点が出ないことを許容）。
3. **ヒアリング**: メインが戻り値を受け取り、`/user-hearing` の作法で各 Q を順次発火し、回答を `<workdir>/04_decisions.yaml` に記録する。設計論点が無く質問が発生しない場合も、空（または「論点なし」を明示した）`<workdir>/04_decisions.yaml` を必ず作成してから次の Write モードへ進む（Write モードは decisions ファイルの存在で起動が決まるため）。
4. **設計書 Write**: メインが `develop-design-author`（Write モード）を再起動する。
   - 引数: `<workdir>/03_requirements.md` / `<workdir>/02_survey.md` / `<workdir>/04_best-practices.md` / `<workdir>/04_decisions.yaml`。
   - 戻り値: `<workdir>/04_design.md`（冒頭に領域定義セクションを必ず含む。埋め込み済み領域分割から本要件で扱う層を選択）。設計書にはテスト設計セクション（要件の受入条件に対応する E2E 受入シナリオ＋ユニットテスト観点）を含める。本フローは実装をテスト駆動とするため、テスト設計は設計工程で確定する。
5. **承認**: メインが approval ゲートを実施する。限定 Read で `04_design.md` の `## 設計サマリ` / `## 領域定義` のみ提示し、1 通の `AskUserQuestion`（承認／修正要望）。修正要望時は `develop-design-author` を revise 起動し、承認まで反復する。
- 出力: `<workdir>/04_best-practices.md` / `<workdir>/04_decisions.yaml` / `<workdir>/04_design.md`。

## Step 5 — 改善ループ（実装 → コードレビュー／動作確認の並列 → 判定）

`<iteration>` を 1 から始めるループを回す（`/multi-aspect-review` 構成）。各周回で以下を実施する。

1. **実装（テスト駆動）**: メインが `04_design.md` 冒頭の領域定義セクションを参照し、領域ごとに対応する coder を spawn する。本プロジェクトは単一領域のため `develop-coder` を 1 体 spawn する。coder は設計書のテスト設計セクションに対応するテスト（ユニット・E2E）をプロダクションコードと併せて追加・更新する。テストの追加・更新は coder の責務であり、後段で並列実行される runner はテストを追加せず実行のみを担う（並列レビュー中にリポジトリファイルが変化して reviewer の点検対象とズレる・worktree が競合する事態を防ぐため）。
   - 引数: `<workdir>/04_design.md`（再実装時は併せて FAIL 指摘レポートの絶対パス群）。
   - 戻り値: 実装差分（プロダクションコード＋テストコード）。
2. **コードレビューと動作確認の並列実行**: メインが **単一メッセージ内に複数の `Agent` 呼び出しを並べて並列 spawn** する。
   - コードレビュー: 固定 6 観点それぞれに `develop-reviewer` を 1 体ずつ並列 spawn（合計 6 体）。
     - 各引数: 実装差分 / `<workdir>/04_design.md` / `<workdir>/03_requirements.md` / `<aspect>` / `<output-path>`（メインが `<workdir>/05_review-<iteration>_<aspect>.md` を具体化して渡すレビューレポート書き出し先絶対パス。`develop-reviewer` は `/multi-aspect-review` 契約に従いこの `output-path` に Write する。2 周目以降は併せて前周回レポート `<workdir>/05_review-<iteration-1>_<aspect>.md` の絶対パスを `previous-review-path` として渡す）。
     - 各戻り値: `<workdir>/05_review-<iteration>_<aspect>.md` ＋ 最終メッセージで `<絶対パス> PASS|FAIL`。
     - 固定 6 観点（spawn する順序が API。並び替え・カスタマイズ不可）: `requirement-fidelity` / `architecture-fidelity` / `security` / `performance` / `readability` / `test-coverage`。各観点の点検基準・判定定義の正本は `develop-reviewer` にあり、本スキルは spawn 対象としてこの 6 観点を列挙するのみで定義を再掲しない。
   - 動作確認: `develop-runner` を 1 体（コードレビューと同一メッセージで並列）。
     - 引数: 実装差分 / `<workdir>/04_design.md` / `<requirement>` / `<iteration>`（現在の反復番号。runner が出力ファイルを決定論的に命名するための正規の渡し方。出力先を明示固定したい場合の代替として `<output-path>` に具体化した `<workdir>/05_runtime-verification-<iteration>.md` を直接渡してよい）。
     - 戻り値: `<workdir>/05_runtime-verification-<iteration>.md` ＋ 最終メッセージで `<絶対パス> PASS|FAIL`。
     - 動作確認手段の本体（実行するコマンド・`make test-integration` を含む条件分岐・ブラウザ自動操作の手順）は `develop-runner` の埋め込み手段を正本とし、本スキルでは再掲しない。runner は実装差分と設計書のテスト設計セクションに基づいて検証し、要件充足に必要なテストが不足していればテストを足さず FAIL の根拠として明記する（次周回で coder が補う）。ブラウザ自動操作が技術的に実施できない場合も runner がその原因を根拠に `FAIL` を返す。判定は PASS/FAIL の二値。
3. **判定**:
   - 全コードレビュー観点 PASS かつ動作確認 PASS → ループ脱出（コミットへ）。
   - 1 つでも FAIL → 工程 1（実装）へ戻り、FAIL レポートの絶対パス群を入力として再実装・再レビュー・再動作確認。
   - **反復上限は 5 周**。上限到達時はメインが `AskUserQuestion` で「Step 6 へ継続（残課題を PR 説明に明記）／中止（PR を作らずワークフロー終了。作業ブランチはローカルに保持）」を確認し、ユーザー判断に従う。
4. **コミット**: ループ脱出後、Step 6 へ進む前に「git 操作のタイミング」表に従い実装差分をコミットする（粒度・メッセージは `AskUserQuestion` で確認）。
- 出力: `<workdir>/05_review-<iteration>_<aspect>.md`（観点 × 反復）/ `<workdir>/05_runtime-verification-<iteration>.md`。

## Step 6 — ドキュメント更新（主体: メイン ＋ `develop-doc-updater`）

- メインが埋め込み済みドキュメント所在と実装差分を突き合わせ、次の判定軸で更新対象ドキュメントを特定する。
  - 公開インターフェースの変更（API シグネチャ・CLI 引数・設定スキーマ・公開関数の追加／変更／削除）。
  - 構造の変化（新規モジュール追加・ディレクトリ構成変更・依存関係の追加削除）。
  - 手順・規約の変化（セットアップ／コントリビュート手順・命名規則・運用フローの変更）。
- いずれにも該当しないと判断した場合: 判断根拠を 1 行でユーザーへ提示し本ステップをスキップして Step 7 へ進む。
- 更新対象が 1 本以上特定できた場合: ドキュメント 1 本につき `develop-doc-updater` を 1 体 spawn する。
  - 各引数: `<workdir>/04_design.md` / 実装差分 / レビュー結果 / 対象ドキュメントパス。
  - 各戻り値: 更新された対象ドキュメント。
- 更新差分は「git 操作のタイミング」表に従いコミットする（粒度・メッセージは `AskUserQuestion`）。

## Step 7 — PR 作成（主体: メイン ＋ `develop-pr-author`）

- メインが Step 6 までのコミット（ドキュメント更新分を含む）を `git push -u origin <work-branch>` でリモートへ push する。
- メインが `develop-pr-author` を起動する。
  - 引数: 要件定義書・設計書・実装差分・レビュー結果・動作確認結果の各絶対パス / `<base-branch>` / `<work-branch>`。
  - 戻り値: 作成された PR の URL。
  - 責務: PR タイトル・本文を組み立て `gh pr create --base <base-branch> --head <work-branch>` で PR を作成。Step 5 改善ループが上限到達で「継続」を選んだ場合は残課題を PR 本文末尾に明記する。
- メインは `develop-pr-author` 完了後、作成された PR の URL と簡潔な概要をテキストで提示してワークフローを終了する。

## git 操作のタイミング（develop 固有）

| タイミング | 操作 | 主体 | 備考 |
|---|---|---|---|
| Step 1 | 作業ブランチ作成 | メイン | `<base-branch>` から作業ブランチを派生し実ブランチ名を `<work-branch>` に保持（既定 `<task-slug>`） |
| Step 5 末尾 | 実装差分コミット | メイン | 粒度（単一コミット／機能単位で分割）とメッセージは `AskUserQuestion` で確認 |
| Step 6 末尾 | ドキュメント更新差分コミット | メイン | 粒度・メッセージのヒアリング方法は Step 5 末尾と同じ |
| Step 7 冒頭 | push | メイン | `git push -u origin <work-branch>` |

**NEVER** 承認なしのブランチ削除・force 系オプション・`-D` 等の破壊的 git 操作。改善ループ中止・反復上限到達時の中止判断時も、作業ブランチはローカルに保持する。

## 最終的にユーザーへ返す内容

- 正常完了時: 作成された PR の URL と簡潔な概要。
- Step 5 改善ループ中止／反復上限到達で中止を選んだ場合: PR は作成せず、作業ブランチがローカルに保持されている旨と残課題を提示して終了する。
