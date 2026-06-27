"""GreetingPort の具象実装（DB 未接続の静的リポジトリ）。

最小機能では MySQL に接続せず、静的な "Hello, World" を返す。将来の
MySQL ドライバ（PyMySQL）依存はこの infrastructure 層に閉じる。
"""

from domain.greeting import Greeting
from usecase.greeting_port import GreetingPort


class StaticGreetingRepository(GreetingPort):
    """常に "Hello, World" を返す静的リポジトリ。"""

    def get(self) -> Greeting:
        return Greeting("Hello, World")
