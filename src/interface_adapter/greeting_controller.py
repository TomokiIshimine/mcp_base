"""挨拶コントローラ（interface_adapter 層）。

usecase を起動し、view 用の結果（挨拶文字列）を返す。
依存方向は interface_adapter -> usecase（外側 -> 内側）のみ。
"""

from usecase.greet_usecase import GreetUseCase


class GreetingController:
    """GreetUseCase を起動し、view へ渡す挨拶文字列を返すコントローラ。"""

    def __init__(self, greet_usecase: GreetUseCase) -> None:
        self._greet_usecase = greet_usecase

    def handle(self) -> str:
        """usecase を実行し、挨拶メッセージ文字列を返す。"""
        greeting = self._greet_usecase.execute()
        return greeting.message
