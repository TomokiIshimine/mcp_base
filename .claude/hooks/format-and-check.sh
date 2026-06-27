#!/usr/bin/env bash
# PostToolUse フック: 編集された 1 ファイルだけに対して
#   1) ruff format     （整形・書き戻し）
#   2) ruff check --fix （自動修正可能な lint を修正・書き戻し）
#   3) ruff check      （残った lint を報告）
#   4) mypy            （型検査・src 配下のみ）
# を実行する。問題が残った場合は exit 2 で stderr を Claude に返し、修正を促す。
#
# 全体ではなく対象ファイル限定で走らせることで高速・低負荷に保つ。
# ツールは Docker ではなくローカル .venv のバイナリを直接叩く（最速）。
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
RUFF="$ROOT/.venv/bin/ruff"
MYPY="$ROOT/.venv/bin/mypy"

# stdin の JSON から編集対象ファイルパスを取り出す（Edit/Write/MultiEdit 共通）。
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

# 対象外なら何もせず終了（フックは全イベントに発火しうるため早期 return）。
[ -z "$file" ] && exit 0
case "$file" in
  *.py) ;;            # Python ファイルのみ対象
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0    # 削除直後などファイルが無ければスキップ

# ツールが無い場合は黙って継続（環境未構築でフックが邪魔をしないように）。
[ -x "$RUFF" ] || exit 0

errors=""

# 1) 整形（書き戻し）。失敗しても致命ではないので継続。
"$RUFF" format "$file" >/dev/null 2>&1

# 2) 自動修正可能な lint を修正（書き戻し）。
"$RUFF" check --fix "$file" >/dev/null 2>&1

# 3) 残った lint を収集。
if ! lint_out="$("$RUFF" check "$file" 2>&1)"; then
  errors+="[ruff] 自動修正できない lint が残っています:\n${lint_out}\n\n"
fi

# 4) 型検査は mypy の設定対象（src 配下）のファイルのみ実行する。
case "$file" in
  */src/*|src/*)
    if [ -x "$MYPY" ]; then
      if ! mypy_out="$(MYPYPATH="$ROOT/src" "$MYPY" "$file" 2>&1)"; then
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
