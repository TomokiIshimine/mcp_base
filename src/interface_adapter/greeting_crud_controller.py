"""挨拶 CRUD のコントローラ（interface_adapter 層）。

usecase を起動し、view が扱いやすいプリミティブ（id と文字列のタプル列）へ変換する。
usecase 層の業務例外は OperationError へ翻訳し、view へドライバ非依存で伝える。
依存方向は interface_adapter -> usecase（外側 -> 内側）のみ。
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from interface_adapter.errors import InvalidOperationError, SystemFailureError
from usecase.errors import (
    GreetingNotFoundError,
    InvalidGreetingError,
    RepositoryError,
)
from usecase.manage_greetings_usecase import ManageGreetingsUseCase

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 利用者起因の失敗。バリデーション失敗（ValueError）・対象不在（NotFound）・DB 制約
# 違反（InvalidGreetingError）を、再操作で直り得る InvalidOperationError へ翻訳する。
_USER_ERRORS = (ValueError, GreetingNotFoundError, InvalidGreetingError)


class GreetingCrudController:
    """ManageGreetingsUseCase を起動し、view へ渡す結果を整える。"""

    def __init__(self, usecase: ManageGreetingsUseCase) -> None:
        self._usecase = usecase

    def list_all(self) -> list[tuple[int, str]]:
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
        """usecase 操作を実行し、提示可能な例外を原因別の OperationError へ翻訳する。

        利用者起因（入力不正・対象不在）は InvalidOperationError、永続化失敗は
        SystemFailureError へ振り分ける。infrastructure が付けた利用者向け文言を
        そのまま使うため、メッセージは差し替えない。
        """
        try:
            return action()
        except _USER_ERRORS as error:
            logger.warning("操作失敗（利用者起因）: %s", error)
            raise InvalidOperationError(str(error)) from error
        except RepositoryError as error:
            logger.error("操作失敗（システム障害）: %s", error)
            raise SystemFailureError(str(error)) from error
