"""GreetingCrudPort の MySQL 具象実装（infrastructure 層）。

PyMySQL で MySQL に接続し、greetings テーブルへ CRUD を行う。
DB ドライバ依存はこの infrastructure 層に閉じ、ドライバ固有の例外は
usecase 層の業務例外（RepositoryError 等）へ翻訳して上位へ伝える。
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pymysql

from domain.greeting_record import GreetingRecord
from infrastructure.config import MySQLConfig
from usecase.errors import GreetingNotFoundError, RepositoryError
from usecase.greeting_crud_port import GreetingCrudPort


class MySQLGreetingCrudRepository(GreetingCrudPort):
    """MySQL の greetings テーブルに対する CRUD リポジトリ。"""

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config

    @contextmanager
    def _cursor(self) -> Iterator[pymysql.cursors.Cursor]:
        """接続を確立してカーソルを払い出し、終了時に確実に閉じる（autocommit 有効）。

        接続・SQL 実行で生じた pymysql.Error は RepositoryError へ翻訳する。
        """
        try:
            connection = pymysql.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database,
                autocommit=True,
            )
        except pymysql.Error as error:
            raise RepositoryError("DB に接続できませんでした") from error
        try:
            with connection.cursor() as cursor:
                yield cursor
        except pymysql.Error as error:
            raise RepositoryError("DB 操作に失敗しました") from error
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
        if new_id is None:
            raise RepositoryError("作成した行の id を取得できませんでした")
        return GreetingRecord(new_id, message)

    def update(self, greeting_id: int, message: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE greetings SET message = %s WHERE id = %s",
                (message, greeting_id),
            )
            if cursor.rowcount == 0:
                raise GreetingNotFoundError(f"id={greeting_id} の挨拶が見つかりません")

    def delete(self, greeting_id: int) -> None:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM greetings WHERE id = %s", (greeting_id,))
            if cursor.rowcount == 0:
                raise GreetingNotFoundError(f"id={greeting_id} の挨拶が見つかりません")
