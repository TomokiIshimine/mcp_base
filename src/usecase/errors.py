"""ポート境界をまたぐ業務例外（usecase 層）。

infrastructure 層は DB ドライバ固有の例外をここで定義する型へ翻訳し、
上位層（interface_adapter）がドライバ非依存のままエラーを扱えるようにする。
"""


class GreetingError(Exception):
    """挨拶 CRUD で発生する業務例外の基底。"""


class GreetingNotFoundError(GreetingError):
    """指定 id の挨拶が存在しないことを表す。"""


class InvalidGreetingError(GreetingError):
    """挨拶の値が制約に反することを表す（DB 制約違反のドライバ非依存な翻訳先）。

    アプリ側のバリデーションをすり抜けた入力が DB 制約（長さ超過等）に当たった
    場合に、infrastructure 層がドライバ固有の例外をここへ翻訳する。利用者起因で
    再操作により解消し得る点で RepositoryError（システム障害）と区別する。
    """


class RepositoryError(GreetingError):
    """永続化層での操作失敗（接続不可・SQL 実行エラー等）を表す。"""
