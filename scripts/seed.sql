-- Wave Server Database Seed Data
-- This creates realistic test data for development

-- Clear existing data
DELETE FROM wavelet_updates;
DELETE FROM wavelets;
DELETE FROM waves;

-- Insert test waves
INSERT INTO waves (wave_id, creator, created_at) VALUES
    ('indexwave!indexwave', 'system@localhost', datetime('now', '-7 days')),
    ('localhost!w+abc123', 'alice@localhost', datetime('now', '-5 days')),
    ('localhost!w+def456', 'bob@localhost', datetime('now', '-3 days')),
    ('localhost!w+ghi789', 'alice@localhost', datetime('now', '-1 day'));

-- Insert wavelets (conversation roots and replies)
INSERT INTO wavelets (wave_id, wavelet_id, creator, creation_time, version, history_hash, last_modified_time, participants, docs) VALUES
    -- Index wavelet (inbox)
    ('indexwave!indexwave', 'indexwave!indexwave', 'system@localhost', 
     datetime('now', '-7 days'), 1, 'hash0', datetime('now', '-7 days'),
     '["system@localhost"]',
     '{"main": {"docId": "main", "contributors": ["system@localhost"], "content": ["Wave Server Index"]}}'),
    
    -- Alice's first wave
    ('localhost!w+abc123', 'localhost!conv+root', 'alice@localhost',
     datetime('now', '-5 days'), 3, 'hash1', datetime('now', '-4 days'),
     '["alice@localhost", "bob@localhost", "charlie@localhost"]',
     '{"main": {"docId": "main", "contributors": ["alice@localhost", "bob@localhost"], "content": ["Welcome to our discussion about Wave protocol!", {"type": "line"}, "Alice: I think the real-time collaboration features are amazing.", {"type": "line"}, "Bob: Agreed! The operational transformation is clever."]}, "digest": {"docId": "digest", "contributors": ["alice@localhost"], "content": ["Discussion: Wave protocol features"]}}'),
    
    -- Bob's wave
    ('localhost!w+def456', 'localhost!conv+root', 'bob@localhost',
     datetime('now', '-3 days'), 2, 'hash2', datetime('now', '-2 days'),
     '["bob@localhost", "alice@localhost"]',
     '{"main": {"docId": "main", "contributors": ["bob@localhost", "alice@localhost"], "content": ["Testing the new Emacs client", {"type": "line"}, "Bob: The WebSocket connection seems stable now.", {"type": "line"}, "Alice: Great! How about trying some editing operations?"]}, "digest": {"docId": "digest", "contributors": ["bob@localhost"], "content": ["Emacs client testing"]}}'),
    
    -- Alice's recent wave with image
    ('localhost!w+ghi789', 'localhost!conv+root', 'alice@localhost',
     datetime('now', '-1 day'), 4, 'hash3', datetime('now', '-6 hours'),
     '["alice@localhost", "charlie@localhost"]',
     '{"main": {"docId": "main", "contributors": ["alice@localhost", "charlie@localhost"], "content": ["Check out this architecture diagram:", {"type": "line"}, {"type": "image", "attributes": {"url": "http://localhost:9898/attachments/architecture.png", "width": "600", "height": "400"}}, {"type": "line"}, "Alice: This shows how the Wave server handles operations.", {"type": "line"}, "Charlie: Nice! The event sourcing pattern makes sense."]}, "digest": {"docId": "digest", "contributors": ["alice@localhost"], "content": ["Architecture discussion with diagram"]}}'),
    
    -- Nested blip example
    ('localhost!w+abc123', 'localhost!b+reply1', 'charlie@localhost',
     datetime('now', '-4 days', '+2 hours'), 1, 'hash4', datetime('now', '-4 days', '+2 hours'),
     '["charlie@localhost"]',
     '{"main": {"docId": "main", "contributors": ["charlie@localhost"], "content": ["Charlie: Don''t forget about the conflict resolution algorithms!"]}}');

-- Insert some wavelet updates (simulating real-time activity)
INSERT INTO wavelet_updates (wave_id, wavelet_id, channel_id, update_data, timestamp) VALUES
    ('localhost!w+abc123', 'localhost!conv+root', 1, 
     '{"type": "ProtocolWaveletUpdate", "operations": [{"type": "documentOp", "docId": "main", "components": [{"type": "retain", "count": 50}, {"type": "characters", "text": " Updated!"}]}]}',
     datetime('now', '-4 days')),
    
    ('localhost!w+def456', 'localhost!conv+root', 2,
     '{"type": "ProtocolWaveletUpdate", "operations": [{"type": "addParticipant", "participant": "alice@localhost"}]}',
     datetime('now', '-2 days')),
    
    ('localhost!w+ghi789', 'localhost!conv+root', 3,
     '{"type": "ProtocolWaveletUpdate", "operations": [{"type": "documentOp", "docId": "main", "components": [{"type": "elementStart", "element": {"type": "blip"}}, {"type": "characters", "text": "New blip content"}, {"type": "elementEnd"}]}]}',
     datetime('now', '-6 hours'));

-- Create some realistic inbox entries by updating the index
UPDATE wavelets 
SET docs = json_set(
    docs,
    '$.inbox',
    json('[' ||
        '{"waveId": "localhost!w+abc123", "title": "Discussion: Wave protocol features", "snippet": "Welcome to our discussion about Wave protocol!", "unread": 2, "lastModified": "' || datetime('now', '-4 days') || '"},' ||
        '{"waveId": "localhost!w+def456", "title": "Emacs client testing", "snippet": "Testing the new Emacs client", "unread": 0, "lastModified": "' || datetime('now', '-2 days') || '"},' ||
        '{"waveId": "localhost!w+ghi789", "title": "Architecture discussion with diagram", "snippet": "Check out this architecture diagram:", "unread": 1, "lastModified": "' || datetime('now', '-6 hours') || '"}' ||
    ']')
)
WHERE wave_id = 'indexwave!indexwave' AND wavelet_id = 'indexwave!indexwave';

-- Summary
SELECT 'Database seeded with:' as message;
SELECT COUNT(*) || ' waves' as count FROM waves;
SELECT COUNT(*) || ' wavelets' as count FROM wavelets;
SELECT COUNT(*) || ' updates' as count FROM wavelet_updates;