"""挨拶 CRUD のコントローラ（interface_adapter 層）。

usecase を起動し、view が扱いやすいプリミティブ（id と文字列のタプル列）へ変換する。
usecase 層の業務例外は OperationError へ翻訳し、view へドライバ非依存で伝える。
依存方向は interface_adapter -> usecase（外側 -> 内側）のみ。
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from interface_adapter.errors import OperationError
from usecase.errors import GreetingError
from usecase.manage_greetings_usecase import ManageGreetingsUseCase

logger = logging.getLogger(__name__)

T = TypeVar("T")

# usecase 層から伝わる、利用者へ提示可能な失敗。バリデーション失敗（ValueError）と
# 業務例外（GreetingError: 該当なし・永続化失敗等）をまとめて OperationError に翻訳する。
_PRESENTABLE_ERRORS = (ValueError, GreetingError)


class GreetingCrudController:
    """ManageGreetingsUseCase を起動し、view へ渡す結果を整える。"""

    def __init__(self, usecase: ManageGreetingsUseCase) -> None:
        self._usecase = usecase

    def list(self) -> list[tuple[int, str]]:
        """全挨拶を (id, message) のタプル列で返す。"""
        return self._run(
            lambda: [(r.id, r.message) for r in self._usecase.list_greetings()]
        )

    def create(self, message: str) -> None:
        """挨拶を作成する。"""
        self._run(lambda: self._usecase.create_greeting(message))

    def update(self, greeting_id: int, message: str) -> None:
        """指定 id の挨拶を更新する。"""
        self._run(lambda: self._usecase.update_greeting(greeting_id, message))

    def delete(self, greeting_id: int) -> None:
        """指定 id の挨拶を削除する。"""
        self._run(lambda: self._usecase.delete_greeting(greeting_id))

    @staticmethod
    def _run(action: Callable[[], T]) -> T:
        """usecase 操作を実行し、提示可能な例外を OperationError へ翻訳する。"""
        try:
            return action()
        except _PRESENTABLE_ERRORS as error:
            logger.warning("操作失敗: %s", error)
            raise OperationError(str(error)) from error
