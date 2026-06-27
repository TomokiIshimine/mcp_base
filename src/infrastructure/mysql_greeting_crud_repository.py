"""GreetingCrudPort の MySQL 具象実装（infrastructure 層）。

PyMySQL で MySQL に接続し、greetings テーブルへ CRUD を行う。
DB ドライバ依存はこの infrastructure 層に閉じ、ドライバ固有の例外は
usecase 層の業務例外（RepositoryError 等）へ翻訳して上位へ伝える。
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pymysql
from dbutils.pooled_db import PooledDB

from domain.greeting_record import GreetingRecord
from infrastructure.config import MySQLConfig
from usecase.errors import (
    GreetingNotFoundError,
    InvalidGreetingError,
    RepositoryError,
)
from usecase.greeting_crud_port import GreetingCrudPort

logger = logging.getLogger(__name__)

# プールが保持する物理接続の上限。Streamlit の同時セッション数に対する目安。
_MAX_CONNECTIONS = 5


class MySQLGreetingCrudRepository(GreetingCrudPort):
    """MySQL の greetings テーブルに対する CRUD リポジトリ。

    接続はコネクションプール（PooledDB）から借り、操作後にプールへ返却する。
    操作ごとに物理接続を張り直さないため、Streamlit の再実行コストを抑えられる。
    プールはスレッドセーフで、複数セッションからの同時利用に耐える。
    """

    def __init__(self, config: MySQLConfig) -> None:
        # mincached=0（既定）のため、プール生成時点では物理接続を確立しない。
        # 実接続は connection() 払い出し時に遅延確立され、ping=1 で死活確認する。
        self._pool = PooledDB(
            creator=pymysql,
            maxconnections=_MAX_CONNECTIONS,
            blocking=True,
            ping=1,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            autocommit=True,
        )

    @contextmanager
    def _cursor(
        self, cursor_class: type[pymysql.cursors.Cursor] | None = None
    ) -> Iterator[pymysql.cursors.Cursor]:
        """プールから接続を借りてカーソルを払い出し、終了時にプールへ返却する。

        cursor_class を渡すとそのカーソル種別（例: DictCursor）で払い出す。
        例外はドライバ非依存な業務例外へ翻訳する: DB 制約違反（長さ超過等）は
        利用者起因の InvalidGreetingError、それ以外の接続・実行失敗は
        システム障害の RepositoryError とする。
        """
        try:
            connection = self._pool.connection()
        except pymysql.Error as error:
            logger.exception("DB 接続に失敗")
            raise RepositoryError("DB に接続できませんでした") from error
        try:
            with connection.cursor(cursor_class) as cursor:
                yield cursor
        except (pymysql.err.DataError, pymysql.err.IntegrityError) as error:
            # アプリ側バリデーションをすり抜けた入力が DB 制約に当たったケース。
            # 利用者の再操作で解消し得るため、システム障害とは区別する。
            logger.warning("DB 制約違反: %s", error)
            raise InvalidGreetingError(
                "入力値が制約に反するため保存できませんでした"
            ) from error
        except pymysql.Error as error:
            logger.exception("DB 操作に失敗")
            raise RepositoryError("DB 操作に失敗しました") from error
        finally:
            # PooledDB の接続は close() でプールへ返却される（物理切断ではない）。
            connection.close()

    def list_all(self) -> list[GreetingRecord]:
        # DictCursor でカラム名アクセスし、SELECT の列順への暗黙依存を避ける。
        with self._cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT id, message FROM greetings ORDER BY id")
            rows = cursor.fetchall()
        return [GreetingRecord(row["id"], row["message"]) for row in rows]

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
