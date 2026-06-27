# Streamlit アプリ（app サービス）用イメージ。
# uv で依存解決し、Clean Architecture 4 層を含むアプリを起動する。
# fmt/lint/test もこのイメージ上の一時コンテナで実行するため、dev 依存も解決する。
FROM python:3.12-slim

# uv を公式イメージからコピーして導入
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# venv をプロジェクト配下（/app/.venv）ではなく /opt/venv に置く。
# こうすると make fmt/lint/test がソースを /app に bind mount しても venv を隠さない。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH=/opt/venv/bin:$PATH
# pytest と同じ import ルート（src レイアウト）を実行時にも適用
ENV PYTHONPATH=/app/src

# プロジェクト一式をコピー（不要物は .dockerignore で除外）
COPY . /app

# dev 依存も含めて解決（ruff/pytest をコンテナ内で実行できるようにする）
RUN uv sync

EXPOSE 8501

# venv の bin に PATH が通っているので streamlit を直接起動する
CMD ["streamlit", "run", "app.py", \
     "--server.headless=true", "--server.address=0.0.0.0", "--server.port=8501"]
