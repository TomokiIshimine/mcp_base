"""ログ出力の初期化（infrastructure 層）。

ログのレベル・フォーマット・出力先という外界の詳細をここに閉じ込め、合成ルート
（app.py）から 1 回だけ呼び出す。各層は logging.getLogger(__name__) でロガーを
取得するだけで、設定方法を知らない。
"""

import logging
import os
import sys


def configure_logging() -> None:
    """標準 logging を stdout 向けに初期化する。

    レベルは環境変数 LOG_LEVEL（未設定時は INFO）で制御する。Streamlit が握る
    既定設定を上書きしてフォーマットを一貫させるため force=True を指定する。
    """
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        force=True,
    )
