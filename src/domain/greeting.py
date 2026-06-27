"""挨拶メッセージを表す値オブジェクト。

domain 層。Streamlit／MySQL 等の外部依存を持たない純 Python。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Greeting:
    """挨拶メッセージを保持する不変の値オブジェクト。"""

    message: str
