const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:9898/ws');

ws.on('open', function open() {
  console.log('Connected to Wave Server WebSocket');
  
  // Send open wave request
  ws.send(JSON.stringify({
    type: 'open_wave',
    wave_id: 'localhost!w+abc123'
  }));
});

ws.on('message', function message(data) {
  console.log('Received:', JSON.parse(data));
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
});

ws.on('close', function close() {
  console.log('Disconnected from Wave Server');
});

// Keep the connection alive
setTimeout(() => {
  ws.close();
  process.exit(0);
}, 5000);
