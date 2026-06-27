"""MySQL 接続設定（infrastructure 層）。

接続情報は環境変数から読み取り、infrastructure 層に閉じる。上位層（usecase/domain）
へ接続詳細を漏らさず、リポジトリ実装にのみ渡す。
"""

import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    """設定不備で起動を継続できないことを表す（fail-fast 用の例外）。"""


def _require_env(name: str) -> str:
    """必須の環境変数を取得する。未設定・空文字なら起動を止める。

    弱い既定資格情報で意図せず接続を試みるより、誤設定を起動時に検出して
    落とす方が安全という判断（fail-fast）。`.env` 等での明示設定を強制する。
    """
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            f"必須の環境変数 {name} が未設定です。.env 等で設定してください。"
        )
    return value


@dataclass(frozen=True)
class MySQLConfig:
    """MySQL への接続設定を保持する不変の値。"""

    host: str
    port: int
    user: str
    # repr/ログ出力に展開させず、パスワード漏洩を構造的に防ぐ。
    password: str = field(repr=False)
    database: str

    @classmethod
    def from_env(cls) -> "MySQLConfig":
        """環境変数から接続設定を構築する。

        資格情報（user/password）と接続先 DB 名は秘匿・本番固有の値であり、
        弱い既定値で意図せぬ接続を招かないよう必須とする（未設定なら ConfigError
        で起動失敗）。host/port は秘匿情報でなくローカル開発の利便性が勝るため、
        未設定時はローカル既定値（127.0.0.1:3306）にフォールバックする。
        """
        return cls(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=_require_env("MYSQL_USER"),
            password=_require_env("MYSQL_PASSWORD"),
            database=_require_env("MYSQL_DATABASE"),
        )
