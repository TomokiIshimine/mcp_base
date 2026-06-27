"""永続化識別子付きの挨拶レコード（domain 層）。

CRUD 操作の対象となる、id を伴う挨拶エンティティ。Streamlit／MySQL 非依存の純 Python。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GreetingRecord:
    """id と message を保持する不変の挨拶レコード。"""

    id: int
    message: str
