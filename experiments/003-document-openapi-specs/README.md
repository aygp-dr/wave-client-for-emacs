# Experiment 003: Document OpenAPI Specifications

## Objective
Reverse-engineer the Wave API specification from client code and create comprehensive OpenAPI documentation.

## Approach
1. Analyze Emacs client HTTP/WebSocket calls
2. Extract expected request/response formats
3. Document Wave protocol operations (fetch, submit, etc.)
4. Create OpenAPI 3.0 specification

## Expected API Areas
- Session management
- Wavelet operations
- Blip CRUD operations
- Real-time updates (WebSocket)
- Authentication/authorization

## Outputs
- `wave-api.openapi.yaml` - Complete API specification
- Message schema definitions
- Example requests/responses
- Protocol documentation