.DEFAULT_GOAL := help

##@ Setup

.PHONY: deps setup clean

deps: deps-check ## Install dependencies

setup: deps ## Initial project setup
	@echo "Setting up project..."

##@ Development

.PHONY: help deps-check install dev test test-python test-elisp lint lint-python format server dashboard .env README.md mock-server mock-validate mock-test test-connection test-api ws-listen ws-open-wave ws-test ws-test-interactive rest-client rest-client-mock rest-client-interactive wave-dashboard wave-monitor elisp-check-syntax elisp-load-test elisp-list-waves elisp-version elisp-http-inbox elisp-batch-demo screenshots gastown-sim gastown-sim-live

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*## .*' Makefile | sort

deps: deps-check

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

test: test-python test-elisp ## Run all tests

test-python: install ## Run Python tests
	@echo "Running Python tests..."
	uv run --extra test pytest -v

test-elisp: ## Run Elisp tests
	@echo "Running Elisp tests..."
	@./scripts/test-elisp.sh

lint: lint-python ## Run linters

lint-python: install ## Run Python linters
	@echo "Running Python linters..."
	uv run --extra dev ruff check src/ tests/
	uv run --extra dev mypy src/

format: install ## Format Python code
	@echo "Formatting Python code..."
	uv run --extra dev black src/ tests/
	uv run --extra dev ruff check --fix src/ tests/

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

README.md: README.org ## Generate README.md from README.org
	@echo "Generating README.md from README.org..."
	@emacs -Q -l org --batch --eval "(progn (find-file \"README.org\") (org-md-export-to-markdown))"
	@echo "README.md generated successfully!"

logs/websocket.log: ## Debugging support
	websocat -t ws://localhost:9898/ws - | tee $@

# WebSocket debugging targets
ws-listen: ## Listen to WebSocket messages from Wave server (port 9898)
	@command -v websocat >/dev/null 2>&1 || { echo "❌ websocat not found. Install with: cargo install websocat"; exit 1; }
	@echo "Connecting to ws://localhost:9898/ws ..."
	@echo "Type JSON messages to send, Ctrl-C to exit"
	websocat -v ws://localhost:9898/ws

ws-open-wave: ## Send ProtocolOpenRequest for index wave
	@command -v websocat >/dev/null 2>&1 || { echo "❌ websocat not found."; exit 1; }
	@python3 -c 'import json; print(json.dumps({"version":0,"sequenceNumber":1,"messageType":"ProtocolOpenRequest","messageJson":json.dumps({"2":"indexwave!indexwave"})}))' | websocat ws://localhost:9898/ws

ws-test: ## Run WebSocket test client
	python3 scripts/ws-test.py

ws-test-interactive: ## Interactive WebSocket client
	python3 scripts/ws-test.py --interactive

# Mock Server targets
mock-server: ## Run OpenAPI mock server using prism (port 4010)
	@command -v npx >/dev/null 2>&1 || { echo "❌ npx not found. Install Node.js first."; exit 1; }
	@echo "Starting Prism mock server on http://localhost:4010..."
	npx @stoplight/prism-cli mock specs/wave-api.openapi.yaml --port 4010 --host 0.0.0.0

mock-validate: ## Validate OpenAPI specification with Spectral
	@command -v npx >/dev/null 2>&1 || { echo "❌ npx not found. Install Node.js first."; exit 1; }
	@echo "Validating OpenAPI spec..."
	npx @stoplight/spectral-cli lint specs/wave-api.openapi.yaml --ruleset spectral:oas

mock-test: ## Test mock server endpoints with curl
	@echo "Testing mock server at http://localhost:4010..."
	@curl -sf http://localhost:4010/api/inbox >/dev/null && echo "✅ GET /api/inbox" || echo "❌ GET /api/inbox"
	@curl -sf "http://localhost:4010/api/waves/test" >/dev/null && echo "✅ GET /api/waves/{id}" || echo "❌ GET /api/waves/{id}"

test-connection: ## Test Emacs client can connect to Wave server
	@echo "Testing Emacs Wave client connection..."
	@emacs -Q -batch -l tests/http/connection-test.el 2>&1 || echo "Note: Run 'gmake server' first"

test-api: ## Quick API smoke test with curl
	@echo "Testing Wave server at http://localhost:9898..."
	@curl -sf http://localhost:9898/ >/dev/null && echo "✅ Server responding" || { echo "❌ Server not running"; exit 1; }
	@curl -sf http://localhost:9898/api/inbox >/dev/null && echo "✅ GET /api/inbox" || echo "⚠️  /api/inbox returned error"
	@echo "API tests complete"

rest-client: ## Run REST client tests against real server
	python3 scripts/rest-client.py

rest-client-mock: ## Run REST client tests against mock server
	python3 scripts/rest-client.py --mock

rest-client-interactive: ## Interactive REST client REPL
	python3 scripts/rest-client.py --interactive

wave-dashboard: ## Run Wave TUI dashboard
	python3 scripts/wave-dashboard.py

wave-monitor: ## Monitor WebSocket updates in real-time
	python3 scripts/wave-dashboard.py --ws

# Emacs batch mode targets
EMACS ?= $(HOME)/opt/emacs-30-amd64-freebsd/bin/emacs
EMACS_BATCH = $(EMACS) -Q --batch -L lisp

elisp-check-syntax: ## Check elisp syntax by byte-compiling
	@echo "Checking elisp syntax..."
	@$(EMACS_BATCH) --eval "(setq byte-compile-error-on-warn t)" \
		-f batch-byte-compile lisp/*.el 2>&1 | grep -E "^(lisp/|Error|Warning)" || true
	@rm -f lisp/*.elc
	@echo "Syntax check complete"

elisp-load-test: ## Test that all elisp files load without errors
	@echo "Testing elisp load..."
	@$(EMACS_BATCH) \
		--eval "(require 'cl)" \
		-l wave-util \
		-l wave-data \
		-l websocket \
		-l wave-client-websocket \
		-l wave-client-browser-channel \
		-l wave-client \
		-l wave-update \
		-l wave-display \
		-l wave-edit \
		-l wave-list \
		--eval "(message \"All wave-client modules loaded successfully\")"

elisp-list-waves: ## List waves from server in batch mode (requires running server)
	@echo "Fetching waves from localhost:9898..."
	@$(EMACS_BATCH) \
		--eval "(require 'cl)" \
		-l wave-util \
		-l wave-data \
		-l websocket \
		-l wave-client-websocket \
		-l wave-client \
		--eval "(progn \
			(setq wave-client-connection-method 'websocket) \
			(setq wave-client-ws-url \"ws://localhost:9898/ws\") \
			(setq wave-client-user \"batch@localhost\") \
			(setq wave-debug t) \
			(defvar batch-inbox-received nil) \
			(wave-client-ws-connect wave-client-ws-url) \
			(dotimes (_ 10) (accept-process-output nil 0.5)) \
			(wave-ws-get-inbox \
			  (lambda (inbox) \
			    (setq batch-inbox-received t) \
			    (message \"=== INBOX (%d waves) ===\" (length inbox)) \
			    (dolist (wave inbox) \
			      (message \"  %s: %s\" \
			        (plist-get wave :id) \
			        (plist-get wave :digest))))) \
			(dotimes (_ 20) \
			  (unless batch-inbox-received \
			    (accept-process-output nil 0.5))) \
			(unless batch-inbox-received \
			  (message \"Timeout waiting for inbox response\")))"

elisp-version: ## Show Emacs version being used
	@$(EMACS) --version | head -1

elisp-http-inbox: ## Fetch inbox via HTTP (simpler than WebSocket, requires server)
	@echo "Fetching inbox via HTTP from localhost:9898..."
	@$(EMACS_BATCH) \
		--eval "(require 'url)" \
		--eval "(require 'json)" \
		--eval "(let* ((buf (url-retrieve-synchronously \"http://localhost:9898/api/inbox\" t)) (json-object-type 'plist) (json-array-type 'list)) (with-current-buffer buf (goto-char url-http-end-of-headers) (let ((inbox (json-read))) (message \"=== INBOX (%d waves) ===\" (length inbox)) (dolist (wave inbox) (message \"  %s: %s\" (plist-get wave :id) (plist-get wave :digest))))))"

elisp-batch-demo: ## Run comprehensive batch mode demo (requires server)
	@$(EMACS_BATCH) -l scripts/wave-batch-demo.el

screenshots: ## Capture screenshots of Wave client (requires server, X11)
	@./scripts/capture-screenshots.sh

gastown-sim: ## Simulate gastown agent communication via Wave
	@python3 scripts/gastown-wave-sim.py

gastown-sim-live: ## Simulate gastown agents with live Wave server
	@python3 scripts/gastown-wave-sim.py --live

