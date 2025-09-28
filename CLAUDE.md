# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **股票分析平台** (Stock Analysis Platform) - an automated stock data collection and technical analysis platform that provides real-time technical indicator calculations and visualization charts. The platform supports both Taiwan Stock Exchange (TSE) and US stock markets.

### Technology Stack

**Backend (Python):**
- FastAPI for REST API
- PostgreSQL as primary database
- Redis for caching and session management
- Apache Airflow for workflow automation
- TA-Lib for technical indicator calculations
- SQLAlchemy ORM with Alembic migrations

**Frontend (TypeScript/Next.js):**
- Next.js 14 with App Router
- TypeScript for type safety
- TailwindCSS for styling
- TradingView Lightweight Charts for financial charts
- Redux Toolkit for state management
- React Query for data fetching and caching

## Essential Commands

### Development Setup
```bash
# Full development environment setup
make dev-setup

# Individual services
make build          # Build all Docker images
make up            # Start all services
make down          # Stop all services
```

### Backend Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Database operations
python database/migrate.py init     # Initialize database
python database/migrate.py upgrade  # Run migrations
python database/seed_data.py       # Seed initial data
python database/test_connection.py # Test DB connection

# Testing
python -m pytest tests/ -v
python tests/run_tests.py          # Run all tests
python tests/run_indicator_tests.py # Run indicator-specific tests

# Code quality
python -m flake8 .    # Linting
python -m black .     # Code formatting
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Development
npm run dev          # Start development server
npm run build        # Build for production
npm start           # Start production server

# Code quality
npm run lint         # ESLint
tsc --noEmit        # Type checking (npm run type-check)
```

### Airflow Development
```bash
cd airflow

# Install dependencies
pip install -r requirements.txt

# Code quality
black .              # Code formatting
flake8 .            # Linting
```

### Make Commands (Recommended)
```bash
make test           # Run all tests (backend + frontend)
make lint           # Run linting (backend + frontend)
make format         # Format code (backend + frontend)
make logs           # View service logs
make clean          # Clean Docker resources
```

## Architecture

### Clean Architecture Implementation

The backend follows **Clean Architecture** principles with clear layer separation and dependency inversion. The architecture ensures maintainability, testability, and scalability.

**Backend Structure (Clean Architecture):**

```
backend/
├── app/                          # FastAPI 啟動 & DI 容器
│   ├── main.py                   # Application entry point
│   ├── dependencies.py           # 統一註冊服務、repository、config
│   └── settings.py               # Type-safe configuration management
├── api/
│   ├── routers/                  # 純路由組合 (按領域分檔)
│   │   └── v1/
│   │       ├── stocks.py         # Stock management endpoints
│   │       ├── analysis.py       # Technical analysis endpoints
│   │       └── signals.py        # Trading signals endpoints
│   ├── schemas/                  # Pydantic models (domain input/output)
│   └── utils/                    # API-specific utilities
├── domain/                       # 實際業務核心 - Business Logic Layer
│   ├── services/                 # 業務邏輯 (分析、交易、數據收集)
│   │   ├── stock_service.py      # Stock business logic
│   │   ├── technical_analysis_service.py  # Technical analysis
│   │   ├── data_collection_service.py     # Data collection
│   │   └── trading_signal_service.py      # Trading signals
│   └── repositories/             # Repository interfaces (ports)
│       ├── stock_repository_interface.py
│       └── price_history_repository_interface.py
├── infrastructure/               # Infrastructure Layer
│   ├── persistence/              # Repository 實作與 ORM Mapper
│   │   ├── stock_repository.py   # Concrete stock repository
│   │   └── price_history_repository.py
│   ├── cache/                    # Redis 封裝 (統一快取抽象)
│   │   └── redis_cache_service.py
│   ├── external/                 # 第三方 API / yfinance 介接
│   └── scheduler/                # 原 scheduler、pubsub 等
├── models/                       # SQLAlchemy Domain Models
│   └── domain/                   # Database entity definitions
│       ├── stock.py
│       ├── price_history.py
│       ├── technical_indicator.py
│       └── trading_signal.py
├── core/                         # 系統級設定 & 共用工具
│   ├── config.py                 # System configuration
│   ├── database.py               # Database connection
│   └── redis.py                  # Redis connection
├── utils/                        # 純共用小工具（與業務無關的 helper）
├── scripts/                      # CLI / one-off scripts
└── tests/                        # Comprehensive test suite
    ├── unit/                     # Unit tests for domain services
    ├── integration/              # API and database integration tests
    └── e2e/                      # End-to-end tests
```

### Architecture Principles

**Layer Responsibilities:**

1. **Domain Layer** (Business Core):
   - Pure business logic without infrastructure dependencies
   - Repository interfaces (dependency inversion)
   - Domain services with business rules
   - Data models and business entities

2. **Infrastructure Layer**:
   - Concrete implementations of repository interfaces
   - External API integrations (Yahoo Finance)
   - Cache implementations (Redis)
   - Database ORM mappings

3. **Application Layer**:
   - Dependency injection container
   - Application configuration
   - Service orchestration

4. **Interface Layer** (API):
   - HTTP routing and request handling
   - Input validation and response formatting
   - Delegates business logic to domain services

**Key Design Patterns:**
- **Repository Pattern**: Abstract data access with interfaces
- **Dependency Injection**: IoC container for service management
- **Service Layer**: Encapsulated business logic
- **Interface Segregation**: Clean abstraction boundaries

### Migration Strategy

The architecture has been migrated in phases while maintaining backward compatibility:

- **Phase 1**: Settings management and dependency injection
- **Phase 2**: Domain services and repository pattern implementation
- **Phase 3**: API router refactoring and comprehensive integration

Legacy components coexist with new architecture during transition period.

### Folder Migration Map

**Current to Clean Architecture mapping:**

```
Legacy Structure                    →    Clean Architecture
──────────────────────────────────────────────────────────────────
services/analysis/                  →    domain/services/
services/data/                      →    domain/services/
services/trading/                   →    domain/services/
services/infrastructure/cache.py    →    infrastructure/cache/
models/domain/                      →    models/domain/ (unchanged)
models/repositories/                →    infrastructure/persistence/
api/v1/                            →    api/routers/v1/
core/config.py                     →    app/settings.py (new) + core/config.py (legacy)
                                   →    app/dependencies.py (new DI container)
```

**Integration Guidelines:**
- **services/analysis/** → Migrated to `domain/services/technical_analysis_service.py`
- **services/data/** → Migrated to `domain/services/data_collection_service.py`
- **services/trading/** → Migrated to `domain/services/trading_signal_service.py`
- **models/repositories/** → Interface definitions in `domain/repositories/`, implementations in `infrastructure/persistence/`
- **Cache modules** → Unified in `infrastructure/cache/redis_cache_service.py`
- **API routing** → Clean separation in `api/routers/v1/` with domain service injection

**Key Domain Models:**
- Stock symbols with market classification (TW/US)
- Price history with OHLCV data
- Technical indicators (RSI, SMA, EMA, MACD, Bollinger Bands, KD)
- Trading signals with golden cross/death cross detection

**Airflow DAGs:**
- Daily stock data collection from Yahoo Finance
- Automated technical indicator calculations
- Market-aware scheduling with sensor-based triggers

### Database Schema
- PostgreSQL with SQLAlchemy ORM
- Alembic for schema migrations
- Optimized for time-series data queries
- Redis caching for frequently accessed data

### API Design
- RESTful API with FastAPI
- Automatic OpenAPI documentation at `/docs`
- CORS enabled for frontend integration
- Health check endpoint at `/health`

## Service URLs (Development)
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Airflow UI: http://localhost:8080 (admin/admin)

## Testing Strategy

**Backend Tests:**
- Unit tests for calculators and services
- Integration tests for API endpoints
- Benchmark tests for indicator performance
- Database migration tests

**Frontend Tests:**
- Component unit tests
- Integration tests for API calls
- End-to-end tests for user workflows

## Configuration

**Environment Variables:**
- Database connection via `DATABASE_URL`
- Redis connection via `REDIS_URL`
- Yahoo Finance API settings
- JWT authentication settings
- CORS allowed origins

**Key Files:**
- `backend/app/settings.py` - Type-safe configuration with Pydantic
- `backend/app/dependencies.py` - Dependency injection container
- `backend/core/config.py` - Legacy system configuration
- `docker-compose.yml` - Local development services
- `Makefile` - Development workflow automation

## Development Guidelines

### Dependency Injection
All services should be registered in `app/dependencies.py` and injected via FastAPI's `Depends` mechanism:

```python
# Clean Architecture services
from app.dependencies import (
    get_stock_service,
    get_technical_analysis_service_clean,
    get_data_collection_service_clean,
    get_trading_signal_service_clean
)

@router.get("/stocks/{stock_id}/analysis")
async def get_analysis(
    stock_id: int,
    db: AsyncSession = Depends(get_database_session),
    technical_service = Depends(get_technical_analysis_service_clean)
):
    return await technical_service.calculate_stock_indicators(db, stock_id)
```

### Business Logic Placement
- **Domain Services**: Pure business logic, no framework dependencies
- **API Routers**: HTTP handling, parameter validation, response formatting only
- **Infrastructure**: Concrete implementations of domain interfaces

### Testing Strategy
- **Unit Tests**: Test domain services with mocked dependencies
- **Integration Tests**: Test API endpoints with real database
- **Architecture Tests**: Verify Clean Architecture compliance

### Code Organization
- Follow the established layer structure
- Use dependency injection for all service interactions
- Keep business logic in domain services
- Abstract external dependencies through interfaces

### Quality Assurance

**Testing Commands:**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v              # Domain service unit tests
python -m pytest tests/integration/ -v       # API integration tests
python -m pytest tests/unit/test_domain_services_migration.py -v  # Architecture tests

# Run with coverage
python -m pytest tests/ --cov=domain --cov=infrastructure --cov=api
```

**Code Quality:**
```bash
# Linting and formatting
python -m flake8 .                          # Style checking
python -m black .                           # Code formatting
python -m isort .                           # Import sorting

# Type checking (if using mypy)
mypy domain/ infrastructure/ api/
```

**Architecture Validation:**
- Domain layer should not import from infrastructure or api layers
- Infrastructure layer implements domain interfaces
- API layer uses dependency injection for all services
- All external dependencies are abstracted through interfaces

### Important Notes for AI Assistants

**When working with this codebase:**

1. **Use Dependency Injection**: Always inject services via `app/dependencies.py` rather than direct instantiation
2. **Follow Layer Boundaries**: Keep business logic in domain services, not in API routers
3. **Test Coverage**: Write unit tests for domain services with mocked dependencies
4. **Interface Implementation**: When adding new repositories, create interface first in `domain/repositories/`
5. **Configuration**: Use `app/settings.py` for new configuration, maintain backward compatibility with `core/config.py`
6. **Legacy Migration**: When modifying existing services, prefer migrating to Clean Architecture rather than patching legacy code

**Common Patterns:**
- Repository Pattern for data access
- Service Layer for business logic
- Dependency Injection for loose coupling
- Interface Segregation for clean boundaries