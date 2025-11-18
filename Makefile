.PHONY: help setup install init-db run ingest watch clean test

help:
	@echo "Life DB - Available commands:"
	@echo ""
	@echo "  make setup      - Set up the project (create venv, install deps, init db)"
	@echo "  make install    - Install Python dependencies"
	@echo "  make init-db    - Initialize the database"
	@echo "  make run        - Start the web server"
	@echo "  make ingest     - Ingest documents from ./data directory"
	@echo "  make watch      - Start file watcher for automatic indexing"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up generated files"
	@echo ""

setup:
	@bash setup.sh

install:
	@pip install -r requirements.txt

init-db:
	@python -m src.models.database

run:
	@echo "Starting Life DB web server..."
	@python -m src.api.main

ingest:
	@echo "Ingesting documents from ./data..."
	@python -m src.ingestion.ingestor ./data

watch:
	@echo "Starting file watcher..."
	@python -m src.utils.file_watcher ./data

test:
	@echo "Running tests..."
	@pytest tests/ -v

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@echo "✓ Cleaned up"
