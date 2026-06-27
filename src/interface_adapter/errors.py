"""画面提示用のエラー（interface_adapter 層）。

controller が usecase 層の業務例外を本型へ翻訳し、view は usecase 層へ
依存することなく、利用者に提示するメッセージとしてエラーを扱える。

失敗の原因によって 2 つに区別する。view はこの区別を使い、利用者起因は
警告（再操作で直る見込み）、システム障害は明確なエラーとして出し分ける。
"""


class OperationError(Exception):
    """利用者に提示する操作失敗の基底。message には表示文言を持つ。"""


class InvalidOperationError(OperationError):
    """利用者起因の失敗（入力不正・対象が存在しない等）。再操作で解消し得る。"""


class SystemFailureError(OperationError):
    """システム障害（DB 接続不可・SQL 実行エラー等）。利用者の操作では直らない。"""
