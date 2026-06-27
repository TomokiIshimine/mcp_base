#!/usr/bin/env bash
# PostToolUse フック: 編集された 1 ファイルだけに対して
#   1) ruff check --fix （自動修正可能な lint を修正・書き戻し）
#   2) ruff format     （整形・書き戻し。lint 修正後の最終コードを整える）
#   3) ruff check      （残った lint を報告）
#   4) mypy            （型検査・src 配下のみ）
# を実行する。問題が残った場合は exit 2 で stderr を Claude に返し、修正を促す。
# lint 修正(pyupgrade 等)はコードを書き換えるため、整形は必ず修正の後に行う。
# こうしないと CI の `ruff format --check` と整形差分で食い違う。
#
# 全体ではなく対象ファイル限定で走らせることで高速・低負荷に保つ。
# ツールは Docker ではなくローカル .venv のバイナリを直接叩く（最速）。
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
RUFF="$ROOT/.venv/bin/ruff"
MYPY="$ROOT/.venv/bin/mypy"
PY="$ROOT/.venv/bin/python"

input="$(cat)"

# .venv が無ければ何もせず終了（環境未構築でフックが邪魔をしないフェイルセーフ）。
# JSON 解析にも整形/検査にも .venv のツールしか使わないため、ここで一括判定する。
# 解析を make setup が必ず入れる Python に寄せ、未宣言依存（jq）への依存を排除する。
[ -x "$PY" ] || exit 0
[ -x "$RUFF" ] || exit 0

# stdin の JSON から編集対象ファイルパスを取り出す（Edit/Write/MultiEdit 共通）。
file="$(printf '%s' "$input" | "$PY" -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' \
  2>/dev/null)"

# 対象外なら何もせず終了（フックは全イベントに発火しうるため早期 return）。
[ -z "$file" ] && exit 0
case "$file" in
  *.py) ;;            # Python ファイルのみ対象
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0    # 削除直後などファイルが無ければスキップ

errors=""

# 1) 自動修正可能な lint を修正（書き戻し）。コードを書き換えることがある。
"$RUFF" check --fix "$file" >/dev/null 2>&1

# 2) 整形（書き戻し）。修正後の最終コードを整える。必ず check --fix の後に行う。
"$RUFF" format "$file" >/dev/null 2>&1

# 3) 残った lint を収集。
if ! lint_out="$("$RUFF" check "$file" 2>&1)"; then
  errors+="[ruff] 自動修正できない lint が残っています:\n${lint_out}\n\n"
fi

# 4) 型検査は mypy の設定対象（src 配下）のファイルのみ実行する。
# mypy の設定探索は CWD 基準で上方探索しないため、CWD がリポジトリ外だと
# pyproject.toml を取りこぼし strict 等が無効化される。--config-file で明示し、
# CWD に依存せず CI（make typecheck）と同じ設定で検査する。
case "$file" in
  */src/*|src/*)
    if [ -x "$MYPY" ]; then
      if ! mypy_out="$(MYPYPATH="$ROOT/src" "$MYPY" \
          --config-file "$ROOT/pyproject.toml" "$file" 2>&1)"; then
        errors+="[mypy] 型エラーがあります:\n${mypy_out}\n"
      fi
    fi
    ;;
esac

# 問題があれば exit 2 で Claude にフィードバックし、修正させる。
if [ -n "$errors" ]; then
  printf '%b' "$errors" >&2
  exit 2
fi

exit 0
