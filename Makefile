# X-Tern Agents Makefile

.PHONY: dev backend frontend test fmt lint clean docker-up docker-down help

# Default target
.DEFAULT_GOAL := help

# Variables
BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV := $(BACKEND_DIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Help
help:
	@echo "X-Tern Agents - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start all services (docker-compose)"
	@echo "  make backend      - Start backend server only"
	@echo "  make frontend     - Start frontend server only"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests only"
	@echo "  make e2e-aws      - E2E AWS persistence test (backend must be running)"
	@echo "  make verify-aws   - Verify S3/DynamoDB integration"
	@echo ""
	@echo "Code Quality:"
	@echo "  make fmt          - Format all code"
	@echo "  make fmt-backend  - Format Python code"
	@echo "  make fmt-frontend - Format JavaScript/TypeScript code"
	@echo "  make lint         - Run all linters"
	@echo "  make lint-backend - Run Python linters"
	@echo "  make lint-frontend- Run ESLint"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - Start services with Docker Compose"
	@echo "  make docker-down  - Stop Docker Compose services"
	@echo "  make docker-build - Build Docker images"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install all dependencies"
	@echo "  make clean        - Clean build artifacts"

# Development
dev:
	docker-compose up --build

backend:
	cd $(BACKEND_DIR) && source .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd $(FRONTEND_DIR) && npm run dev

# Testing
test: test-backend

test-backend:
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -v

# E2E and AWS verification (requires backend running + USE_AWS=1)
e2e-aws:
	cd $(BACKEND_DIR) && ( set -a && [ -f .env ] && . .env && set +a ) && \
		PYTHONPATH=$(PWD)/$(BACKEND_DIR) python3 scripts/e2e_aws_persistence_test.py

verify-aws:
	cd $(BACKEND_DIR) && ( set -a && [ -f .env ] && . .env && set +a ) && \
		PYTHONPATH=$(PWD)/$(BACKEND_DIR) python3 scripts/verify_aws_integration.py

# Formatting
fmt: fmt-backend fmt-frontend

fmt-backend:
	cd $(BACKEND_DIR) && source .venv/bin/activate && \
		ruff check --fix . && \
		black .

fmt-frontend:
	cd $(FRONTEND_DIR) && npm run lint -- --fix

# Linting
lint: lint-backend lint-frontend

lint-backend:
	cd $(BACKEND_DIR) && source .venv/bin/activate && \
		ruff check . && \
		black --check .

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

# Installation
install: install-backend install-frontend

install-backend:
	cd $(BACKEND_DIR) && \
		python3 -m venv .venv && \
		source .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt

install-frontend:
	cd $(FRONTEND_DIR) && npm install

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/.coverage
	rm -rf $(BACKEND_DIR)/htmlcov
