"""greeting_crud_view の描画分岐テスト（streamlit.testing の AppTest を使用）。

実 DB・実ブラウザを介さず、controller をスタブ化して render_crud の描画分岐を
検証する。特に「一覧取得が失敗しても作成フォームは描画される」（C-2）という
フェーズ②の UX 改善を回帰として固定する。
"""

from collections.abc import Sequence

from streamlit.testing.v1 import AppTest

from interface_adapter.errors import InvalidOperationError, SystemFailureError
from interface_adapter.greeting_crud_controller import GreetingView


class _StubController:
    """GreetingCrudController の振る舞いを模すスタブ（duck typing）。

    list_all の戻り値・送出例外を注入できる。create/update/delete は呼ばれても
    何もしない（初期描画では submit されないため作用しない）。
    """

    def __init__(
        self,
        *,
        rows: list[GreetingView] | None = None,
        list_error: Exception | None = None,
    ) -> None:
        self._rows = rows or []
        self._list_error = list_error

    def list_all(self) -> list[GreetingView]:
        if self._list_error is not None:
            raise self._list_error
        return self._rows

    def create(self, message: str) -> None:
        return None

    def update(self, greeting_id: int, message: str) -> None:
        return None

    def delete(self, greeting_id: int) -> None:
        return None


def _script(controller):
    # AppTest.from_function は関数ソースを別名前空間で再実行する。クロージャも、
    # モジュール定義名（型アノテーション含む）も参照できないため、アノテーションは
    # 付けず、controller は kwargs で受け取り、import と本体のみに閉じる。
    from interface_adapter.greeting_crud_view import render_crud

    render_crud(controller)


def _render(controller: _StubController) -> AppTest:
    """スタブ controller で render_crud を 1 回描画した AppTest を返す。"""
    # 既定 3 秒は streamlit の初回コールドスタートで超過しうるため余裕を持たせる。
    at = AppTest.from_function(
        _script, default_timeout=30, kwargs={"controller": controller}
    )
    at.run()
    return at


def _subheaders(at: AppTest) -> Sequence[str]:
    return [s.value for s in at.subheader]


def test_populated_list_renders_all_sections():
    rows = [GreetingView(1, "a"), GreetingView(2, "b")]
    at = _render(_StubController(rows=rows))

    assert not at.exception
    assert not at.error
    # 一覧・新規作成・更新・削除の全セクションが描画される。
    assert _subheaders(at) == ["一覧", "新規作成", "更新", "削除"]
    assert len(at.table) == 1


def test_empty_list_shows_info_and_create_only():
    at = _render(_StubController(rows=[]))

    assert not at.error
    # 空のときは案内（info）を出し、作成フォームのみ。更新/削除は出さない。
    assert len(at.info) == 1
    assert _subheaders(at) == ["一覧", "新規作成"]


def test_system_failure_still_renders_create_form():
    # C-2 回帰: 一覧取得が失敗しても作成フォームは描画される。
    at = _render(_StubController(list_error=SystemFailureError("DB に接続できません")))

    assert len(at.error) == 1
    # 「新規作成」が残ること＝作成フォームが描画されていること。
    assert "新規作成" in _subheaders(at)
    # id を要する更新/削除は描画しない。
    assert "更新" not in _subheaders(at)
    assert "削除" not in _subheaders(at)


def test_invalid_operation_is_shown_as_warning():
    at = _render(_StubController(list_error=InvalidOperationError("不正な操作")))

    # 利用者起因はエラーではなく警告として提示し、作成フォームは描画する。
    assert len(at.warning) == 1
    assert not at.error
    assert "新規作成" in _subheaders(at)
