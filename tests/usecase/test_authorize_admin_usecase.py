"""AuthorizeAdminUseCase の単体テスト（純粋ロジック、外部依存なし）。

D-2 の認可判定規則（検証フラグ＋管理者 Email の完全一致・正規化なし）を固定する。
"""

from usecase.authorize_admin_usecase import AuthorizeAdminUseCase

_ADMIN = "admin@example.com"


def _usecase() -> AuthorizeAdminUseCase:
    return AuthorizeAdminUseCase(_ADMIN)


def test_authorizes_verified_matching_email():
    # 正常系（AC-3）: 検証済み かつ 完全一致 → 認可成立。
    assert _usecase().is_authorized(_ADMIN, email_verified=True) is True


def test_rejects_non_matching_email():
    # 異常系（AC-4）: Email 不一致 → 拒否。
    assert _usecase().is_authorized("other@example.com", email_verified=True) is False


def test_rejects_matching_email_when_not_verified():
    # 境界（AC-5）: 一致しても email_verified=False は拒否。
    assert _usecase().is_authorized(_ADMIN, email_verified=False) is False


def test_rejects_when_verified_flag_is_none():
    # 境界（AC-5）: email_verified が None / 欠落（True 以外）も拒否。
    assert _usecase().is_authorized(_ADMIN, email_verified=None) is False


def test_rejects_case_only_difference():
    # 境界（AC-6）: 大文字小文字のみ差異 → 正規化せず拒否。
    assert _usecase().is_authorized("Admin@Example.com", email_verified=True) is False


def test_rejects_whitespace_only_difference():
    # 境界（AC-6）: 前後空白のみ差異 → 正規化せず拒否。
    assert _usecase().is_authorized(" admin@example.com ", email_verified=True) is False


def test_rejects_none_email():
    # 防御的: email が None（取り出せず）でも例外でなく拒否を返す。
    assert _usecase().is_authorized(None, email_verified=True) is False


def test_is_pure_function_without_side_effects():
    # 回帰防止: 同一入力で安定し、Streamlit / infrastructure に依存せず呼べる。
    usecase = _usecase()
    first = usecase.is_authorized(_ADMIN, email_verified=True)
    second = usecase.is_authorized(_ADMIN, email_verified=True)
    assert first is second is True
