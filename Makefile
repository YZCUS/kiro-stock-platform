# 股票分析平台 Makefile

.PHONY: help build up down logs clean test airflow-test qlib-test test-coverage backend-coverage frontend-coverage e2e db-init db-migrate db-reset db-seed db-test prod-deploy db-backup db-restore

# 預設目標
help:
	@echo "股票分析平台 - 可用命令:"
	@echo ""
	@echo "Docker 操作:"
	@echo "  build     - 建置所有 Docker 映像"
	@echo "  up        - 啟動所有服務"
	@echo "  down      - 停止所有服務"
	@echo "  logs      - 查看服務日誌"
	@echo "  clean     - 清理 Docker 資源"
	@echo ""
	@echo "資料庫操作:"
	@echo "  db-init   - 初始化資料庫"
	@echo "  db-migrate - 執行資料庫遷移"
	@echo "  db-reset  - 重置資料庫（危險操作）"
	@echo "  db-seed   - 建立種子數據"
	@echo "  db-test   - 測試資料庫連接"
	@echo ""
	@echo "開發操作:"
	@echo "  test      - 執行測試"
	@echo "  test-coverage - 執行前後端 coverage"
	@echo "  e2e       - 執行 Chromium E2E smoke"
	@echo "  lint      - 程式碼檢查"
	@echo "  format    - 程式碼格式化"

# Docker 操作
build:
	docker compose -p kiro-stock-platform build

up:
	docker compose -p kiro-stock-platform up -d

down:
	docker compose -p kiro-stock-platform down

logs:
	docker compose -p kiro-stock-platform logs -f

clean:
	docker compose -p kiro-stock-platform down -v --rmi all --remove-orphans
	docker system prune -f

# 資料庫操作
db-init:
	cd backend && python database/migrate.py init

db-migrate:
	cd backend && python database/migrate.py upgrade

db-reset:
	cd backend && python database/migrate.py reset

db-seed:
	cd backend && python database/seed_data.py

db-test:
	cd backend && python database/test_connection.py

# 開發操作
test:
	cd backend && python -m pytest tests/ -v
	$(MAKE) airflow-test
	$(MAKE) qlib-test
	cd frontend && npm test

airflow-test:
	AIRFLOW_HOME=/tmp/kiro-airflow-test PYTHONPATH=airflow \
		python -m pytest --import-mode=importlib airflow/tests/unit -q

qlib-test:
	PYTHONPATH=qlib_service QLIB_ARTIFACT_ROOT=/tmp/kiro-qlib-test \
		QLIB_PROVIDER_URI=/tmp/kiro-qlib-test/provider \
		python -m pytest qlib_service/tests -q

backend-coverage:
	PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests \
		--cov=backend/api --cov=backend/app --cov=backend/core \
		--cov=backend/domain --cov=backend/infrastructure \
		--cov-report=term-missing:skip-covered

frontend-coverage:
	cd frontend && npm test -- --runInBand --coverage

test-coverage: backend-coverage frontend-coverage

e2e:
	cd frontend && npm run test:e2e -- --project=chromium

lint:
	cd backend && python -m flake8 .
	cd frontend && npm run lint

format:
	cd backend && python -m black .
	cd frontend && npm run format

# 快速啟動開發環境
dev-setup: build up db-init db-seed
	@echo "開發環境設置完成！"
	@echo "前端: http://localhost:3000"
	@echo "後端 API: http://localhost:8000"
	@echo "API 文檔: http://localhost:8000/docs"
	@echo "Airflow: http://localhost:8080 (admin/admin)"

# 生產環境部署
prod-deploy:
	@test -s .env.images || (echo "Missing immutable .env.images" >&2; exit 1)
	@test -s nginx/ssl/fullchain.pem || (echo "Missing TLS fullchain" >&2; exit 1)
	@test -s nginx/ssl/privkey.pem || (echo "Missing TLS private key" >&2; exit 1)
	python3 scripts/validate-production-env.py .env.production
	python3 scripts/validate-production-env.py --images .env.images
	docker compose -p kiro-stock-platform --env-file .env.production --env-file .env.images -f docker-compose.prod.yml pull backend qlib-prediction-service airflow-webserver frontend
	docker compose -p kiro-stock-platform --env-file .env.production --env-file .env.images -f docker-compose.prod.yml up -d --remove-orphans

# 備份資料庫
db-backup:
	PROJECT_DIR=$(CURDIR) bash scripts/backup.sh

# 還原資料庫
db-restore:
	PROJECT_DIR=$(CURDIR) bash scripts/restore.sh
