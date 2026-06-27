"""実 MySQL を介した MySQLGreetingCrudRepository の統合テスト（重い／DB 必須）。

単体テスト（フェイクプール）では検証できない「実ドライバ＋実 DB を通した経路」を
確認する。接続情報は環境変数（MYSQL_*）から取得する。実行には起動済みの MySQL と
greetings テーブル（db/init/01_schema.sql 相当）が必要。

既定の軽量実行からは integration マーカーで除外され、make test-integration および
PR の CI でのみ実行される。
"""

import pymysql
import pytest

from infrastructure.config import MySQLConfig
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from usecase.errors import GreetingNotFoundError, InvalidGreetingError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def config() -> MySQLConfig:
    return MySQLConfig.from_env()


@pytest.fixture
def repository(config: MySQLConfig) -> MySQLGreetingCrudRepository:
    return MySQLGreetingCrudRepository(config)


@pytest.fixture(autouse=True)
def _clean_greetings(config: MySQLConfig):
    """各テスト前に greetings を空にし、テスト間の独立性を担保する。

    テーブルは外部（compose の初期化 SQL / CI の schema 適用）で用意済みを前提とし、
    ここでは中身だけ消す（schema の二重管理を避ける）。
    """
    connection = pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM greetings")
    finally:
        connection.close()
    yield


def test_create_then_list_roundtrips(repository: MySQLGreetingCrudRepository):
    created = repository.create("hello")

    rows = repository.list_all()
    assert [(r.id, r.message) for r in rows] == [(created.id, "hello")]


def test_update_reflects_and_unknown_id_raises(
    repository: MySQLGreetingCrudRepository,
):
    created = repository.create("old")

    repository.update(created.id, "new")
    assert repository.list_all()[0].message == "new"

    with pytest.raises(GreetingNotFoundError):
        repository.update(created.id + 10_000, "x")


def test_delete_removes_and_unknown_id_raises(
    repository: MySQLGreetingCrudRepository,
):
    created = repository.create("bye")

    repository.delete(created.id)
    assert repository.list_all() == []

    with pytest.raises(GreetingNotFoundError):
        repository.delete(created.id)


def test_too_long_message_translates_to_invalid_greeting(
    repository: MySQLGreetingCrudRepository,
):
    # アプリ検証をすり抜けた長さ超過が、実 DB の VARCHAR(255) 制約（strict mode）で
    # DataError となり、infrastructure 層で InvalidGreetingError へ翻訳されること。
    with pytest.raises(InvalidGreetingError):
        repository.create("x" * 256)
