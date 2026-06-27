"""MySQLConfig の環境変数パースの単体テスト（DB 非接続の純ロジック）。"""

from infrastructure.config import MySQLConfig


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


def test_from_env_uses_defaults_when_unset(monkeypatch):
    for key in (
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ):
        monkeypatch.delenv(key, raising=False)

    config = MySQLConfig.from_env()

    assert config.host == "127.0.0.1"
    assert config.port == 3306
    assert config.database == "app_db"
