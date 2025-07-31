.PHONY: help deps-check install dev test clean server dashboard .env

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deps-check: ## Check if required dependencies are installed
	@echo "Checking dependencies..."
	@command -v git >/dev/null 2>&1 || { echo "❌ git is not installed"; exit 1; }
	@echo "✅ git found: $$(git --version)"
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv is not installed"; exit 1; }
	@echo "✅ uv found: $$(uv --version)"
	@command -v hg >/dev/null 2>&1 || { echo "❌ hg (mercurial) is not installed"; exit 1; }
	@echo "✅ hg found: $$(hg --version | head -1)"
	@command -v tmux >/dev/null 2>&1 || { echo "⚠️  tmux is not installed (needed for dashboard)"; }
	@command -v tmux >/dev/null 2>&1 && echo "✅ tmux found: $$(tmux -V)"
	@command -v jq >/dev/null 2>&1 || { echo "⚠️  jq is not installed (optional for dashboard)"; }
	@command -v jq >/dev/null 2>&1 && echo "✅ jq found: $$(jq --version)"
	@echo "All required dependencies are installed! 🎉"

install: deps-check ## Install Python dependencies
	uv sync

dev: install ## Run development server
	uv run wave-client-server

server: install ## Run production server
	uv run uvicorn wave_client_server.wave_server:app --host 0.0.0.0 --port 9898

test: install ## Run tests
	@echo "Running tests..."
	@if [ -f "tests/test_*.py" ]; then \
		uv run pytest tests/; \
	else \
		echo "No Python tests found"; \
	fi
	@if [ -f "tests/wave-tests.el" ]; then \
		echo "Emacs Lisp tests found in tests/wave-tests.el"; \
		echo "Run with: emacs -batch -l tests/wave-tests.el"; \
	fi

clean: ## Clean up generated files
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf src/**/__pycache__/
	rm -rf *.egg-info/
	rm -f *.db
	rm -f *.sqlite
	rm -f *.sqlite3
	find . -name "*.pyc" -delete
	find . -name "*.elc" -delete

history: deps-check ## Show Mercurial history from original project
	@echo "Original Mercurial history:"
	hg log -R .hg

explore-hg: deps-check ## Explore original Mercurial repository contents
	@echo "Original repository structure:"
	hg manifest -R .hg

.env: ## Create .env from .env.example
	@if [ -f .env ]; then \
		echo ".env already exists. Remove it first to regenerate."; \
	else \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
		echo "Edit .env to configure your environment"; \
	fi

dashboard: install .env ## Run Wave server and Emacs client in tmux dashboard
	@./scripts/dashboard.sh

db-seed: ## Seed database with test data
	@echo "Seeding database with test data..."
	@sqlite3 wave_server.db < scripts/seed.sql
	@echo "Database seeded successfully!"

db-summary: ## Show database summary and statistics
	@echo "=== Wave Server Database Summary ==="
	@if [ -f wave_server.db ]; then \
		python3 scripts/check_db.py; \
	else \
		echo "No database found. Run 'make server' first to create it."; \
	fi

db-query: ## Interactive SQLite prompt for database queries
	@if [ -f wave_server.db ]; then \
		echo "Opening SQLite prompt. Type .help for commands, .quit to exit"; \
		sqlite3 wave_server.db; \
	else \
		echo "No database found. Run 'make server' first to create it."; \
	fi

db-report: ## Generate quick database report
	@if [ -f wave_server.db ]; then \
		./scripts/db_query.sh; \
	else \
		echo "No database found. Run 'make server' first to create it."; \
	fi