"""GreetUseCase の単体テスト。

フェイクの GreetingPort 実装を注入し、execute() が期待どおりの
Greeting を返すことを検証する。infrastructure 層には依存しない。
"""

from domain.greeting import Greeting
from usecase.greet_usecase import GreetUseCase
from usecase.greeting_port import GreetingPort


class FakeGreetingPort(GreetingPort):
    """テスト用の GreetingPort 実装。注入された Greeting をそのまま返す。"""

    def __init__(self, greeting: Greeting) -> None:
        self._greeting = greeting

    def get(self) -> Greeting:
        return self._greeting


def test_execute_returns_injected_greeting() -> None:
    expected = Greeting("Hello, World")
    usecase = GreetUseCase(FakeGreetingPort(expected))

    result = usecase.execute()

    assert result == expected
    assert result.message == "Hello, World"
