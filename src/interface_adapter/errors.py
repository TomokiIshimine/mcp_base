"""画面提示用のエラー（interface_adapter 層）。

controller が usecase 層の業務例外を本型へ翻訳し、view は usecase 層へ
依存することなく、利用者に提示するメッセージとしてエラーを扱える。
"""


class OperationError(Exception):
    """利用者に提示する操作失敗。message には表示文言を持つ。"""
