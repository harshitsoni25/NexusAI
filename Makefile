# Developer entry points. CI runs exactly these targets, so a green `make check`
# locally means a green pipeline.

.PHONY: help install format lint typecheck test check build clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create a virtual environment and install the project with dev extras
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,test]"
	@echo "Activate with: source .venv/bin/activate"

format:  ## Apply formatting and import ordering
	black src tests
	ruff check --fix src tests

lint:  ## Check formatting and linting without modifying files
	black --check --diff src tests
	ruff check src tests

typecheck:  ## Run strict type checking
	mypy

test:  ## Run the test suite with coverage
	pytest

check: lint typecheck test  ## Everything CI runs

build:  ## Build the wheel and source distribution
	python -m build

clean:  ## Remove caches and build output
	rm -rf build dist *.egg-info .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
