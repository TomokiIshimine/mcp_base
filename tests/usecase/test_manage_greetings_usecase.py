"""ManageGreetingsUseCase の単体テスト（フェイクポート注入、DB 非接続）。"""

import pytest

from domain.greeting_record import GreetingRecord
from usecase.greeting_crud_port import GreetingCrudPort
from usecase.manage_greetings_usecase import ManageGreetingsUseCase


class FakeGreetingCrudPort(GreetingCrudPort):
    """インメモリで CRUD を再現するフェイクポート。"""

    def __init__(self) -> None:
        self._items: dict[int, str] = {}
        self._sequence = 0

    def list_all(self) -> list[GreetingRecord]:
        return [GreetingRecord(i, m) for i, m in sorted(self._items.items())]

    def create(self, message: str) -> GreetingRecord:
        self._sequence += 1
        self._items[self._sequence] = message
        return GreetingRecord(self._sequence, message)

    def update(self, greeting_id: int, message: str) -> None:
        self._items[greeting_id] = message

    def delete(self, greeting_id: int) -> None:
        self._items.pop(greeting_id, None)


def test_create_then_list_returns_record():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())

    created = usecase.create_greeting("Hello")

    assert created.id == 1
    assert usecase.list_greetings() == [GreetingRecord(1, "Hello")]


def test_update_changes_message():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())
    usecase.create_greeting("Hello")

    usecase.update_greeting(1, "Updated")

    assert usecase.list_greetings() == [GreetingRecord(1, "Updated")]


def test_delete_removes_record():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())
    usecase.create_greeting("Hello")

    usecase.delete_greeting(1)

    assert usecase.list_greetings() == []


def test_create_rejects_blank_message():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())

    with pytest.raises(ValueError):
        usecase.create_greeting("   ")


def test_create_rejects_too_long_message():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())

    with pytest.raises(ValueError):
        usecase.create_greeting("A" * 256)


def test_create_accepts_max_length_message():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())

    created = usecase.create_greeting("A" * 255)

    assert created.message == "A" * 255


def test_update_rejects_too_long_message():
    usecase = ManageGreetingsUseCase(FakeGreetingCrudPort())
    usecase.create_greeting("Hello")

    with pytest.raises(ValueError):
        usecase.update_greeting(1, "A" * 256)
