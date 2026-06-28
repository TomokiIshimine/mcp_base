"""AuthConfig の環境変数パースと機微情報抑止の単体テスト（D-4 / AC-1）。"""

import pytest

from infrastructure.config import AuthConfig, ConfigError

_ADMIN = "admin@example.com"


def test_from_env_reads_admin_email(monkeypatch):
    # 正常系: 管理者 Email が設定済みなら値を保持して構築成功。
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", _ADMIN)

    config = AuthConfig.from_env()

    assert config.admin_email == _ADMIN


def test_from_env_fails_fast_when_admin_email_missing(monkeypatch):
    # 異常系（AC-1）: 未設定なら弱い既定で誰でも認可せず起動を止める。
    monkeypatch.delenv("AUTH_ADMIN_EMAIL", raising=False)

    with pytest.raises(ConfigError):
        AuthConfig.from_env()


def test_from_env_fails_fast_when_admin_email_empty(monkeypatch):
    # 異常系（AC-1）: 空文字も未設定と同等に扱う。
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", "")

    with pytest.raises(ConfigError):
        AuthConfig.from_env()


def test_repr_does_not_leak_admin_email(monkeypatch):
    # 機微情報抑止（回帰防止）: repr/str に管理者 Email 平文が現れない。
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", _ADMIN)

    config = AuthConfig.from_env()

    assert _ADMIN not in repr(config)
    assert _ADMIN not in str(config)


def test_config_error_message_does_not_leak_admin_email(monkeypatch):
    # 例外メッセージにも管理者 Email 平文を載せない（未設定時は env 名のみ）。
    monkeypatch.delenv("AUTH_ADMIN_EMAIL", raising=False)

    with pytest.raises(ConfigError) as exc_info:
        AuthConfig.from_env()

    assert _ADMIN not in str(exc_info.value)
