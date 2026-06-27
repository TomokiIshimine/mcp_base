.DEFAULT_GOAL := help

.PHONY: help build up run down logs ps db-check fmt lint test clean

# fmt/lint/test 用の使い捨てコンテナ実行コマンド。
#  --rm      終了後にコンテナを破棄する
#  --no-deps db を起動せずに app イメージだけ使う（単体テストに DB は不要）
#  -v ...    ホストの最新ソースを /app にマウントし、ビルド時の COPY ではなく
#            手元の現在のコードを検査・整形する（fmt の書き戻しもホストへ反映される）
DC_RUN := docker compose run --rm --no-deps -v "$(CURDIR):/app" app

help: ## このヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

build: ## Docker イメージをビルドする
	docker compose build

run: ## Docker で MySQL + Streamlit を起動する（http://localhost:8501、Ctrl-C で停止）
	docker compose up --build

up: ## Docker で MySQL + Streamlit をバックグラウンド起動する
	docker compose up --build -d

down: ## Docker コンテナを停止・削除する
	docker compose down

logs: ## Docker のログを追従表示する
	docker compose logs -f

ps: ## Docker コンテナの状態を表示する
	docker compose ps

db-check: ## MySQL コンテナへ SELECT 1 で疎通確認する
	docker compose exec -T db mysql -uapp -papp_password app_db -e "SELECT 1;"

fmt: ## Docker 上の ruff でコードを整形する
	$(DC_RUN) ruff format .

lint: ## Docker 上の ruff で静的検査する
	$(DC_RUN) ruff check .

test: ## Docker 上の pytest で単体テストを実行する
	$(DC_RUN) pytest

clean: ## Docker コンテナ・ボリュームとローカルキャッシュを削除する
	docker compose down -v --remove-orphans
	rm -rf .venv .pytest_cache .ruff_cache **/__pycache__
