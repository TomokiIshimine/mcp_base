"""挨拶を取得して返すアプリケーションロジック。"""

from domain.greeting import Greeting
from usecase.greeting_port import GreetingPort


class GreetUseCase:
    """ポート経由で挨拶を取得するユースケース。"""

    def __init__(self, greeting_port: GreetingPort) -> None:
        self._greeting_port = greeting_port

    def execute(self) -> Greeting:
        """挨拶を取得して返す。"""
        return self._greeting_port.get()
