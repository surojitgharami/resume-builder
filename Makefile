.PHONY: help install dev test clean docker-up docker-down migrate security-check

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install all dependencies (backend and frontend)
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev: ## Run development servers (requires docker-compose)
	docker-compose up -d

dev-stop: ## Stop development servers
	docker-compose down

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && npm run test

test-backend: ## Run backend tests only
	cd backend && pytest -v

test-frontend: ## Run frontend tests only
	cd frontend && npm run test

lint: ## Run linters
	@echo "Linting backend..."
	cd backend && black --check app
	@echo "Linting frontend..."
	cd frontend && npm run lint

format: ## Format code
	@echo "Formatting backend..."
	cd backend && black app
	@echo "Formatting frontend..."
	cd frontend && npm run format

security-check: ## Run security vulnerability checks
	@echo "Checking backend dependencies..."
	cd backend && pip-audit
	@echo "Checking frontend dependencies..."
	cd frontend && npm audit

clean: ## Clean build artifacts and caches
	@echo "Cleaning backend..."
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage
	@echo "Cleaning frontend..."
	rm -rf frontend/dist frontend/node_modules

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-rebuild: ## Rebuild Docker containers
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

migrate: ## Run database migrations (create indexes)
	@echo "Creating database indexes..."
	python -c "import asyncio; from backend.app.db.mongo import connect_to_mongo, create_indexes; asyncio.run(connect_to_mongo()); asyncio.run(create_indexes())"

seed: ## Seed database with sample data
	@echo "Seeding database..."
	# TODO: Implement database seeding script

deploy-backend: ## Deploy backend to Render
	@echo "Deploying backend..."
	git push origin main

deploy-frontend: ## Deploy frontend to Vercel
	@echo "Deploying frontend..."
	cd frontend && vercel --prod

setup-keys: ## Generate RS256 key pair for JWT
	@echo "Generating RS256 key pair..."
	openssl genrsa -out backend/private_key.pem 2048
	openssl rsa -in backend/private_key.pem -pubout -out backend/public_key.pem
	@echo "Keys generated: backend/private_key.pem, backend/public_key.pem"
	@echo "Add to .env: RS_PRIVATE_KEY and RS_PUBLIC_KEY"
