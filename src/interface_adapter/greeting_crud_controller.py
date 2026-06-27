"""挨拶 CRUD のコントローラ（interface_adapter 層）。

usecase を起動し、view が扱いやすいプリミティブ（id と文字列のタプル列）へ変換する。
依存方向は interface_adapter -> usecase（外側 -> 内側）のみ。
"""

from usecase.manage_greetings_usecase import ManageGreetingsUseCase


class GreetingCrudController:
    """ManageGreetingsUseCase を起動し、view へ渡す結果を整える。"""

    def __init__(self, usecase: ManageGreetingsUseCase) -> None:
        self._usecase = usecase

    def list(self) -> list[tuple[int, str]]:
        """全挨拶を (id, message) のタプル列で返す。"""
        return [(r.id, r.message) for r in self._usecase.list_greetings()]

    def create(self, message: str) -> None:
        """挨拶を作成する。"""
        self._usecase.create_greeting(message)

    def update(self, greeting_id: int, message: str) -> None:
        """指定 id の挨拶を更新する。"""
        self._usecase.update_greeting(greeting_id, message)

    def delete(self, greeting_id: int) -> None:
        """指定 id の挨拶を削除する。"""
        self._usecase.delete_greeting(greeting_id)
