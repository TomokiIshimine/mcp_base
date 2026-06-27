"""Streamlit エントリポイント（DI 合成ルート）。

依存配線のみを担い、画面描画・ビジネスロジックは src/ の 4 層に委譲する。
MySQL の greetings テーブルに対する CRUD 画面を描画する。
`streamlit run app.py` で起動する。
"""

from infrastructure.config import MySQLConfig
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from interface_adapter.greeting_crud_controller import GreetingCrudController
from interface_adapter.greeting_crud_view import render_crud
from usecase.manage_greetings_usecase import ManageGreetingsUseCase


def main() -> None:
    """greetings テーブルの CRUD 画面を描画する。"""
    repository = MySQLGreetingCrudRepository(MySQLConfig.from_env())
    usecase = ManageGreetingsUseCase(repository)
    controller = GreetingCrudController(usecase)
    render_crud(controller)


if __name__ == "__main__":
    main()
