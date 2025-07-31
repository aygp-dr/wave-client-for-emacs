# Research Experiments

This directory contains research experiments for exploring the Wave client implementation and developing new server components.

## Experiment Naming Convention

Experiments use a `###-experiment-name` format for easy ordering and tracking.

## Planned Experiments

### 001-explore-server-code
**Objective**: Analyze the original Clojure server implementation from Mercurial history
**Scope**: 
- Extract and examine `src/client.clj` from `.hg/store/data/`
- Understand the original Wave protocol integration
- Analyze dependencies (fedone-api, protobuf, etc.)
- Document the original architecture

**Expected Outputs**:
- Clojure source code extraction
- Architecture documentation
- Dependency analysis
- Protocol implementation notes

### 002-analyze-emacs-lisp
**Objective**: Deep dive into the Emacs Lisp client implementation
**Scope**:
- Map out the module structure and responsibilities
- Understand the WebSocket and browser channel protocols
- Analyze data structures and message handling
- Document the client-server communication patterns

**Expected Outputs**:
- Module dependency graph
- Protocol message documentation
- Client architecture overview
- API surface analysis

### 003-document-openapi-specs
**Objective**: Reverse-engineer and document the Wave API as OpenAPI specifications
**Scope**:
- Based on Emacs client code, infer the expected API endpoints
- Document message formats and data structures
- Create comprehensive OpenAPI 3.0 specification
- Include examples and test cases

**Expected Outputs**:
- `wave-api.openapi.yaml` specification
- API documentation
- Message schema definitions
- Example request/response pairs

### 004-fastapi-openapi-generation
**Objective**: Implement FastAPI server that exposes compliant OpenAPI specs
**Scope**:
- Create FastAPI endpoints matching the documented API
- Auto-generate OpenAPI documentation
- Implement request/response validation
- Add interactive API documentation (Swagger UI)

**Expected Outputs**:
- Enhanced FastAPI server implementation
- Auto-generated OpenAPI docs at `/docs`
- Request/response validation
- Interactive API testing interface

## Running Experiments

Each experiment directory will contain:
- `README.md` - Experiment objectives and methodology
- `run.sh` - Script to execute the experiment
- `results/` - Output data and findings
- `notes.md` - Research notes and observations