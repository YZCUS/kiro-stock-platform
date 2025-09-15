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

### Core Components

**Backend Structure:**
- `api/v1/` - API endpoints (stocks, analysis)
- `models/domain/` - Domain models (Stock, PriceHistory, TechnicalIndicator, TradingSignal)
- `models/repositories/` - Data access layer with CRUD operations
- `services/` - Business logic organized by domain:
  - `analysis/` - Technical analysis and indicator calculations
  - `data/` - Data collection, validation, and backfill
  - `trading/` - Signal generation and notifications
  - `infrastructure/` - Cache, storage, and scheduling
- `scripts/cli/` - Command-line tools for analysis and management

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
- `backend/core/config.py` - Centralized configuration
- `docker-compose.yml` - Local development services
- `Makefile` - Development workflow automation