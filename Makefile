.DEFAULT_GOAL := help

.PHONY: help build up run down logs ps db-check fmt lint typecheck test \
        test-integration audit security clean _require-env

# fmt/lint/test 用の使い捨てコンテナ実行コマンド。
# 本番 app イメージには dev 依存（ruff/pytest/mypy 等）を含めないため、ツールは
# dev 依存込みの tooling サービス（Dockerfile の dev ステージ）上で実行する。
#  --rm      終了後にコンテナを破棄する
#  --no-deps db を起動せずに tooling イメージだけ使う（軽量タスクに DB は不要）
#  -v ...    ホストの最新ソースを /app にマウントし、ビルド時の COPY ではなく
#            手元の現在のコードを検査・整形する（fmt の書き戻しもホストへ反映される）
DC_RUN := docker compose run --rm --no-deps -v "$(CURDIR):/app" tooling
# 統合テスト用。--no-deps を外し、depends_on により db を起動・healthy まで待機する。
DC_RUN_DB := docker compose run --rm -v "$(CURDIR):/app" tooling

# compose は資格情報を .env から補間するため、.env が無いと全 compose コマンドが
# 失敗する。先回りして分かりやすいエラーで案内する（一度だけ実施すればよい）。
_require-env:
	@test -f .env || { \
		echo "Error: .env がありません。'cp .env.example .env' を実行してください。" >&2; \
		exit 1; }

help: ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build: _require-env ## Docker イメージをビルドする
	docker compose build

run: _require-env ## Docker で MySQL + Streamlit を起動する（http://localhost:8501、Ctrl-C で停止）
	docker compose up --build

up: _require-env ## Docker で MySQL + Streamlit をバックグラウンド起動する
	docker compose up --build -d

down: _require-env ## Docker コンテナを停止・削除する
	docker compose down

logs: _require-env ## Docker のログを追従表示する
	docker compose logs -f

ps: _require-env ## Docker コンテナの状態を表示する
	docker compose ps

db-check: _require-env ## MySQL コンテナへ SELECT 1 で疎通確認する
	docker compose exec -T db sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE" -e "SELECT 1;"'

fmt: _require-env ## Docker 上の ruff でコードを整形する
	$(DC_RUN) ruff format .

lint: _require-env ## Docker 上の ruff で静的検査する
	$(DC_RUN) ruff check .

typecheck: _require-env ## Docker 上の mypy で静的型検査する
	$(DC_RUN) mypy

test: _require-env ## Docker 上の pytest で軽量テスト（DB 不要）を実行する
	$(DC_RUN) pytest

test-integration: _require-env ## 実 MySQL を起動して統合テスト（重い）を実行する
	$(DC_RUN_DB) pytest -m integration --no-cov

audit: _require-env ## 依存ライブラリの既知脆弱性を pip-audit で検査する
	$(DC_RUN) pip-audit

security: _require-env ## bandit でコードのセキュリティ検査をする
	$(DC_RUN) bandit -c pyproject.toml -r src

clean: _require-env ## Docker コンテナ・ボリュームとローカルキャッシュを削除する
	docker compose down -v --remove-orphans
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache **/__pycache__
