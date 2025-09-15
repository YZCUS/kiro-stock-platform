# 股票分析平台 Makefile

.PHONY: help build up down logs clean test db-init db-migrate db-reset db-seed db-test

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
	@echo "  lint      - 程式碼檢查"
	@echo "  format    - 程式碼格式化"

# Docker 操作
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --rmi all --remove-orphans
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
	cd frontend && npm test

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
	docker-compose -f docker-compose.prod.yml up -d

# 備份資料庫
db-backup:
	docker-compose exec postgres pg_dump -U postgres stock_analysis > backup_$(shell date +%Y%m%d_%H%M%S).sql

# 還原資料庫
db-restore:
	@read -p "請輸入備份檔案名稱: " backup_file; \
	docker-compose exec -T postgres psql -U postgres stock_analysis < $$backup_file