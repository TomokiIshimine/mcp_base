"""Streamlit による画面描画を担う view。"""

import streamlit as st


def render(message: str) -> None:
    """挨拶メッセージを Streamlit 画面に描画する。"""
    st.write(message)
