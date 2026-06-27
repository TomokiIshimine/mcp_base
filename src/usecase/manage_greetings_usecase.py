"""挨拶の CRUD を担うアプリケーションロジック。

ポート経由で永続化層を操作し、入力の最小バリデーション（空文字禁止）を行う。
"""

from domain.greeting_record import GreetingRecord
from usecase.greeting_crud_port import GreetingCrudPort

# greetings.message は VARCHAR(255)。DB 制約に到達する前にアプリ側で弾く。
MAX_MESSAGE_LENGTH = 255


class ManageGreetingsUseCase:
    """挨拶レコードの一覧・作成・更新・削除を提供するユースケース。"""

    def __init__(self, port: GreetingCrudPort) -> None:
        self._port = port

    def list_greetings(self) -> list[GreetingRecord]:
        """全ての挨拶レコードを返す。"""
        return self._port.list_all()

    def create_greeting(self, message: str) -> GreetingRecord:
        """挨拶を作成する。空メッセージは拒否する。"""
        return self._port.create(self._require_message(message))

    def update_greeting(self, greeting_id: int, message: str) -> None:
        """指定 id の挨拶を更新する。空メッセージは拒否する。"""
        self._port.update(greeting_id, self._require_message(message))

    def delete_greeting(self, greeting_id: int) -> None:
        """指定 id の挨拶を削除する。"""
        self._port.delete(greeting_id)

    @staticmethod
    def _require_message(message: str) -> str:
        """前後空白を除去し、空文字・長さ超過なら ValueError を送出する。"""
        normalized = message.strip()
        if not normalized:
            raise ValueError("メッセージは空にできません")
        if len(normalized) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"メッセージは {MAX_MESSAGE_LENGTH} 文字以内にしてください"
            )
        return normalized
