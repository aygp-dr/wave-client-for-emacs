.PHONY: help tangle clean test

help: ## Show this help message
	@echo "Examples Makefile"
	@echo "================="
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

tangle: ## Tangle HTTP examples from README.org
	@echo "Tangling HTTP test files from README.org..."
	@emacs -Q --batch \
		--eval "(require 'org)" \
		--eval "(setq org-confirm-babel-evaluate nil)" \
		--eval "(find-file \"README.org\")" \
		--eval "(org-babel-tangle)" \
		--kill
	@echo "✓ Tangled files to ../tests/http/"
	@ls -la ../tests/http/*.http 2>/dev/null | head -10 || echo "No .http files generated"

clean: ## Remove tangled files
	@echo "Cleaning tangled files..."
	@rm -f ../tests/http/*.http
	@rm -f ../tests/http/*.js
	@rm -f ../tests/http/*.el
	@rm -f ../tests/integration/test_http_api.py
	@echo "✓ Cleaned tangled files"

test: tangle ## Run HTTP tests using httpie (if available)
	@if command -v http >/dev/null 2>&1; then \
		echo "Running health check test..."; \
		http GET localhost:9898/health; \
	else \
		echo "httpie not installed. Install with: pip install httpie"; \
		echo "You can also use these files with restclient-mode in Emacs"; \
	fi