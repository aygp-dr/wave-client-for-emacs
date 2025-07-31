# Experiment 002: Analyze Emacs Lisp Implementation

## Objective
Map out the Emacs Lisp client architecture and understand the client-server communication patterns.

## Files to Analyze
- `wave-client.el` - Main client interface
- `wave-client-websocket.el` - WebSocket communication
- `wave-client-browser-channel.el` - Browser channel protocol
- `wave-data.el` - Data structures and models
- `wave-display.el` - UI and rendering
- `wave-edit.el` - Editing operations
- `wave-util.el` - Utility functions

## Research Questions
1. What protocols does the client support (WebSocket vs browser channel)?
2. What API endpoints does it expect?
3. How are Wave operations (blips, wavelets) modeled?
4. What's the message format for client-server communication?

## Expected Outputs
- Module dependency graph
- API endpoint documentation
- Message format specifications
- Client state management analysis