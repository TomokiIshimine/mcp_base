"""挨拶 CRUD の Streamlit 画面描画を担う view（interface_adapter 層）。

一覧表示・新規作成・更新・削除の UI を構築し、操作を controller へ委譲する。
描画責務をここに集約し、controller 以外（usecase/infrastructure）には依存しない。
"""

from collections.abc import Callable

import streamlit as st

from interface_adapter.errors import InvalidOperationError, SystemFailureError
from interface_adapter.greeting_crud_controller import GreetingCrudController


def render_crud(controller: GreetingCrudController) -> None:
    """挨拶 CRUD 画面を描画する。"""
    st.title("Greetings CRUD")
    st.caption("MySQL の greetings テーブルを操作します。")

    try:
        rows = controller.list_all()
    except InvalidOperationError as error:
        st.warning(str(error))
        return
    except SystemFailureError as error:
        st.error(str(error))
        return

    _render_list(rows)
    _render_create_form(controller)
    if rows:
        _render_update_form(controller, rows)
        _render_delete(controller, rows)


def _render_list(rows: list[tuple[int, str]]) -> None:
    """挨拶の一覧を表示する。"""
    st.subheader("一覧")
    if rows:
        st.table([{"id": gid, "message": message} for gid, message in rows])
    else:
        st.info("レコードがありません。下のフォームから作成してください。")


def _render_create_form(controller: GreetingCrudController) -> None:
    """新規作成フォームを描画する。"""
    st.subheader("新規作成")
    with st.form("create_form", clear_on_submit=True):
        new_message = st.text_input("メッセージ")
        if st.form_submit_button("作成") and _guard(controller.create, new_message):
            st.success("作成しました。")
            st.rerun()


def _render_update_form(
    controller: GreetingCrudController, rows: list[tuple[int, str]]
) -> None:
    """更新フォームを描画する。rows が空でないことを前提とする。"""
    ids = [gid for gid, _ in rows]
    message_by_id = {gid: message for gid, message in rows}

    st.subheader("更新")
    update_id = st.selectbox("更新する id", ids, key="update_id")
    with st.form("update_form"):
        updated_message = st.text_input(
            "新しいメッセージ", value=message_by_id[update_id]
        )
        if st.form_submit_button("更新") and _guard(
            controller.update, update_id, updated_message
        ):
            st.success("更新しました。")
            st.rerun()


def _render_delete(
    controller: GreetingCrudController, rows: list[tuple[int, str]]
) -> None:
    """削除 UI を描画する。rows が空でないことを前提とする。"""
    ids = [gid for gid, _ in rows]

    st.subheader("削除")
    delete_id = st.selectbox("削除する id", ids, key="delete_id")
    if st.button("削除") and _guard(controller.delete, delete_id):
        st.success("削除しました。")
        st.rerun()


def _guard(action: Callable[..., None], *args: object) -> bool:
    """controller 操作を実行し、失敗時は原因別に表示して False を返す。

    利用者起因は警告（再操作で直る見込み）、システム障害はエラーとして出し分ける。
    """
    try:
        action(*args)
    except InvalidOperationError as error:
        st.warning(str(error))
        return False
    except SystemFailureError as error:
        st.error(str(error))
        return False
    return True
