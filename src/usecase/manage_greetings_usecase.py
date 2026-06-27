"""挨拶の CRUD を担うアプリケーションロジック。

ポート経由で永続化層を操作し、入力の最小バリデーション（空文字禁止）を行う。
"""

import logging

from domain.greeting_record import GreetingRecord
from usecase.greeting_crud_port import GreetingCrudPort

logger = logging.getLogger(__name__)

# メッセージ最大長の真実源（single source of truth）。DB 制約に到達する前に
# アプリ側で弾く。値を変更する際は db/init/01_schema.sql の VARCHAR(255) も
# 同期させること（両者は物理的に共有できないため、コメントで相互参照する）。
#
# 既知の限界: 長さ判定は len()（Unicode コードポイント数）で行う。絵文字の
# ZWJ シーケンスや結合文字を含むと、コードポイント数・人間が見た目で数える
# 文字数・MySQL の VARCHAR 文字数定義が微妙にずれうる。実害は小さい（境界
# 付近で数文字前後する程度）ため現状はこの近似で許容する。書記素単位で厳密に
# 数える必要が出たら、grapheme 分割ライブラリの導入を検討する。
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
        record = self._port.create(self._require_message(message))
        logger.info("挨拶を作成 id=%s message_len=%d", record.id, len(record.message))
        return record

    def update_greeting(self, greeting_id: int, message: str) -> None:
        """指定 id の挨拶を更新する。空メッセージは拒否する。"""
        normalized = self._require_message(message)
        self._port.update(greeting_id, normalized)
        logger.info("挨拶を更新 id=%s message_len=%d", greeting_id, len(normalized))

    def delete_greeting(self, greeting_id: int) -> None:
        """指定 id の挨拶を削除する。"""
        self._port.delete(greeting_id)
        logger.info("挨拶を削除 id=%s", greeting_id)

    @staticmethod
    def _require_message(message: str) -> str:
        """前後空白を除去し、空文字・長さ超過なら ValueError を送出する。

        バリデーション失敗のログは出さない（呼び出し元へ送出し、最終的に
        interface_adapter 層が利用者起因の警告として一元的に記録する）。
        """
        normalized = message.strip()
        if not normalized:
            raise ValueError("メッセージは空にできません")
        if len(normalized) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"メッセージは {MAX_MESSAGE_LENGTH} 文字以内にしてください"
            )
        return normalized
