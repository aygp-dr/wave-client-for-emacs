-- Wave Server Database Seed Data
-- This creates realistic test data for development

-- Clear existing data
DELETE FROM wavelet_updates;
DELETE FROM wavelets;
DELETE FROM waves;
-- Per-user state (created by the server; created here too so seeding a fresh DB works)
CREATE TABLE IF NOT EXISTS user_wave_state (
    id INTEGER NOT NULL PRIMARY KEY, user VARCHAR NOT NULL, wave_id VARCHAR NOT NULL,
    folder VARCHAR, archived BOOLEAN, muted BOOLEAN, spam BOOLEAN, trashed BOOLEAN,
    read_at DATETIME, tags JSON, UNIQUE (user, wave_id));
DELETE FROM user_wave_state;

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

-- Waves modelled on the 2009 Wave UI (experiments/014): threads, a public
-- wave with a Yes/No/Maybe gadget, and help waves that document the client.
INSERT INTO waves (wave_id, creator, created_at) VALUES
    ('localhost!w+io2009', 'dave@localhost', datetime('now', '-3 hours')),
    ('localhost!w+rsvp01', 'erin@localhost', datetime('now', '-2 days')),
    ('localhost!w+search', 'system@localhost', datetime('now', '-6 days')),
    ('localhost!w+welcome', 'system@localhost', datetime('now', '-7 days'));

INSERT INTO wavelets (wave_id, wavelet_id, creator, creation_time, version, history_hash, last_modified_time, participants, docs) VALUES
    ('localhost!w+io2009', 'localhost!conv+root', 'dave@localhost',
     datetime('now', '-3 hours'), 1, '', datetime('now', '-3 hours'),
     '["dave@localhost", "alice@localhost", "bob@localhost", "charlie@localhost", "erin@localhost"]',
     '{"main": {"content": ["So how was Google I/O for you?", {"type": "line"}, "Looking for fellow sandbox account holders who want to get some waves going.", {"type": "line"}, "Wave users so far: alice, bob, charlie, dave, erin"]}, "digest": {"content": ["So how was Google I/O for you?"]}}'),
    ('localhost!w+io2009', 'localhost!b+io1', 'bob@localhost',
     datetime('now', '-170 minutes'), 1, '', datetime('now', '-170 minutes'), '["bob@localhost"]',
     '{"main": {"content": ["hello all"]}, "thread": {"parent": "b+root"}}'),
    ('localhost!w+io2009', 'localhost!b+io2', 'charlie@localhost',
     datetime('now', '-160 minutes'), 1, '', datetime('now', '-160 minutes'), '["charlie@localhost"]',
     '{"main": {"content": ["I suppose they will not mind if we just started adding them, since they do not have any contacts to talk to either, right?"]}, "thread": {"parent": "b+io1"}}'),
    ('localhost!w+io2009', 'localhost!b+io3', 'bob@localhost',
     datetime('now', '-150 minutes'), 1, '', datetime('now', '-150 minutes'), '["bob@localhost"]',
     '{"main": {"content": ["yes, this works far better with someone other than yourself to test with."]}, "thread": {"parent": "b+io2"}}'),
    ('localhost!w+io2009', 'localhost!b+io4', 'erin@localhost',
     datetime('now', '-20 minutes'), 1, '', datetime('now', '-20 minutes'), '["erin@localhost"]',
     '{"main": {"content": ["Yes! Much better with other people... very cool system."]}, "thread": {"parent": "b+root"}}'),

    ('localhost!w+rsvp01', 'localhost!conv+root', 'erin@localhost',
     datetime('now', '-2 days'), 1, '', datetime('now', '-1 hour'),
     '["erin@localhost", "public@localhost", "alice@localhost", "bob@localhost", "charlie@localhost", "dave@localhost"]',
     '{"main": {"content": ["I am new to Wave and am bored, anyone want to chat to go through the features?", {"type": "line"}, {"type": "gadget", "attributes": {"id": "rsvp", "kind": "yesnomaybe", "title": "Who is in?"}}]}, "digest": {"content": ["New to Wave: anyone want to go through the features?"]}, "gadgets": {"rsvp": {"yes": ["alice@localhost", "dave@localhost"], "no": ["charlie@localhost"], "maybe": ["bob@localhost"]}}}'),
    ('localhost!w+rsvp01', 'localhost!b+rsvp1', 'alice@localhost',
     datetime('now', '-1 hour'), 1, '', datetime('now', '-1 hour'), '["alice@localhost"]',
     '{"main": {"content": ["sounds good to me"]}, "thread": {"parent": "b+root"}}'),

    ('localhost!w+search', 'localhost!conv+root', 'system@localhost',
     datetime('now', '-6 days'), 1, '', datetime('now', '-6 days'),
     '["system@localhost", "alice@localhost", "bob@localhost", "charlie@localhost", "dave@localhost", "erin@localhost"]',
     '{"main": {"content": ["Search Cheat Sheet", {"type": "line"}, "is:unread  is:read  is:muted  is:public", {"type": "line"}, "with:<name>  by:<name>  tag:<tag>", {"type": "line"}, "Anything else matches title and text. Terms combine with AND."]}, "digest": {"content": ["Search Cheat Sheet"]}}'),

    ('localhost!w+welcome', 'localhost!conv+root', 'system@localhost',
     datetime('now', '-7 days'), 1, '', datetime('now', '-7 days'),
     '["system@localhost", "alice@localhost", "bob@localhost", "charlie@localhost", "dave@localhost", "erin@localhost"]',
     '{"main": {"content": ["Welcome to Wave!", {"type": "line"}, "In Emacs: RET opens a wave, f picks a folder, s searches, r/u mark read/unread, a archives, m mutes.", {"type": "line"}, "On the web: /app (log in as your user name, password = user name)."]}, "digest": {"content": ["Welcome to Wave!"]}}');

INSERT INTO user_wave_state (user, wave_id, archived, muted, spam, trashed, read_at, tags) VALUES
    ('alice@localhost', 'localhost!w+welcome', 0, 0, 0, 0, datetime('now'), '["help"]'),
    ('alice@localhost', 'localhost!w+search', 0, 0, 0, 0, datetime('now'), '["help"]');

-- Summary
SELECT 'Database seeded with:' as message;
SELECT COUNT(*) || ' waves' as count FROM waves;
SELECT COUNT(*) || ' wavelets' as count FROM wavelets;
SELECT COUNT(*) || ' updates' as count FROM wavelet_updates;