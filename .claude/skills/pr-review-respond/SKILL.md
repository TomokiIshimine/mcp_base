---
name: pr-review-respond
description: 対象 PR のレビューコメントを収集し、各指摘を実ソースに照らして対応要否を判定、対応分だけを実装・並列レビュー・動作確認の改善ループで仕上げ、PR の各スレッドへ対応内容（見送りは根拠）を返信したいときに使う。push・PR コメント投稿という不可逆な副作用を伴うため、ユーザーが明示的に起動したときにのみ実行する。
argument-hint: [pr-number]
disable-model-invocation: true
---

# pr-review-respond — PR レビュー対応ワークフロー

対象 PR のレビュー指摘を収集・妥当性評価し、ユーザー承認のうえで対応分を一貫実装し、PR の各スレッドへ対応内容（見送りは根拠）を返信する、サブエージェント駆動のワークフロースキル。

## 目的

PR のレビュー指摘を鵜呑みにせず実コードと照合して対応要否を判定し、対応範囲をユーザー承認のうえで実装・レビュー・動作確認まで一貫処理し、最終的に PR の各スレッドへ対応／見送りを返信する。具体的な How（指摘収集・判定・実装・レビュー・返信投稿の手順）は各サブエージェントへ委譲し、本スキルは手順とオーケストレーションのみを規定する。

## 実行前提（起動方法・トリガー条件・自動発火可否）

- **起動方法**: ユーザーが `/pr-review-respond [pr-number]` のように **明示的に呼び出す**。`pr-number` は任意。
- **トリガー条件**: PR のレビューコメントへ対応・返信したい場面。`pr-number` が渡されればその PR を対象にし、無指定なら現在ブランチに紐づく PR（`gh pr view`）を Step 2 で対象解決する。
- **`disable-model-invocation: true`（明示呼び出し専用）**: 本スキルは frontmatter で自動発火を無効化している。**選択理由**は、Step 5 で作業ブランチの push・PR スレッドへのコメント投稿という **不可逆な副作用** を持つため、Claude Code の自主判断による誤発火を防ぐこと（既存 `develop` ワークフローと整合）。したがって本ワークフローはユーザーの明示起動でのみ動く。

## 共通契約への準拠

本スキルのメイン側オーケストレーションは、横断的な作法と設計サイクルの作法を既存 How スキルに委譲する。本節では契約本文を再掲せず、参照のみで完結させる（DRY）。

- **メイン側の横断的な作法は `/workflow-orchestration` の契約に従う**。限定 Read 契約・絶対パスの引き回し・サブエージェント実行モード（背景実行可否に依存しない並列 spawn）・戻り値形式・整合チェック失敗時の中断ポリシー・メインがしないこと、は `/workflow-orchestration` を正本とし、**本スキルでは再掲しない**。
- **設計サイクルと承認ゲートの作法は `/proposal-design-cycle` の契約に従う**。Step 3 の承認ゲート（1 通の `AskUserQuestion` による承認 or 修正要望取得、修正要望時の再起動）は `/proposal-design-cycle` のオーケストレーター契約を正本とし、approval ゲートの具体手順・限定 Read の規範・修正要望時の再評価起動を **本スキルでは再掲しない**。
- Step 4 の品質保証ループ（観点別並列レビュー → FAIL のみ再実装 → 全 PASS まで反復）は `/multi-aspect-review` の契約に従い、観点別レビュアー／再実装 author／オーケストレーターの責務・PASS/FAIL ループ手順・レポートのパスとテンプレートは同契約を正本とし、本スキルでは再掲しない。

以降のセクションでは、上記契約に対する **本ワークフロー固有の差分**（自スキル内の呼称・限定 Read 契約の固定見出しテーブル・クリーンワークツリーゲートとブランチ整合プリフライト・対応方針の写像サブへの委譲・反復制御の差分・流用 3 体への入力写像・失敗時のリカバリ）のみを列挙する。

## 限定 Read 契約（固定見出しテーブル）

メインがサブの生成物から Read してよいのは下表の見出しのみ。本文全読は禁止（`/workflow-orchestration` の限定 Read 契約に準拠）。

| 用途 | 対象ファイル | 抜粋する見出し |
|---|---|---|
| Step 3 承認ゲートでの対応方針サマリ提示 | `<workdir>/01_review-assessment.md` | `## 評価サマリ` |
| 対象 PR 番号の取得（無引数起動時の後段引き回し用） | `<workdir>/01_review-assessment.md` | `## 評価サマリ`（`- 対象 PR 番号: <N>` 行） |

固定見出し以外を Read したくなった場合は、サブ側に固定見出しへの整形を依頼し、メインは限定 Read を破らない。

対象 PR 番号は、`pr-review-analyst` の最終メッセージ（`対象 PR: #<N>`）と上記 `## 評価サマリ` の双方から取得できる。メインはこの値を `<pr-number>` として保持し、Step 2.5 のブランチ解決と Step 5 の返信投稿へ引き回す。

## サブエージェント構成

- `workflow-init`（流用）: 日付付き作業ディレクトリ作成ユーティリティ。
- `pr-review-analyst`（新規）: 対象 PR を解決しレビュー指摘を収集、実ソースに照らして対応要否を判定し対応方針を機械可読レポート化する係。1 体。
- `pr-review-fix-plan-mapper`（新規）: 承認済みの対応方針を、流用 3 体が Read する入力実ファイル（`02_fix-plan.md` / `03_requirements.md` / `04_design.md`）へ写像生成（Write）する係。1 体。メインは `/workflow-orchestration` 契約上サブ成果物を Write できないため、本写像 Write を本係に委譲する。
- `develop-coder` / `develop-reviewer` / `develop-runner`（流用 3 体）: Step 4 の実装・並列レビュー・動作確認を担う改善ループ要員。`develop` ワークフロー由来。
- `pr-review-responder`（新規）: 承認済み対応方針と実装差分を入力に、PR の対応スレッドへ対応内容を返信し見送り指摘へ根拠コメントを投稿する係。1 体。

## Step 1 — 作業ディレクトリ作成

- 呼び出し: `workflow-init`
- 渡す引数: `name=pr-review-respond`
- 期待する戻り値: `<workdir>` の絶対パス（`tasks/yyyy-mm-dd_pr-review-respond/`）。以後のステップで保持・引き回す。

## Step 1.5 — クリーンワークツリーの確認（開始時ゲート）

Step 4 で流用する `develop-reviewer` は実装差分を `git diff HEAD`（未コミット作業ツリー差分）＋未追跡ファイルとして取得する。開始時点に無関係な未コミット変更があると、それが「実装差分」に混入し、誤ってコミット・push・返信される。これを防ぐため、`develop` ワークフロー Step 1 相当のゲートをワークフロー冒頭に置く。

- メインが `git status` で未コミット変更・未追跡ファイルの有無を確認する。
- 変更がある場合は `AskUserQuestion` で「中止／そのまま継続／一時停止（ユーザーのコミット完了後に再開）」を、検出した未コミットファイル数を添えて確認する。ユーザーの選択なしにコミット・push へ進まない。
- クリーン、または「そのまま継続」が選ばれた場合のみ後段へ進む。継続時はこの時点の `HEAD` をベースラインとして保持し、Step 5 のコミット対象を本ワークフローの修正差分に限る根拠にする。

## Step 2 — PR 解決・指摘収集・妥当性評価

- 呼び出し: `pr-review-analyst`
- 渡す引数: `<pr-number>`（任意。無指定なら現在ブランチの PR を解決させる）／ `<workdir>`
- 期待する戻り値: `<workdir>/01_review-assessment.md` の絶対パスと、解決した対象 PR 番号（最終メッセージの `対象 PR: #<N>`）。メインはこの PR 番号を `<pr-number>` として確定・保持し、以後 Step 2.5・Step 5 へ引き回す。評価レポートは指摘一覧＋判定＋根拠＋対応分の修正方針を持ち、先頭に承認ゲート用の固定見出し `## 評価サマリ`（`- 対象 PR 番号: <N>` 行を含む）を備える。

## Step 2.5 — ブランチ整合プリフライト

Step 5 は対象 PR の head ブランチをコミット・push する必要がある。現在チェックアウト中のブランチが対象 PR の head と異なると、修正が別ブランチへ push されたまま `pr-review-responder` が「対応済み」と返信し、PR 本体に変更が反映されない齟齬が起きる。これを防ぐため、PR 番号確定後にブランチ整合をメインが固定手順で検証する。

- メインが `gh pr view <pr-number> --json headRefName` で対象 PR の head ブランチを解決する。
- 現在ブランチが head と一致すればそのまま続行する。不一致なら head ブランチをチェックアウトする。チェックアウトが安全に行えない（未コミット変更が残る等）場合は中断し、ユーザーへ状況を提示して指示を仰ぐ（`/workflow-orchestration` の中断ポリシーに準拠）。
- 解決した head ブランチ名を `<work-branch>` として保持し、Step 5 の push 対象に引き回す。

## Step 3 — 対応方針の承認ゲート

`/proposal-design-cycle` のオーケストレーター契約（approval ゲート手順）に従う。本ワークフロー固有の差分は以下。

- **限定 Read 対象**: `<workdir>/01_review-assessment.md` の `## 評価サマリ`（上記固定見出しテーブル）。本文全読はしない。
- **承認ゲートの論点**: どの指摘を対応・どれを見送りにするかの対応方針。`AskUserQuestion` の質問文に `01_review-assessment.md` の絶対パスを含め、ユーザーが実ファイルでレビューできる状態にする。選択肢は「承認」「修正要望あり」。
- **修正要望時**: 自由記述で修正要望（対応・見送りの再指定）を取得し、`pr-review-analyst` を再評価起動するか、メインが対応方針を更新する。承認まで反復（反復上限なし）。
- **承認後**: メインは確定した対応方針（承認結果と、修正要望があればその内容）を引数として `pr-review-fix-plan-mapper` を起動し、Step 4 の流用 3 体が読む入力実ファイルへの写像生成を委譲する。メインは `/workflow-orchestration` 契約上サブ成果物を Write しないため、本ステップでメイン自身がファイルを Write することはない。
  - 呼び出し: `pr-review-fix-plan-mapper`
  - 渡す引数: `<workdir>/01_review-assessment.md` の絶対パス ／ `<workdir>` ／（承認時に修正要望があればその自由記述）
  - 期待する戻り値: `<workdir>/02_fix-plan.md`（確定対応方針）・`<workdir>/03_requirements.md`（対応要件）・`<workdir>/04_design.md`（冒頭に領域定義／テスト設計セクションを備えた設計書）の絶対パス各 1 行。
- 出力: `<workdir>/02_fix-plan.md` ／ `<workdir>/03_requirements.md` ／ `<workdir>/04_design.md`。

## Step 4 — 実装・レビュー・動作確認の改善ループ

`/multi-aspect-review` の契約に従う品質保証ループ。全観点 PASS かつ動作確認 PASS まで反復する。

- **入力写像（本ワークフロー固有の差分）**: 流用 3 体（`develop-coder` / `develop-reviewer` / `develop-runner`）は `develop` 由来の入力パスをハードコードで Read する。すなわち `develop-coder` は `<workdir>/04_design.md`、`develop-reviewer` は `<workdir>/04_design.md` と `<workdir>/03_requirements.md`、`develop-runner` は `<workdir>/04_design.md` を Read する。これら実ファイルは Step 3 承認後に `pr-review-fix-plan-mapper` が写像生成済みである（メインは Write しない）。実体化を省くと流用 3 体は入力欠落でループ前に停止するため、Step 4 起動前に 3 ファイルの存在を前提とする。
  - 流用 3 体への引数供給元を Step 4 内で明示する: `develop-runner` の `<requirement>` には対応要件サマリを渡し、`develop-reviewer` の `<aspect>` は固定 6 観点を 1 体 1 観点で割り当て、`output-path` / `previous-review-path` は `/multi-aspect-review` 契約の命名規約で具体化する。
  - develop 側の成果物契約（入力パス・セクション名）が変わった場合は `pr-review-fix-plan-mapper` の写像も追従が要る（疎結合上の既知の依存）。
- **実装工程**: `develop-coder` に `<workdir>/04_design.md`（および 2 周目以降は FAIL 指摘）を渡し、対応分を TDD 実装させる。戻り値=実装差分。
- **点検工程（並列）**: 同一反復内で、`develop-reviewer` を固定 6 観点ぶん **並列** 起動（1 インスタンス = 1 観点）し、同時に `develop-runner` を 1 体 **並列** 起動する。並列 spawn は単一メッセージ内に複数 `Agent` 呼び出しを並べて実現する。
  - `develop-reviewer` の戻り値: `<観点別レビューレポート絶対パス> SP (PASS|FAIL)`。
  - `develop-runner` の戻り値: `<動作確認レポート絶対パス> SP (PASS|FAIL)`。
- **反復制御**: FAIL の観点・FAIL の動作確認がある限り、当該 FAIL を入力に `develop-coder` を再実装起動し、再点検する。全観点 PASS かつ動作確認 PASS で抜ける。レビューレポート・動作確認レポートのパスとテンプレートは `/multi-aspect-review` 契約を正本とする（本スキルで固定しない）。
- 出力: 実装差分／観点別レビューレポート群／動作確認レポート。

## Step 5 — PR へ対応反映・返信

本ステップは **コミット → push → 返信投稿** の順序で実施する。Step 4 の `develop-coder` は Write/Edit のみで git 操作をしないため、実装差分はワークツリーに未コミットで残る。コミットを挟まず push すると差分がリモートに届かないまま `pr-review-responder` が「対応済み」と返信し、投稿内容とリモート状態が矛盾する。順序を以下に固定し、未コミット状態での push・返信投稿を禁止する。

- **コミット（メインが実施）**: Step 4 改善ループ脱出後・push 前に、実装差分をコミットする。コミット対象は Step 1.5 で保持したベースライン `HEAD` 以降の本ワークフローの修正差分に限り、開始時点に存在した無関係な変更を巻き込まない。コミット粒度・メッセージはメインが対応方針に基づき決め、必要に応じ `AskUserQuestion` でユーザーに確認する。
- **push（メインが実施）**: コミット後に、Step 2.5 で確定した対象 PR の head ブランチ `<work-branch>` を `git push` する。push 対象が対象 PR の head と一致することを前提とし、push は本ステップでメインが実施し、`pr-review-responder` は実施しない前提。
- 呼び出し: `pr-review-responder`
- 渡す引数: 承認済み対応方針（`<workdir>/02_fix-plan.md`）／ 実装差分 ／ 対象 PR 番号（Step 2 で保持した `<pr-number>`）
- 責務: 対応した各レビュースレッドへ対応内容（どう直したか）を `gh` で返信、見送り指摘へ根拠コメントを投稿。
- 期待する戻り値: `<workdir>/response-summary.md` の絶対パス（投稿結果サマリ）。

## ユーザーへ返す最終出力

- 対象 PR 番号と対応／見送りの内訳サマリ。
- `<workdir>/01_review-assessment.md`（妥当性評価）・`<workdir>/02_fix-plan.md`（確定対応方針）・`<workdir>/response-summary.md`（投稿結果）の絶対パス。
- Step 4 改善ループの最終結果（全観点 PASS・動作確認 PASS の到達）と、PR スレッドへの返信／見送り根拠コメントの投稿結果。

## 失敗時のリカバリ

- サブエージェントが整合チェック失敗（入力レポート間の値の不一致・引数の XOR 違反等）を報告した場合、メインは自動進行・自動補正せず、報告内容をユーザーに提示して指示を仰ぐ（`/workflow-orchestration` の中断ポリシーに準拠）。
- Step 3 が未承認のまま Step 4 以降へ進まない。Step 4 の改善ループが全 PASS に至らないうちは Step 5 の push・返信投稿を行わない（不可逆な副作用を承認・品質確認の後段に閉じる）。
