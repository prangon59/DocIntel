.PHONY: up down build test lint format eval clean help

help:
	@echo "Available commands:"
	@echo "  make up       - Start all Docker containers (API, Worker, Postgres, Redis, Web)"
	@echo "  make down     - Stop all Docker containers"
	@echo "  make build    - Build all container images"
	@echo "  make test     - Run backend test suite"
	@echo "  make lint     - Run linters (ruff, mypy)"
	@echo "  make format   - Run formatters (ruff format)"
	@echo "  make eval     - Run evaluation benchmark pipeline"
	@echo "  make clean    - Remove build artifacts and temporary files"

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	pytest backend/tests

lint:
	ruff check backend
	mypy backend/app

format:
	ruff format backend

eval:
	python eval/run_eval.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
