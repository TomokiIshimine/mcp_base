"""MySQLGreetingCrudRepository の単体テスト（プールをフェイク化、DB 非接続）。

infrastructure 層の核心はドライバ固有例外の業務例外への翻訳と、rowcount/
lastrowid に基づく分岐である。実 MySQL を立てず、PooledDB をフェイクに差し替えて
これらの分岐を網羅する。pymysql の例外型のみ本物を用いる（翻訳条件の対象だから）。
"""

import pymysql
import pytest

from domain.greeting_record import GreetingRecord
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from usecase.errors import (
    GreetingNotFoundError,
    InvalidGreetingError,
    RepositoryError,
)


class _FakeCursor:
    """execute / fetchall / lastrowid / rowcount を模すフェイクカーソル。

    execute 時に送出する例外（execute_error）と、fetchall の戻り値・lastrowid・
    rowcount をテストごとに注入できる。with 文に対応する。
    """

    def __init__(
        self,
        *,
        rows: list[dict] | None = None,
        lastrowid: int | None = None,
        rowcount: int = 1,
        execute_error: Exception | None = None,
    ) -> None:
        self._rows = rows or []
        self.lastrowid = lastrowid
        self.rowcount = rowcount
        self._execute_error = execute_error
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))
        if self._execute_error is not None:
            raise self._execute_error

    def fetchall(self) -> list[dict]:
        return self._rows


class _FakeConnection:
    """cursor() でフェイクカーソルを返し、close() の呼び出しを記録する接続。"""

    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False
        self.cursor_class_used: type | None = None

    def cursor(self, cursor_class: type | None = None) -> _FakeCursor:
        self.cursor_class_used = cursor_class
        return self._cursor

    def close(self) -> None:
        self.closed = True


class _FakePool:
    """connection() でフェイク接続を払い出すプール。取得失敗の注入も可能。"""

    def __init__(
        self,
        connection: _FakeConnection | None = None,
        *,
        connect_error: Exception | None = None,
    ) -> None:
        self._connection = connection
        self._connect_error = connect_error

    def connection(self) -> _FakeConnection:
        if self._connect_error is not None:
            raise self._connect_error
        assert self._connection is not None
        return self._connection


def _make_repository(pool: _FakePool) -> MySQLGreetingCrudRepository:
    """PooledDB を生成させず、フェイクプールを注入したリポジトリを作る。

    __new__ で __init__（PooledDB 構築）を回避し、_pool だけを差し替える。
    実 DB 接続を一切行わずに CRUD メソッドの分岐を検証するための足場。
    """
    repository = MySQLGreetingCrudRepository.__new__(MySQLGreetingCrudRepository)
    repository._pool = pool
    return repository


def test_list_all_maps_rows_to_records_and_uses_dict_cursor():
    cursor = _FakeCursor(rows=[{"id": 1, "message": "a"}, {"id": 2, "message": "b"}])
    connection = _FakeConnection(cursor)
    repository = _make_repository(_FakePool(connection))

    result = repository.list_all()

    assert result == [GreetingRecord(1, "a"), GreetingRecord(2, "b")]
    # 列順依存を避けるため DictCursor で払い出していること。
    assert connection.cursor_class_used is pymysql.cursors.DictCursor
    assert connection.closed is True


def test_create_returns_record_with_lastrowid():
    cursor = _FakeCursor(lastrowid=42)
    connection = _FakeConnection(cursor)
    repository = _make_repository(_FakePool(connection))

    created = repository.create("hi")

    assert created == GreetingRecord(42, "hi")
    # パラメータ化クエリで渡していること（SQL インジェクション防止の確認）。
    sql, params = cursor.executed[0]
    assert "INSERT INTO greetings" in sql
    assert params == ("hi",)


def test_create_raises_when_lastrowid_missing():
    cursor = _FakeCursor(lastrowid=None)
    repository = _make_repository(_FakePool(_FakeConnection(cursor)))

    with pytest.raises(RepositoryError):
        repository.create("hi")


def test_update_succeeds_when_row_affected():
    cursor = _FakeCursor(rowcount=1)
    connection = _FakeConnection(cursor)
    repository = _make_repository(_FakePool(connection))

    repository.update(1, "new")

    sql, params = cursor.executed[0]
    assert "UPDATE greetings" in sql
    assert params == ("new", 1)
    assert connection.closed is True


def test_update_unknown_id_raises_not_found():
    cursor = _FakeCursor(rowcount=0)
    repository = _make_repository(_FakePool(_FakeConnection(cursor)))

    with pytest.raises(GreetingNotFoundError):
        repository.update(999, "new")


def test_delete_succeeds_when_row_affected():
    cursor = _FakeCursor(rowcount=1)
    repository = _make_repository(_FakePool(_FakeConnection(cursor)))

    repository.delete(1)

    sql, params = cursor.executed[0]
    assert "DELETE FROM greetings" in sql
    assert params == (1,)


def test_delete_unknown_id_raises_not_found():
    cursor = _FakeCursor(rowcount=0)
    repository = _make_repository(_FakePool(_FakeConnection(cursor)))

    with pytest.raises(GreetingNotFoundError):
        repository.delete(999)


def test_connection_acquire_failure_translates_to_repository_error():
    pool = _FakePool(connect_error=pymysql.OperationalError("can't connect"))
    repository = _make_repository(pool)

    with pytest.raises(RepositoryError):
        repository.list_all()


@pytest.mark.parametrize(
    "driver_error",
    [
        pymysql.err.DataError("Data too long"),
        pymysql.err.IntegrityError("constraint"),
    ],
)
def test_constraint_violation_translates_to_invalid_greeting_error(driver_error):
    cursor = _FakeCursor(execute_error=driver_error)
    connection = _FakeConnection(cursor)
    repository = _make_repository(_FakePool(connection))

    with pytest.raises(InvalidGreetingError):
        repository.create("x")
    # 翻訳後も接続はプールへ返却される（リーク防止）。
    assert connection.closed is True


def test_other_driver_error_translates_to_repository_error():
    cursor = _FakeCursor(execute_error=pymysql.err.OperationalError("deadlock"))
    connection = _FakeConnection(cursor)
    repository = _make_repository(_FakePool(connection))

    with pytest.raises(RepositoryError):
        repository.update(1, "x")
    assert connection.closed is True
