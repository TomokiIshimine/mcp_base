"""GreetingPort の MySQL 具象実装（infrastructure 層）。

PyMySQL で MySQL に接続し、greetings テーブルから挨拶メッセージを取得する。
DB ドライバ依存はこの infrastructure 層に閉じ、usecase/domain は具象を知らない。
"""

import pymysql

from domain.greeting import Greeting
from infrastructure.config import MySQLConfig
from usecase.greeting_port import GreetingPort


class MySQLGreetingRepository(GreetingPort):
    """MySQL から挨拶メッセージを取得するリポジトリ。"""

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config

    def get(self) -> Greeting:
        """greetings テーブルの先頭行から挨拶を取得して返す。"""
        connection = pymysql.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT message FROM greetings ORDER BY id LIMIT 1")
                row = cursor.fetchone()
        finally:
            connection.close()

        if row is None:
            raise RuntimeError("greetings テーブルに行がありません")
        return Greeting(row[0])
