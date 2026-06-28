"""管理者認可の判定ロジック（usecase 層）。

ログイン済みユーザーの Email と検証フラグを受け取り、管理者として認可してよいかを
純粋な業務ルールとして判定する。Streamlit にも infrastructure 実装にも依存せず、
副作用（ログ・I/O）を持たない純粋関数として呼べることを契約とする（層分離の維持）。
"""


class AuthorizeAdminUseCase:
    """管理者 Email との完全一致＋検証フラグで認可可否を判定するユースケース。

    管理者 Email は infrastructure の設定クラス由来の値を合成ルートから注入する。
    判定は「`email_verified` が True であること」を先に確認し、その上で `email` を
    管理者 Email とバイト単位で完全一致照合する。正規化（大文字小文字の無視・前後
    空白の除去）は意図的に行わない（なりすまし・別アカウント混入を防ぐため、表記の
    ゆれを別人扱いする厳格側に倒す）。
    """

    def __init__(self, admin_email: str) -> None:
        self._admin_email = admin_email

    def is_authorized(self, email: str | None, email_verified: bool | None) -> bool:
        """ログイン済みユーザーを管理者として認可してよいかを返す。

        `email_verified` が True 以外（False / None / 欠落）の場合は、Email が一致
        しても拒否する。検証済みでない Email は所有者が確認されておらず、なりすまし
        の余地を残すため、文字列一致のみでは認可しない。
        """
        if email_verified is not True:
            return False
        return email == self._admin_email
