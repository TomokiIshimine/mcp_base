"""MySQL 接続設定（infrastructure 層）。

接続情報は環境変数から読み取り、infrastructure 層に閉じる。上位層（usecase/domain）
へ接続詳細を漏らさず、リポジトリ実装にのみ渡す。
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MySQLConfig:
    """MySQL への接続設定を保持する不変の値。"""

    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "MySQLConfig":
        """環境変数から接続設定を構築する。未設定時はローカル既定値を使う。"""
        return cls(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "app"),
            password=os.environ.get("MYSQL_PASSWORD", "app_password"),
            database=os.environ.get("MYSQL_DATABASE", "app_db"),
        )
