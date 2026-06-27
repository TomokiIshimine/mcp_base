"""Streamlit エントリポイント（DI 合成ルート）。

依存配線のみを担い、画面描画・ビジネスロジックは src/ の 4 層に委譲する。
GREETING_BACKEND=mysql のときは MySQL の greetings テーブルに対する CRUD 画面を、
それ以外（static）は DB 未接続の Hello World 表示を描画する。
`streamlit run app.py` で起動する。
"""

import os

from infrastructure.config import MySQLConfig
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from infrastructure.static_greeting_repository import StaticGreetingRepository
from interface_adapter.greeting_controller import GreetingController
from interface_adapter.greeting_crud_controller import GreetingCrudController
from interface_adapter.greeting_crud_view import render_crud
from interface_adapter.greeting_view import render
from usecase.greet_usecase import GreetUseCase
from usecase.manage_greetings_usecase import ManageGreetingsUseCase


def _render_mysql_crud() -> None:
    """MySQL バックエンド: greetings テーブルの CRUD 画面を描画する。"""
    repository = MySQLGreetingCrudRepository(MySQLConfig.from_env())
    usecase = ManageGreetingsUseCase(repository)
    controller = GreetingCrudController(usecase)
    render_crud(controller)


def _render_static_greeting() -> None:
    """static バックエンド: DB 未接続の Hello World を描画する。"""
    repository = StaticGreetingRepository()
    usecase = GreetUseCase(repository)
    controller = GreetingController(usecase)
    render(controller.handle())


def main() -> None:
    """環境変数 GREETING_BACKEND に応じて描画内容を切り替える。"""
    backend = os.environ.get("GREETING_BACKEND", "static").lower()
    if backend == "mysql":
        _render_mysql_crud()
    else:
        _render_static_greeting()


if __name__ == "__main__":
    main()
