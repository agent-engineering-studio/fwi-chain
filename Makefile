.DEFAULT_GOAL := help
.PHONY: help check lint format typecheck test bench build figures docs notebooks \
        demo demo-test mcp docker docker-build down

help: ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

check: lint typecheck test bench ## everything CI checks: lint, types, tests, benchmark

lint: ## ruff, check and format
	uv run ruff check
	uv run ruff format --check

format: ## rewrite the code as ruff wants it
	uv run ruff format
	uv run ruff check --fix

typecheck: ## mypy --strict on src and tests
	uv run mypy

test: ## the tests, with coverage (90 % or more)
	uv run pytest --cov --cov-report=term-missing

bench: ## the known cases, and the text check on its set
	uv run python -m benchmarks.run --check
	uv run python -m benchmarks.faithful --check

build: ## the wheel and the sdist, in dist/
	uv build

figures: ## draw the figures of the docs again
	uv run --with matplotlib python docs/scripts/make_figures.py
	uv run --with matplotlib python docs/scripts/make_blog_figures.py

docs: ## build the site, with llms.txt and the agent skill
	uv run --group docs zensical build --clean --strict
	uv run --group docs python tools/build_llms.py

notebooks: ## write the notebooks from the examples, run them all, save the results
	uv run --group examples python tools/make_notebooks.py
	cd notebooks && uv run --group examples jupyter nbconvert --to notebook --execute --inplace *.ipynb

demo: ## the page for a public body, on http://127.0.0.1:3007 (needs uv and npm)
	sh app/vendor.sh
	cd app && uv run uvicorn diario.api:app --port 3007 --reload

demo-test: ## the tests of the page
	cd app && uv run pytest

mcp: ## the MCP server over HTTP, on http://127.0.0.1:8772/mcp
	uv run --extra mcp fwi-chain-mcp --http

docker: ## the page (3007) and the notebooks (8885) with Docker alone
	docker compose up --build

docker-build: ## build every image, the MCP server included
	docker compose --profile mcp --profile tools build

down: ## stop everything and remove the containers
	docker compose --profile mcp --profile tools down --remove-orphans
