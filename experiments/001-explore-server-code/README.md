# Experiment 001: Explore Server Code

## Objective
Analyze the original Clojure server implementation from Mercurial history to understand the Wave protocol integration and original architecture.

## Methodology
1. Extract Clojure source files from `.hg/store/data/`
2. Analyze the fedone-api and Wave protocol dependencies
3. Document the original server architecture
4. Compare with modern Wave implementations

## Files to Examine
- `src/client.clj` (2.8KB) - Main Clojure client implementation
- `start-repl.sh` (553 bytes) - REPL startup script
- JAR dependencies:
  - `fedone-api-0.2.jar` (433KB)
  - `fedone-server-0.2.jar` (2.7MB)
  - `clojure-1.0.0.jar` (1.31MB)
  - `protobuf-java-2.1.0.jar` (265KB)

## Research Questions
1. Was this a client or server implementation?
2. How did it interface with the Wave protocol?
3. What was the relationship to the Emacs Lisp client?
4. Should we reimplement in Clojure vs Python/FastAPI?

## Expected Outputs
- Extracted Clojure source code
- Architecture analysis document
- Dependency relationship map
- Recommendation for modern implementation