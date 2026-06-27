"""GreetingCrudController の例外翻訳の単体テスト（usecase はスタブ注入）。"""

import pytest

from interface_adapter.errors import OperationError
from interface_adapter.greeting_crud_controller import GreetingCrudController
from usecase.errors import GreetingNotFoundError, RepositoryError


class _RaisingUseCase:
    """指定した例外を送出するだけのユースケーススタブ。"""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def list_greetings(self):
        raise self._error

    def create_greeting(self, message: str):
        raise self._error

    def update_greeting(self, greeting_id: int, message: str) -> None:
        raise self._error

    def delete_greeting(self, greeting_id: int) -> None:
        raise self._error


@pytest.mark.parametrize(
    "error",
    [
        ValueError("メッセージは空にできません"),
        GreetingNotFoundError("id=1 の挨拶が見つかりません"),
        RepositoryError("DB に接続できませんでした"),
    ],
)
def test_create_translates_presentable_errors_to_operation_error(error):
    controller = GreetingCrudController(_RaisingUseCase(error))

    with pytest.raises(OperationError) as excinfo:
        controller.create("Hello")

    assert str(excinfo.value) == str(error)


def test_list_translates_repository_error():
    controller = GreetingCrudController(_RaisingUseCase(RepositoryError("失敗")))

    with pytest.raises(OperationError):
        controller.list()


def test_unexpected_error_is_not_swallowed():
    controller = GreetingCrudController(_RaisingUseCase(KeyError("bug")))

    with pytest.raises(KeyError):
        controller.delete(1)
