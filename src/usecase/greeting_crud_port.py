"""挨拶 CRUD のポート（リポジトリ抽象インターフェース）。

usecase 層が依存方向を内向きに保つために定義する抽象。infrastructure 層が
本ポートを実装し、usecase は具象（DB アクセス等）を知らずに CRUD を行う。
"""

from abc import ABC, abstractmethod

from domain.greeting_record import GreetingRecord


class GreetingCrudPort(ABC):
    """挨拶レコードの CRUD を提供するポート。具象は infrastructure 層が実装する。"""

    @abstractmethod
    def list_all(self) -> list[GreetingRecord]:
        """全ての挨拶レコードを id 昇順で返す。"""
        raise NotImplementedError

    @abstractmethod
    def create(self, message: str) -> GreetingRecord:
        """挨拶を 1 件作成し、採番済みレコードを返す。"""
        raise NotImplementedError

    @abstractmethod
    def update(self, greeting_id: int, message: str) -> None:
        """指定 id の挨拶メッセージを更新する。"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, greeting_id: int) -> None:
        """指定 id の挨拶を削除する。"""
        raise NotImplementedError
