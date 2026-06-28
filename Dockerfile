# Streamlit アプリ（app サービス）用のマルチステージビルド。
#
#   base       … uv 導入と共通環境変数だけを持つ土台
#   deps       … pyproject/uv.lock だけで本番依存を解決（ソース非依存でキャッシュが効く）
#   dev        … deps に dev 依存（ruff/pytest）を足したツール実行用（make fmt/lint/test）
#   production … 本番ランタイム。dev 依存を含まず、非 root ユーザーで起動する
#
# 本番イメージ（production）には ruff/pytest を入れない（G-1: 攻撃面・サイズ削減）。
# 依存解決とソース COPY を分離し、ソース変更で依存解決を再実行しない（G-2）。

# ---- base: 共通の土台（uv 導入・環境変数） ----
FROM python:3.12-slim AS base

# uv を公式イメージからコピーして導入
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# venv をプロジェクト配下（/app/.venv）ではなく /opt/venv に置く。
# こうすると make fmt/lint/test がソースを /app に bind mount しても venv を隠さない。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH=/opt/venv/bin:$PATH
# pytest と同じ import ルート（src レイアウト）を実行時にも適用
ENV PYTHONPATH=/app/src

# ---- deps: 本番依存のみを解決（レイヤキャッシュの要） ----
# 依存定義（pyproject.toml / uv.lock）だけを先に COPY して解決する。ソースを含めない
# ため、アプリのコードを変更しても uv sync のレイヤは再実行されない（G-2）。
# --no-dev で dev 依存を除外し、--no-install-project でプロジェクト自体の
# ビルド/インストールを省く（実行時は PYTHONPATH=/app/src で import するため不要）。
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- dev: ツール実行用（make fmt/lint/test）。dev 依存込み ----
# deps の本番依存レイヤを再利用し、その上に dev 依存（ruff/pytest）を足す。
# ソースは実行時に bind mount される前提なのでここでは COPY しない。
FROM deps AS dev
RUN uv sync --frozen --no-install-project
CMD ["bash"]

# ---- production: 本番ランタイム（dev 依存なし・非 root） ----
FROM base AS production
# deps が解決した本番のみの venv をそのまま持ち込む（ruff/pytest は含まれない）。
COPY --from=deps /opt/venv /opt/venv
# 最小権限の原則に従い、専用の非 root ユーザーを用意する（D-2）。
# 先に作成してレイヤを固定し、後続のソース COPY だけがコード変更で再実行されるようにする。
RUN useradd --create-home --uid 10001 appuser
# アプリ本体を後から COPY（依存レイヤのキャッシュを壊さない、G-2）。所有も非 root に。
COPY --chown=appuser:appuser . /app
USER appuser

EXPOSE 8501

# 起動時に env から .streamlit/secrets.toml の [auth] を生成してから CMD へ exec する
# （方式 A / D-6）。シークレットをイメージ層へ焼き込まず、コンテナ起動時に env から
# 流し込む。WORKDIR=/app のため secrets.toml は /app/.streamlit/ 配下（appuser 所有で
# 書込可）に生成される。必須 OAUTH_* 欠如時はスクリプトが fail-fast で起動を止める。
ENTRYPOINT ["sh", "docker/render-secrets.sh"]

# venv の bin に PATH が通っているので streamlit を直接起動する（entrypoint の "$@"）。
CMD ["streamlit", "run", "src/app.py", \
     "--server.headless=true", "--server.address=0.0.0.0", "--server.port=8501"]
