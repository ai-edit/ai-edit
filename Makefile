.PHONY: help install install-dev test test-cov lint format type-check clean build upload

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	pip install -e .

install-dev: ## Install package with development dependencies
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=ai_edit --cov-report=term-missing --cov-report=html

lint: ## Run linting
	flake8 ai_edit/ tests/
	
format: ## Format code
	black ai_edit/ tests/
	isort ai_edit/ tests/

format-check: ## Check code formatting
	black --check ai_edit/ tests/
	isort --check-only ai_edit/ tests/

type-check: ## Run type checking
	mypy ai_edit/

quality: format lint type-check test ## Run all quality checks

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean ## Build package
	python -m build

upload-test: build ## Upload to test PyPI
	python -m twine upload --repository testpypi dist/*

upload: build ## Upload to PyPI
	python -m twine upload dist/*

# Development workflow shortcuts
dev-setup: ## Complete development setup
	python setup_dev.py

quick-test: ## Run tests quickly (no coverage)
	pytest tests/ -x

watch-test: ## Run tests on file changes (requires pytest-watch)
	ptw tests/ ai_edit/
