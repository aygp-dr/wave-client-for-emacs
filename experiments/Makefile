.DEFAULT_GOAL := help

##@ Experiments

.PHONY: help run list clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## .*' Makefile | sort

run: ## Run all experiments
	@echo "=== Running Wave Client Experiments ==="
	@$(MAKE) -s exp-gastown-sim
	@$(MAKE) -s exp-rest-client
	@$(MAKE) -s exp-ws-test
	@$(MAKE) -s exp-batch-demo
	@echo "=== All experiments complete ==="

list: ## List available experiments
	@echo "Available experiments:"
	@echo "  exp-gastown-sim    - Multi-agent Wave communication simulation"
	@echo "  exp-multi-agent    - Gas Town multi-agent demo (named characters)"
	@echo "  exp-agent-lore     - Literary references guide for agents"
	@echo "  exp-jwt-auth       - JWT authentication experiment"
	@echo "  exp-security       - Security hardening experiment"
	@echo "  exp-rest-client    - REST API client tests"
	@echo "  exp-ws-test        - WebSocket protocol tests"
	@echo "  exp-batch-demo     - Emacs batch mode demo"
	@echo "  exp-elisp-load     - Test Elisp module loading"
	@echo "  exp-db-summary     - Database inspection"

##@ Individual Experiments

exp-gastown-sim: ## Run Gastown agent simulation
	@echo ">>> Gastown Agent Simulation"
	@cd .. && python3 scripts/gastown-wave-sim.py 2>&1 | head -40
	@echo ""

exp-multi-agent: ## Run Gas Town multi-agent demo with named characters
	@echo ">>> Gas Town Multi-Agent Demo"
	@cd .. && python3 scripts/multi-agent-demo.py --scenario sprint --speed 0.1
	@echo ""

exp-agent-lore: ## Show literary references for Gas Town agents
	@echo ">>> Gas Town Agent Lore"
	@cd .. && python3 experiments/007-gastown-agent-lore/experiment.py
	@echo ""

exp-jwt-auth: ## Run JWT authentication experiment
	@echo ">>> JWT Authentication Experiment"
	@cd .. && python3 experiments/005-jwt-authentication/experiment.py
	@echo ""

exp-security: ## Run security hardening experiment
	@echo ">>> Security Hardening Experiment"
	@cd .. && python3 experiments/006-security-hardening/experiment.py
	@echo ""

exp-rest-client: ## Run REST client against server
	@echo ">>> REST Client Tests"
	@cd .. && python3 scripts/rest-client.py 2>&1 | head -30
	@echo ""

exp-ws-test: ## Run WebSocket tests
	@echo ">>> WebSocket Tests"
	@cd .. && python3 scripts/ws-test.py 2>&1 | head -20
	@echo ""

exp-batch-demo: ## Run Emacs batch demo
	@echo ">>> Emacs Batch Demo"
	@cd .. && gmake elisp-batch-demo 2>&1 | head -30
	@echo ""

exp-elisp-load: ## Test Elisp module loading
	@echo ">>> Elisp Load Test"
	@cd .. && gmake elisp-load-test 2>&1
	@echo ""

exp-db-summary: ## Show database summary
	@echo ">>> Database Summary"
	@cd .. && gmake db-summary 2>&1 | head -40
	@echo ""

##@ Research Experiments

exp-protocol-compliance: ## Check Wave protocol compliance
	@echo ">>> Protocol Compliance Check"
	@echo "Testing ProtocolOpenRequest format..."
	@cd .. && python3 -c "import json; print(json.dumps({'version':0,'sequenceNumber':1,'messageType':'ProtocolOpenRequest','messageJson':json.dumps({'2':'indexwave!indexwave'})}))"
	@echo ""

exp-concurrent-clients: ## Test concurrent WebSocket clients
	@echo ">>> Concurrent Client Test"
	@cd .. && python3 -c "\
import asyncio; \
import websockets; \
async def test(): \
    clients = [await websockets.connect('ws://localhost:9898/ws') for _ in range(3)]; \
    print(f'{len(clients)} clients connected'); \
    [await ws.close() for ws in clients]; \
    print('All disconnected'); \
asyncio.run(test())"
	@echo ""

exp-performance: ## Basic performance test
	@echo ">>> Performance Test"
	@cd .. && python3 -c "\
import time, httpx; \
start = time.time(); \
[httpx.get('http://localhost:9898/api/inbox') for _ in range(10)]; \
print(f'10 requests in {time.time()-start:.3f}s')"
	@echo ""

clean: ## Clean experiment artifacts
	@echo "Cleaning experiment artifacts..."
	@rm -f *.log *.out *.tmp
	@echo "Done"
