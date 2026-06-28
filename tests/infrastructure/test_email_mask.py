"""mask_email の単体テスト（D-5 / AC-8）。

ログに Email 平文を残さないことを契約として固定する。
"""

from infrastructure.email_mask import mask_email


def test_masks_local_part_keeping_first_char_and_domain():
    # 正常系: 先頭 1 文字 + マスク + ドメイン保持（a***@example.com 形式）。
    assert mask_email("alice@example.com") == "a***@example.com"


def test_domain_is_preserved():
    masked = mask_email("bob@sub.example.co.jp")
    assert masked.endswith("@sub.example.co.jp")
    assert masked == "b***@sub.example.co.jp"


def test_single_char_local_part_is_not_recoverable():
    # 境界: ローカル部 1 文字でも残り（原文）が固定マスクに潰れる。
    assert mask_email("a@example.com") == "a***@example.com"


def test_local_part_is_not_left_in_plaintext():
    # 回帰防止（AC-8 の核）: 元のローカル部全体が平文で残らない。
    masked = mask_email("alice@example.com")
    assert "alice" not in masked
    assert "lice" not in masked


def test_invalid_string_without_at_is_fully_masked():
    # 異常系: @ を含まない不正値は平文を出さず全体マスクに倒す。
    assert mask_email("not-an-email") == "***"


def test_empty_string_is_masked():
    assert mask_email("") == "***"


def test_empty_local_part_is_masked():
    # ローカル部が空（@ 始まり）でも先頭文字を捏造せず全体マスクにする。
    assert mask_email("@example.com") == "***@example.com"
