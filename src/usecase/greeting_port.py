"""挨拶取得のポート（リポジトリ抽象インターフェース）。

usecase 層が依存方向を内向きに保つために定義する抽象。infrastructure 層が
本ポートを実装し、usecase は具象（DB アクセス等）を知らずに挨拶を取得する。
"""

from abc import ABC, abstractmethod

from domain.greeting import Greeting


class GreetingPort(ABC):
    """挨拶を取得するポート。具象実装は infrastructure 層が提供する。"""

    @abstractmethod
    def get(self) -> Greeting:
        """挨拶の値オブジェクトを返す。"""
        raise NotImplementedError
