"""認証ゲートの Streamlit 画面描画を担う view（interface_adapter 層）。

Streamlit ネイティブ認証 API（st.login / st.user / st.logout）の呼び出しと、3 分岐
（未ログイン → ログイン導線 / ログイン済みかつ認可不成立 → 拒否画面 + ログアウト導線 /
認可成立 → CRUD 描画）の描画をこの層に閉じる。`st.user` から認可判定への入力
（email / email_verified）を取り出す責務もこの層が担う。

認可の業務ルールそのもの（完全一致＋検証フラグ）は usecase 層へ委譲し、この層は
「Streamlit から値を取り出し → usecase に判定させ → 分岐を描画する」変換と表示に徹する。
"""

import logging
from collections.abc import Callable
from enum import Enum, auto

import streamlit as st

from usecase.authorize_admin_usecase import AuthorizeAdminUseCase

logger = logging.getLogger(__name__)


class AuthGateDecision(Enum):
    """認証ゲートの 3 分岐。描画・ログ出力の双方がこの結論を共有する。"""

    UNAUTHENTICATED = auto()
    DENIED = auto()
    AUTHORIZED = auto()


def decide_auth_gate(
    *,
    is_logged_in: bool,
    email: str | None,
    email_verified: bool | None,
    authorize: AuthorizeAdminUseCase,
) -> AuthGateDecision:
    """ログイン状態と認可判定から、描画すべき 3 分岐を決める純粋関数。

    未ログインは認可判定以前に弾く。ログイン済みのときのみ usecase に認可を委ね、
    成立で AUTHORIZED、不成立（Email 不一致 / 未検証）で DENIED とする。Streamlit に
    依存しないため単体テストでゲート分岐を直接検証できる。
    """
    if not is_logged_in:
        return AuthGateDecision.UNAUTHENTICATED
    if authorize.is_authorized(email, email_verified):
        return AuthGateDecision.AUTHORIZED
    return AuthGateDecision.DENIED


def render_auth_gate(
    authorize: AuthorizeAdminUseCase,
    render_authorized: Callable[[], None],
    mask_email: Callable[[str], str],
) -> None:
    """認証ゲートを描画する。認可成立時のみ `render_authorized` を呼ぶ。

    `mask_email` は infrastructure 層のマスク関数を合成ルートから注入する（この層は
    infrastructure を直接 import しない）。認証イベントのログ記録はゲートの結論を
    一手に握るこの関数に集約し、同一事象を複数層で二重に記録しない。
    """
    is_logged_in = bool(getattr(st.user, "is_logged_in", False))
    email: str | None = getattr(st.user, "email", None)
    email_verified: bool | None = getattr(st.user, "email_verified", None)

    decision = decide_auth_gate(
        is_logged_in=is_logged_in,
        email=email,
        email_verified=email_verified,
        authorize=authorize,
    )
    _log_auth_event(decision, email, mask_email)
    _dispatch(
        decision,
        render_login=_render_login,
        render_denied=_render_denied,
        render_authorized=lambda: _render_authorized(render_authorized),
    )


def _dispatch(
    decision: AuthGateDecision,
    *,
    render_login: Callable[[], None],
    render_denied: Callable[[], None],
    render_authorized: Callable[[], None],
) -> None:
    """ゲートの結論に応じて 1 つの描画分岐だけを実行する。

    認可不成立・未ログインでは認可済み描画（CRUD）を一切呼ばないことを保証する
    （CRUD 内容の漏洩防止、FR-5 / FR-6）。Streamlit 非依存で分岐の網羅を単体検証できる。
    """
    if decision is AuthGateDecision.UNAUTHENTICATED:
        render_login()
    elif decision is AuthGateDecision.DENIED:
        render_denied()
    else:
        render_authorized()


def _log_auth_event(
    decision: AuthGateDecision,
    email: str | None,
    mask_email: Callable[[str], str],
) -> None:
    """認証成功・拒否・未認証をログに記録する。Email は必ずマスクして出す。"""
    masked = mask_email(email) if email else "(なし)"
    if decision is AuthGateDecision.AUTHORIZED:
        logger.info("認証成功: 管理者として認可しました email=%s", masked)
    elif decision is AuthGateDecision.DENIED:
        logger.warning("認証拒否: 管理者に不一致または未検証です email=%s", masked)
    else:
        logger.info("未認証アクセス: ログイン導線を提示します email=%s", masked)


def _render_login() -> None:
    """未ログイン分岐: ログイン導線を提示し、CRUD は描画しない。"""
    st.title("ログインが必要です")
    st.info("この画面の利用には管理者 Google アカウントでのログインが必要です。")
    if st.button("Google でログイン"):
        # secrets は名前付きプロバイダ [auth.google] で構成する（render-secrets.sh）。
        # 引数なし st.login() は [auth] 直下のみを読むため Google フローを起動できない。
        # プロバイダ名 "google" は生成される secrets の [auth.google] と一致させる。
        st.login("google")


def _render_denied() -> None:
    """認可不成立分岐: 拒否メッセージ＋別アカウント再ログイン導線。CRUD は描画しない。"""
    st.title("アクセスが許可されていません")
    st.error(
        "このアカウントには管理者権限がありません。"
        "別のアカウントでログインし直してください。"
    )
    _render_logout("別のアカウントでログインし直す")


def _render_authorized(render_authorized: Callable[[], None]) -> None:
    """認可成立分岐: ログアウト導線を添えて CRUD を描画する。"""
    _render_logout("ログアウト")
    render_authorized()


def _render_logout(label: str) -> None:
    """ログアウトボタンを描画する。押下で現在のセッションを未認証へ戻す。"""
    if st.button(label):
        st.logout()
