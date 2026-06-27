from domain.greeting import Greeting


def test_greeting_holds_message() -> None:
    greeting = Greeting("Hello, World")

    assert greeting.message == "Hello, World"


def test_greeting_equality() -> None:
    assert Greeting("Hello, World") == Greeting("Hello, World")
