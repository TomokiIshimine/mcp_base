"""Email のログ用マスク（infrastructure 層）。

認証イベントログに Email を出す際、平文を残さずローカル部を部分マスクする。
機微情報（個人情報）をログに出さない横断規約（.claude/rules/05-architecture.md）に
従い、標準ライブラリのみで実装する（新規依存なし）。
"""

# ローカル部の先頭 1 文字を除く残り全体を置換する固定マスク。長さを露出させない
# よう、原文の長さに依らず常に同じ固定長の記号に潰す（`a***@example.com` 形式）。
_MASK = "***"


def mask_email(email: str) -> str:
    """Email をログ向けにマスクする。先頭 1 文字とドメインのみ残す。

    `alice@example.com` → `a***@example.com`。ローカル部が 1 文字でも残り（＝原文）
    が復元できない固定マスクに潰す。`@` を含まない不正値・空文字は、何が渡されても
    平文を出さないよう安全側でマスク全体（`***`）に倒す。
    """
    if not email or "@" not in email:
        return _MASK
    local, _, domain = email.partition("@")
    if not local:
        # ローカル部が空（`@example.com` 等）。残す先頭文字が無いので全体をマスク。
        return f"{_MASK}@{domain}"
    return f"{local[0]}{_MASK}@{domain}"
