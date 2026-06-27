"""LOG_LEVEL の解決ロジックの単体テスト（ログ初期化の純ロジック）。"""

import pytest

from infrastructure.logging_config import _resolve_log_level


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("DEBUG", "DEBUG"),
        ("WARNING", "WARNING"),
        # 大文字小文字・前後空白は正規化する。
        ("debug", "DEBUG"),
        ("  info  ", "INFO"),
    ],
)
def test_known_levels_pass_through(raw, expected):
    assert _resolve_log_level(raw) == expected


@pytest.mark.parametrize("raw", [None, "VERBOSE", "", "   ", "10"])
def test_unknown_or_unset_falls_back_to_info(raw):
    # 未設定・不正値（未知名・空・数値文字列）は起動を落とさず INFO へ寄せる。
    assert _resolve_log_level(raw) == "INFO"
