.PHONY: install test lint format migrate api web

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m mypy apps/api/app

format:
	python -m ruff format .
	python -m ruff check --fix .

migrate:
	alembic upgrade head

api:
	python -m uvicorn app.main:app --app-dir apps/api --reload

web:
	cd apps/web && pnpm dev
