.PHONY: check lint format typecheck test build figures docs

check: lint typecheck test

lint:
	uv run ruff check
	uv run ruff format --check

format:
	uv run ruff format
	uv run ruff check --fix

typecheck:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing

build:
	uv build

figures:
	uv run --with matplotlib python docs/scripts/make_figures.py

docs:
	uv run --group docs mkdocs build --strict
