.PHONY: help run all clean

help: ## Show available experiments
	@echo "Available experiments:"
	@for dir in */; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "  $$dir"; \
		fi \
	done
	@echo ""
	@echo "Usage:"
	@echo "  make run          # Run all experiments in order"
	@echo "  make 001          # Run specific experiment"
	@echo "  make clean        # Clean all experiment outputs"

run: ## Run all experiments in numerical order
	@echo "Running all experiments..."
	@for dir in $$(ls -d */ | sort); do \
		echo "=== Running $$dir ==="; \
		$(MAKE) -C $$dir run || echo "$$dir failed"; \
		echo ""; \
	done

all: run ## Alias for run

clean: ## Clean all experiment outputs
	@for dir in */; do \
		if [ -f "$$dir/Makefile" ]; then \
			$(MAKE) -C $$dir clean; \
		fi \
	done

# Dynamic targets for each experiment directory
001: ## Run experiment 001
	$(MAKE) -C 001-explore-server-code run

002: ## Run experiment 002
	$(MAKE) -C 002-analyze-emacs-lisp run

003: ## Run experiment 003
	$(MAKE) -C 003-document-openapi-specs run

004: ## Run experiment 004
	$(MAKE) -C 004-fastapi-openapi-generation run