"""Streamlit エントリポイント（DI 合成ルート）。

依存配線のみを担い、画面描画・ビジネスロジックは同じ src/ 配下の 4 層に委譲する。
MySQL の greetings テーブルに対する CRUD 画面を描画する。
`streamlit run src/app.py` で起動する。
"""

import logging

import streamlit as st

from infrastructure.config import AuthConfig, MySQLConfig
from infrastructure.email_mask import mask_email
from infrastructure.logging_config import configure_logging
from infrastructure.mysql_greeting_crud_repository import MySQLGreetingCrudRepository
from interface_adapter.auth_gate_view import render_auth_gate
from interface_adapter.greeting_crud_controller import GreetingCrudController
from interface_adapter.greeting_crud_view import render_crud
from usecase.authorize_admin_usecase import AuthorizeAdminUseCase
from usecase.manage_greetings_usecase import ManageGreetingsUseCase

logger = logging.getLogger(__name__)


@st.cache_resource
def _build_repository() -> MySQLGreetingCrudRepository:
    """リポジトリ（＝接続プール）をプロセス内で 1 回だけ構築し再利用する。

    Streamlit はスクリプトを再実行のたびに評価するため、ここでキャッシュしないと
    操作のたびにプールを作り直すことになる。cache_resource で生成を一度に抑える。
    """
    return MySQLGreetingCrudRepository(MySQLConfig.from_env())


def main() -> None:
    """認証ゲート越しに greetings テーブルの CRUD 画面を描画する。"""
    configure_logging()
    # 設定不備（必須 env 欠如）はここで ConfigError として送出され、握りつぶさず
    # 起動を失敗させる（fail-fast）。認証設定（管理者 Email）の不備も同様に catch-all
    # の外で落とし、認可されていない状態で CRUD を描画させない。一方、描画中に想定外
    # の例外（業務例外に翻訳されないバグ等）が出た場合は、最上位で一度だけ捕捉して
    # ログに残しつつ、スタックトレースを画面に晒さない汎用メッセージへ落とす。
    auth_config = AuthConfig.from_env()
    authorize = AuthorizeAdminUseCase(auth_config.admin_email)
    repository = _build_repository()
    usecase = ManageGreetingsUseCase(repository)
    controller = GreetingCrudController(usecase)
    try:
        # 認可成立時のみ CRUD を描画する。マスク関数は infrastructure の具象を合成
        # ルートから注入し、interface_adapter が infrastructure を直接 import しない
        # 依存方向を保つ。
        render_auth_gate(
            authorize,
            render_authorized=lambda: render_crud(controller),
            mask_email=mask_email,
        )
    except Exception:
        logger.exception("画面描画中に想定外のエラーが発生しました")
        st.error("想定外のエラーが発生しました。時間をおいて再度お試しください。")


if __name__ == "__main__":
    main()
