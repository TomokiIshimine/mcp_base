"""Streamlit エントリポイント（DI 合成ルート）。

依存配線のみを担い、画面描画・ビジネスロジックは src/ の 4 層に委譲する。
MySQL の greetings テーブルに対する CRUD 画面を描画する。
`streamlit run app.py` で起動する。
"""

import streamlit as st

from infrastructure.config import MySQLConfig
from infrastructure.logging_config import configure_logging
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from interface_adapter.greeting_crud_controller import GreetingCrudController
from interface_adapter.greeting_crud_view import render_crud
from usecase.manage_greetings_usecase import ManageGreetingsUseCase


@st.cache_resource
def _build_repository() -> MySQLGreetingCrudRepository:
    """リポジトリ（＝接続プール）をプロセス内で 1 回だけ構築し再利用する。

    Streamlit はスクリプトを再実行のたびに評価するため、ここでキャッシュしないと
    操作のたびにプールを作り直すことになる。cache_resource で生成を一度に抑える。
    """
    return MySQLGreetingCrudRepository(MySQLConfig.from_env())


def main() -> None:
    """greetings テーブルの CRUD 画面を描画する。"""
    configure_logging()
    repository = _build_repository()
    usecase = ManageGreetingsUseCase(repository)
    controller = GreetingCrudController(usecase)
    render_crud(controller)


if __name__ == "__main__":
    main()
