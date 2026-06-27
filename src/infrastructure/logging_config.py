"""ログ出力の初期化（infrastructure 層）。

ログのレベル・フォーマット・出力先という外界の詳細をここに閉じ込め、合成ルート
（src/app.py）から 1 回だけ呼び出す。各層は logging.getLogger(__name__) でロガーを
取得するだけで、設定方法を知らない。
"""

import logging
import os
import sys

# LOG_LEVEL に不正値が来ても起動を失敗させず、安全側へ寄せるための既定レベル。
# 未設定・未知の値はいずれもここへフォールバックする。
_DEFAULT_LOG_LEVEL = "INFO"


def configure_logging() -> None:
    """標準 logging を stdout 向けに初期化する。

    レベルは環境変数 LOG_LEVEL（未設定時は INFO）で制御する。不正値（例: VERBOSE）
    は起動を落とさず INFO へフォールバックする。Streamlit が握る既定設定を上書き
    してフォーマットを一貫させるため force=True を指定する。
    """
    level = _resolve_log_level(os.environ.get("LOG_LEVEL"))
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        force=True,
    )


def _resolve_log_level(raw: str | None) -> str:
    """環境変数の値を有効なログレベル名へ解決する。

    未設定・未知の値は INFO へフォールバックし、設定ミスで起動が落ちるのを防ぐ。
    未知値だった場合は警告ログを残し、設定ミスに気付けるようにする。
    """
    if raw is None:
        return _DEFAULT_LOG_LEVEL
    level = raw.strip().upper()
    # レベル名が登録済みか（DEBUG/INFO/… に対応する int か）で妥当性を判定する。
    # 未知名に対して getLevelName は "Level XXX" という文字列を返す。
    if isinstance(logging.getLevelName(level), int):
        return level
    logging.getLogger(__name__).warning(
        "未知の LOG_LEVEL=%r のため %s で起動します", raw, _DEFAULT_LOG_LEVEL
    )
    return _DEFAULT_LOG_LEVEL
