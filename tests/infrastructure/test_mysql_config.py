"""MySQLConfig の環境変数パースの単体テスト（DB 非接続の純ロジック）。"""

import pytest

from infrastructure.config import ConfigError, MySQLConfig


def _set_required(monkeypatch):
    """必須 env（資格情報＋DB 名）を一通り設定する。"""
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DATABASE", "d")


def test_from_env_reads_all_values(monkeypatch):
    monkeypatch.setenv("MYSQL_HOST", "db")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DATABASE", "d")

    config = MySQLConfig.from_env()

    assert config.host == "db"
    assert config.port == 3307
    assert config.user == "u"
    assert config.password == "p"
    assert config.database == "d"


def test_from_env_defaults_host_and_port_when_unset(monkeypatch):
    # host/port は秘匿情報でないためローカル既定値にフォールバックする。
    _set_required(monkeypatch)
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("MYSQL_PORT", raising=False)

    config = MySQLConfig.from_env()

    assert config.host == "127.0.0.1"
    assert config.port == 3306


@pytest.mark.parametrize(
    "missing_key",
    ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"],
)
def test_from_env_fails_fast_when_required_env_missing(monkeypatch, missing_key):
    # 資格情報・DB 名が欠けたら弱い既定値で接続せず、起動時に落とす（fail-fast）。
    _set_required(monkeypatch)
    monkeypatch.delenv(missing_key, raising=False)

    with pytest.raises(ConfigError):
        MySQLConfig.from_env()


def test_from_env_fails_fast_when_required_env_empty(monkeypatch):
    # 空文字も「未設定」と同等に扱い、誤設定での接続を防ぐ。
    _set_required(monkeypatch)
    monkeypatch.setenv("MYSQL_PASSWORD", "")

    with pytest.raises(ConfigError):
        MySQLConfig.from_env()
