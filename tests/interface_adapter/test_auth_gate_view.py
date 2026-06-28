"""認証ゲート分岐の単体・結合テスト（D-3 / FR-5 / FR-6）。

純粋な決定ロジック（decide_auth_gate）・分岐ディスパッチ（_dispatch）・認証イベント
ログ（_log_auth_event）は Streamlit 非依存で直接検証する。加えて、設計書「テスト設計」
の注記（実 Google アカウント認証を自動操作できない場合は `st.user` をスタブ／フェイクで
差し替えた結合テストでゲート 3 分岐と描画分岐を検証する）に従い、`st` をフェイクに差し
替えて入口 `render_auth_gate` と 4 つの描画分岐関数（_render_login / _render_denied /
_render_authorized / _render_logout）の結線・押下経路・CRUD 非描画を検証する。
"""

import logging

import pytest

from interface_adapter import auth_gate_view
from interface_adapter.auth_gate_view import (
    AuthGateDecision,
    _dispatch,
    _log_auth_event,
    _render_authorized,
    _render_denied,
    _render_login,
    _render_logout,
    decide_auth_gate,
    render_auth_gate,
)
from usecase.authorize_admin_usecase import AuthorizeAdminUseCase

_ADMIN = "admin@example.com"


def _authorize() -> AuthorizeAdminUseCase:
    return AuthorizeAdminUseCase(_ADMIN)


def test_decides_unauthenticated_when_not_logged_in():
    decision = decide_auth_gate(
        is_logged_in=False,
        email=None,
        email_verified=None,
        authorize=_authorize(),
    )
    assert decision is AuthGateDecision.UNAUTHENTICATED


def test_decides_authorized_when_logged_in_and_authorized():
    decision = decide_auth_gate(
        is_logged_in=True,
        email=_ADMIN,
        email_verified=True,
        authorize=_authorize(),
    )
    assert decision is AuthGateDecision.AUTHORIZED


def test_decides_denied_when_logged_in_but_not_authorized():
    decision = decide_auth_gate(
        is_logged_in=True,
        email="other@example.com",
        email_verified=True,
        authorize=_authorize(),
    )
    assert decision is AuthGateDecision.DENIED


def test_decides_denied_when_logged_in_but_unverified():
    decision = decide_auth_gate(
        is_logged_in=True,
        email=_ADMIN,
        email_verified=False,
        authorize=_authorize(),
    )
    assert decision is AuthGateDecision.DENIED


class _Spy:
    """どの描画分岐が呼ばれたかを記録するスパイ。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def make(self, name: str):
        def _call() -> None:
            self.calls.append(name)

        return _call


def _run_dispatch(decision: AuthGateDecision) -> list[str]:
    spy = _Spy()
    _dispatch(
        decision,
        render_login=spy.make("login"),
        render_denied=spy.make("denied"),
        render_authorized=spy.make("authorized"),
    )
    return spy.calls


def test_dispatch_authorized_renders_only_crud():
    assert _run_dispatch(AuthGateDecision.AUTHORIZED) == ["authorized"]


def test_dispatch_denied_does_not_render_crud():
    # FR-6 回帰: 拒否分岐で認可済み描画（CRUD）を呼ばない。
    assert _run_dispatch(AuthGateDecision.DENIED) == ["denied"]


def test_dispatch_unauthenticated_does_not_render_crud():
    # FR-5 回帰: 未ログイン分岐で認可済み描画（CRUD）を呼ばない。
    assert _run_dispatch(AuthGateDecision.UNAUTHENTICATED) == ["login"]


def test_log_masks_email_on_denied(caplog):
    # AC-8: 拒否は WARNING で記録し、Email はマスク済みで出す。
    with caplog.at_level(logging.WARNING):
        _log_auth_event(
            AuthGateDecision.DENIED,
            "alice@example.com",
            mask_email=lambda _email: "a***@example.com",
        )
    record = caplog.records[-1]
    assert record.levelno == logging.WARNING
    message = record.getMessage()
    assert "a***@example.com" in message
    assert "alice@example.com" not in message


def test_log_success_is_info_and_masked(caplog):
    with caplog.at_level(logging.INFO):
        _log_auth_event(
            AuthGateDecision.AUTHORIZED,
            "admin@example.com",
            mask_email=lambda _email: "a***@example.com",
        )
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert "admin@example.com" not in record.getMessage()


def test_log_unauthenticated_without_email(caplog):
    # email が無い未認証でもマスク関数を呼ばず安全な表現で記録する。
    with caplog.at_level(logging.INFO):
        _log_auth_event(
            AuthGateDecision.UNAUTHENTICATED,
            None,
            mask_email=lambda _email: "should-not-be-called",
        )
    assert "should-not-be-called" not in caplog.records[-1].getMessage()


class _FakeUser:
    """`st.user` の代役。指定された属性のみを持ち、欠落属性は getattr 既定に委ねる。

    `is_logged_in` を省けば `render_auth_gate` の `getattr(..., False)` 既定・
    `bool(...)` 強制経路を検証できる。
    """

    def __init__(self, **attrs: object) -> None:
        for name, value in attrs.items():
            setattr(self, name, value)


class _FakeStreamlit:
    """`auth_gate_view` 内の `st` を差し替えるフェイク。

    描画 API の呼び出し・ボタン押下経路・login/logout の発火を記録し、Streamlit
    ランタイム無しで描画分岐の結線を観測できるようにする。`button` は構築時に与えた
    真偽値を返し、押下／非押下の双方を再現する。
    """

    def __init__(self, *, user: _FakeUser, button_returns: bool = False) -> None:
        self.user = user
        self._button_returns = button_returns
        self.login_called = False
        self.login_provider: str | None = None
        self.logout_called = False
        self.titles: list[str] = []
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.button_labels: list[str] = []

    def title(self, text: str) -> None:
        self.titles.append(text)

    def info(self, text: str) -> None:
        self.infos.append(text)

    def error(self, text: str) -> None:
        self.errors.append(text)

    def button(self, label: str) -> bool:
        self.button_labels.append(label)
        return self._button_returns

    def login(self, provider: str | None = None) -> None:
        self.login_called = True
        self.login_provider = provider

    def logout(self) -> None:
        self.logout_called = True


class _RenderSpy:
    """認可済み描画（CRUD 代役）が呼ばれたかを記録するスパイ。"""

    def __init__(self) -> None:
        self.called = False

    def __call__(self) -> None:
        self.called = True


def _mask(_email: str) -> str:
    return "a***@example.com"


def _install_fake_st(monkeypatch, fake: _FakeStreamlit) -> None:
    monkeypatch.setattr(auth_gate_view, "st", fake)


def test_render_auth_gate_authorized_renders_crud_and_logs_info(monkeypatch, caplog):
    # ログイン済み×管理者×検証済み → render_authorized が呼ばれ、INFO がマスク済みで出る。
    fake = _FakeStreamlit(
        user=_FakeUser(
            is_logged_in=True, email="alice@example.com", email_verified=True
        )
    )
    _install_fake_st(monkeypatch, fake)
    spy = _RenderSpy()
    with caplog.at_level(logging.INFO):
        render_auth_gate(
            AuthorizeAdminUseCase("alice@example.com"),
            render_authorized=spy,
            mask_email=_mask,
        )
    assert spy.called is True
    record = caplog.records[-1]
    assert record.levelno == logging.INFO
    assert "a***@example.com" in record.getMessage()
    assert "alice@example.com" not in record.getMessage()


def test_render_auth_gate_denied_skips_crud_and_logs_warning(monkeypatch, caplog):
    # ログイン済み×不一致 → render_authorized は呼ばれず拒否分岐・WARNING ログ。
    fake = _FakeStreamlit(
        user=_FakeUser(
            is_logged_in=True, email="intruder@example.com", email_verified=True
        )
    )
    _install_fake_st(monkeypatch, fake)
    spy = _RenderSpy()
    with caplog.at_level(logging.WARNING):
        render_auth_gate(
            AuthorizeAdminUseCase(_ADMIN),
            render_authorized=spy,
            mask_email=_mask,
        )
    assert spy.called is False
    assert fake.errors  # 拒否メッセージが提示される
    record = caplog.records[-1]
    assert record.levelno == logging.WARNING
    assert "intruder@example.com" not in record.getMessage()


def test_render_auth_gate_unverified_skips_crud(monkeypatch):
    # email 一致でも email_verified が True でなければ拒否（CRUD 非描画、AC-5）。
    fake = _FakeStreamlit(
        user=_FakeUser(is_logged_in=True, email=_ADMIN, email_verified=False)
    )
    _install_fake_st(monkeypatch, fake)
    spy = _RenderSpy()
    render_auth_gate(
        AuthorizeAdminUseCase(_ADMIN),
        render_authorized=spy,
        mask_email=_mask,
    )
    assert spy.called is False
    assert fake.errors


def test_render_auth_gate_unauthenticated_shows_login_not_crud(monkeypatch):
    # is_logged_in 属性欠落 → getattr 既定 False → ログイン分岐（CRUD 非描画）。
    fake = _FakeStreamlit(user=_FakeUser())
    _install_fake_st(monkeypatch, fake)
    spy = _RenderSpy()
    render_auth_gate(
        AuthorizeAdminUseCase(_ADMIN),
        render_authorized=spy,
        mask_email=_mask,
    )
    assert spy.called is False
    assert fake.titles == ["ログインが必要です"]
    assert "Google でログイン" in fake.button_labels


@pytest.mark.parametrize("pressed", [True, False])
def test_render_login_triggers_login_only_when_pressed(monkeypatch, pressed):
    fake = _FakeStreamlit(user=_FakeUser(), button_returns=pressed)
    _install_fake_st(monkeypatch, fake)
    _render_login()
    assert fake.titles == ["ログインが必要です"]
    assert fake.infos  # 案内文を提示する
    assert fake.login_called is pressed
    # 名前付きプロバイダ [auth.google] を起動するため "google" を渡す（引数なしは不可）。
    assert fake.login_provider == ("google" if pressed else None)


@pytest.mark.parametrize("pressed", [True, False])
def test_render_denied_offers_relogin_only_when_pressed(monkeypatch, pressed):
    fake = _FakeStreamlit(user=_FakeUser(), button_returns=pressed)
    _install_fake_st(monkeypatch, fake)
    _render_denied()
    assert fake.titles == ["アクセスが許可されていません"]
    assert fake.errors
    assert "別のアカウントでログインし直す" in fake.button_labels
    assert fake.logout_called is pressed


@pytest.mark.parametrize("pressed", [True, False])
def test_render_authorized_always_renders_crud_with_logout(monkeypatch, pressed):
    fake = _FakeStreamlit(user=_FakeUser(), button_returns=pressed)
    _install_fake_st(monkeypatch, fake)
    spy = _RenderSpy()
    _render_authorized(spy)
    assert spy.called is True  # 認可済みでは CRUD を必ず描画する
    assert "ログアウト" in fake.button_labels
    assert fake.logout_called is pressed


@pytest.mark.parametrize("pressed", [True, False])
def test_render_logout_calls_logout_only_when_pressed(monkeypatch, pressed):
    fake = _FakeStreamlit(user=_FakeUser(), button_returns=pressed)
    _install_fake_st(monkeypatch, fake)
    _render_logout("ログアウト")
    assert fake.button_labels == ["ログアウト"]
    assert fake.logout_called is pressed
