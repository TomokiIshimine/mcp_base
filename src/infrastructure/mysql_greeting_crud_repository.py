"""GreetingCrudPort の MySQL 具象実装（infrastructure 層）。

PyMySQL で MySQL に接続し、greetings テーブルへ CRUD を行う。
DB ドライバ依存はこの infrastructure 層に閉じる。
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pymysql

from domain.greeting_record import GreetingRecord
from infrastructure.config import MySQLConfig
from usecase.greeting_crud_port import GreetingCrudPort


class MySQLGreetingCrudRepository(GreetingCrudPort):
    """MySQL の greetings テーブルに対する CRUD リポジトリ。"""

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config

    @contextmanager
    def _cursor(self) -> Iterator[pymysql.cursors.Cursor]:
        """接続を確立してカーソルを払い出し、終了時に確実に閉じる（autocommit 有効）。"""
        connection = pymysql.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                yield cursor
        finally:
            connection.close()

    def list_all(self) -> list[GreetingRecord]:
        with self._cursor() as cursor:
            cursor.execute("SELECT id, message FROM greetings ORDER BY id")
            rows = cursor.fetchall()
        return [GreetingRecord(row[0], row[1]) for row in rows]

    def create(self, message: str) -> GreetingRecord:
        with self._cursor() as cursor:
            cursor.execute("INSERT INTO greetings (message) VALUES (%s)", (message,))
            new_id = cursor.lastrowid
        return GreetingRecord(new_id, message)

    def update(self, greeting_id: int, message: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE greetings SET message = %s WHERE id = %s",
                (message, greeting_id),
            )

    def delete(self, greeting_id: int) -> None:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM greetings WHERE id = %s", (greeting_id,))
