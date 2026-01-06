# Wave Client Integration Test Suite Plan

## Overview

This document outlines a comprehensive integration test suite for the Wave Client for Emacs project. The suite covers REST API, WebSocket, TUI dashboard, and end-to-end scenarios.

## Current Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests | 17 | Complete |
| REST Integration | 4 | Partial |
| WebSocket Integration | 6 | Partial |
| TUI Dashboard | 0 | Missing |
| E2E Scenarios | 0 | Missing |

## Proposed Test Suite Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   └── test_wave_server.py        # Existing unit tests
├── integration/
│   ├── test_http_api.py           # Existing REST tests
│   ├── test_websocket.py          # Existing WebSocket tests
│   ├── test_rest_extended.py      # NEW: Extended REST coverage
│   ├── test_ws_extended.py        # NEW: Extended WebSocket coverage
│   ├── test_multi_client.py       # NEW: Multi-client scenarios
│   └── test_data_persistence.py   # NEW: Database consistency
├── tui/
│   ├── test_wave_client.py        # NEW: WaveClient class tests
│   ├── test_dashboard_display.py  # NEW: Display functions
│   └── test_dashboard_commands.py # NEW: Command parsing
└── e2e/
    ├── test_full_workflow.py      # NEW: Complete user journeys
    └── test_emacs_integration.py  # NEW: Elisp client scenarios
```

---

## 1. Extended REST API Tests (`test_rest_extended.py`)

### 1.1 Wave Lifecycle Tests
- [ ] Create wave with valid data
- [ ] Create wave with missing required fields (expect 422)
- [ ] Get wave that doesn't exist (expect 404)
- [ ] Create multiple waves, verify unique IDs
- [ ] Create wave, delete wave, verify gone

### 1.2 Wavelet Operations
- [ ] Create wavelet on existing wave
- [ ] Create wavelet on non-existent wave (expect 404)
- [ ] Update wavelet version
- [ ] Add participant to wavelet
- [ ] Remove participant from wavelet
- [ ] Add document to wavelet
- [ ] Modify document content

### 1.3 Inbox Operations
- [ ] Empty inbox returns empty list
- [ ] Create wave appears in inbox
- [ ] Inbox item shows correct unread status
- [ ] Inbox sorted by most recent

### 1.4 Delta Submission
- [ ] Submit add_participant delta
- [ ] Submit remove_participant delta
- [ ] Submit document_op delta (insert)
- [ ] Submit document_op delta (delete)
- [ ] Submit invalid delta (expect 400)
- [ ] Submit to non-existent wave (expect 404)
- [ ] Verify version increments after delta

### 1.5 Error Handling
- [ ] Malformed JSON request (expect 422)
- [ ] Wrong content-type header
- [ ] Request timeout handling
- [ ] Concurrent requests to same resource

---

## 2. Extended WebSocket Tests (`test_ws_extended.py`)

### 2.1 Connection Management
- [ ] Connect and receive welcome message
- [ ] Clean disconnect
- [ ] Reconnect after disconnect
- [ ] Multiple connections from same client
- [ ] Connection timeout/keepalive

### 2.2 Protocol Message Tests
- [ ] ProtocolOpenRequest with valid wave_id
- [ ] ProtocolOpenRequest with invalid wave_id
- [ ] ProtocolOpenRequest with malformed JSON
- [ ] ProtocolWaveletUpdate format validation
- [ ] Message sequence number tracking

### 2.3 Channel Management
- [ ] Channel assignment on open
- [ ] Channel cleanup on close
- [ ] Multiple waves on different channels
- [ ] Channel number uniqueness

### 2.4 Real-time Updates
- [ ] Open wave, receive initial state
- [ ] Update wave via REST, receive WebSocket notification
- [ ] Delta submission triggers broadcast
- [ ] Only subscribed clients receive updates

---

## 3. Multi-Client Tests (`test_multi_client.py`)

### 3.1 Concurrent Operations
- [ ] Two clients open same wave
- [ ] Client A updates, Client B receives notification
- [ ] Both clients submit deltas simultaneously
- [ ] Version conflict resolution
- [ ] Client disconnect doesn't affect other clients

### 3.2 Broadcast Tests
- [ ] Broadcast reaches all connected clients
- [ ] Broadcast excludes disconnected clients
- [ ] Personal message reaches only target client
- [ ] Broadcast with large number of clients (10+)

### 3.3 Race Conditions
- [ ] Simultaneous wave creation
- [ ] Simultaneous delta submission
- [ ] Connect during broadcast
- [ ] Disconnect during message send

---

## 4. Data Persistence Tests (`test_data_persistence.py`)

### 4.1 Database Consistency
- [ ] Wave creation persists to DB
- [ ] Wavelet updates persist to DB
- [ ] Server restart preserves data
- [ ] Concurrent writes maintain consistency
- [ ] Cascade delete works (wave → wavelets → updates)

### 4.2 History Tracking
- [ ] Updates recorded with timestamps
- [ ] Version history is complete
- [ ] History hash calculated correctly
- [ ] Can reconstruct wavelet state from history

### 4.3 JSON Field Handling
- [ ] Participants list serializes correctly
- [ ] Document content with special characters
- [ ] Large document content
- [ ] Empty document handling

---

## 5. TUI Dashboard Tests (`tests/tui/`)

### 5.1 WaveClient Class (`test_wave_client.py`)
- [ ] Initialize with default URLs
- [ ] Initialize with custom URLs
- [ ] HTTP GET request success
- [ ] HTTP GET request failure (connection error)
- [ ] HTTP GET request failure (4xx/5xx)
- [ ] get_inbox() parses response correctly
- [ ] get_inbox() handles empty inbox
- [ ] get_wave() parses wavelets correctly
- [ ] get_wave() handles missing wave
- [ ] WebSocket connection establishment
- [ ] WebSocket message parsing

### 5.2 Display Functions (`test_dashboard_display.py`)
- [ ] print_header() output format
- [ ] print_inbox() with items
- [ ] print_inbox() with empty inbox
- [ ] print_inbox() unread indicator
- [ ] print_wave() with wavelets
- [ ] print_wave() with documents
- [ ] print_wave() with participants
- [ ] print_help() complete output

### 5.3 Command Parser (`test_dashboard_commands.py`)
- [ ] Parse 'inbox' command
- [ ] Parse 'i' alias
- [ ] Parse 'open 1' command
- [ ] Parse 'wave <id>' command
- [ ] Parse 'refresh' / 'r' commands
- [ ] Parse 'quit' / 'q' commands
- [ ] Parse 'help' / 'h' / '?' commands
- [ ] Handle unknown command
- [ ] Handle empty input

---

## 6. End-to-End Tests (`tests/e2e/`)

### 6.1 Full User Workflow (`test_full_workflow.py`)
- [ ] **Scenario: New User Journey**
  1. Server starts fresh
  2. User connects via REST
  3. Creates first wave
  4. Adds participant
  5. Adds document
  6. Views in inbox
  7. Opens wave, sees content

- [ ] **Scenario: Collaborative Editing**
  1. User A creates wave
  2. User A adds User B as participant
  3. User B connects via WebSocket
  4. User B opens wave
  5. User A submits document delta
  6. User B receives update notification
  7. Both see consistent state

- [ ] **Scenario: TUI Dashboard Flow**
  1. Start server with seed data
  2. Launch dashboard
  3. List inbox
  4. Open wave by number
  5. View wavelet details
  6. Return to inbox
  7. Exit cleanly

- [ ] **Scenario: Error Recovery**
  1. Client connected
  2. Server restarts
  3. Client detects disconnect
  4. Client reconnects
  5. State is consistent

### 6.2 Emacs Integration (`test_emacs_integration.py`)
- [ ] Load wave-client.el successfully
- [ ] Connect to server via WebSocket
- [ ] wave-list-mode displays inbox
- [ ] Open wave in buffer
- [ ] Submit edit via Emacs client

---

## 7. Performance Tests (Optional)

### 7.1 Load Testing
- [ ] 100 concurrent connections
- [ ] 1000 waves in database
- [ ] Large wavelet (100KB document)
- [ ] Rapid message throughput

### 7.2 Stress Testing
- [ ] Connection churn (connect/disconnect rapidly)
- [ ] Memory usage under load
- [ ] Database growth over time

---

## Test Infrastructure Requirements

### Fixtures Needed
```python
@pytest.fixture
async def running_server():
    """Start server in subprocess, yield, cleanup"""

@pytest.fixture
async def seeded_database():
    """Database with known test data"""

@pytest.fixture
async def ws_client():
    """Connected WebSocket client"""

@pytest.fixture
async def http_client():
    """Configured httpx AsyncClient"""

@pytest.fixture
async def multiple_clients(n=3):
    """Multiple connected clients for multi-client tests"""
```

### Markers
```ini
[pytest:markers]
unit = Unit tests (no I/O)
integration = Integration tests (requires server)
websocket = WebSocket-specific tests
tui = TUI dashboard tests
e2e = End-to-end scenarios
slow = Tests that take >1s
```

---

## Implementation Priority

| Phase | Tests | Priority |
|-------|-------|----------|
| 1 | TUI WaveClient tests | High |
| 2 | Extended REST tests | High |
| 3 | Extended WebSocket tests | High |
| 4 | Multi-client tests | Medium |
| 5 | Data persistence tests | Medium |
| 6 | E2E workflow tests | Medium |
| 7 | Emacs integration | Low |
| 8 | Performance tests | Low |

---

## Success Metrics

- **Coverage Target**: 80%+ code coverage
- **Test Count Target**: 75+ integration tests
- **Execution Time**: Full suite < 60 seconds
- **Reliability**: 100% pass rate in CI
