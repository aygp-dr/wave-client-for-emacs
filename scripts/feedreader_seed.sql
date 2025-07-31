-- Feed Reader Database Seed Data
-- This creates a tech/programming focused feed reader similar to the screenshot

-- Clear existing data
DELETE FROM read_status;
DELETE FROM feed_categories;
DELETE FROM articles;
DELETE FROM feeds;
DELETE FROM categories;

-- Insert Categories
INSERT INTO categories (id, name, color, icon, priority) VALUES
('tech', 'Technology', '#2196F3', '💻', 1),
('programming', 'Programming', '#4CAF50', '👨‍💻', 2),
('security', 'Security', '#F44336', '🔒', 3),
('opensource', 'Open Source', '#FF9800', '🌟', 4),
('web', 'Web Development', '#9C27B0', '🌐', 5),
('mobile', 'Mobile', '#00BCD4', '📱', 6),
('data', 'Data Science', '#795548', '📊', 7),
('devops', 'DevOps', '#607D8B', '🔧', 8);

-- Insert Feeds
INSERT INTO feeds (id, title, url, description, last_updated, icon_url, active) VALUES
('hn001', 'Hacker News', 'https://news.ycombinator.com/rss', 'Links for the intellectually curious, ranked by readers.', datetime('now'), 'https://news.ycombinator.com/favicon.ico', 1),
('reddit-prog', 'r/programming', 'https://www.reddit.com/r/programming/.rss', 'Computer Programming discussions', datetime('now'), 'https://www.reddit.com/favicon.ico', 1),
('arstech', 'Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index', 'Serving the Technologist', datetime('now'), 'https://arstechnica.com/favicon.ico', 1),
('github-trending', 'GitHub Trending', 'https://github.com/trending', 'Trending repositories on GitHub', datetime('now'), 'https://github.com/favicon.ico', 1),
('techcrunch', 'TechCrunch', 'https://techcrunch.com/feed/', 'Startup and Technology News', datetime('now'), 'https://techcrunch.com/favicon.ico', 1),
('lobsters', 'Lobsters', 'https://lobste.rs/rss', 'Computing-focused community centered around link aggregation', datetime('now'), 'https://lobste.rs/favicon.ico', 1),
('slashdot', 'Slashdot', 'https://rss.slashdot.org/Slashdot/slashdotMain', 'News for nerds, stuff that matters', datetime('now'), 'https://slashdot.org/favicon.ico', 1),
('dev-to', 'DEV Community', 'https://dev.to/feed', 'Where programmers share ideas', datetime('now'), 'https://dev.to/favicon.ico', 1);

-- Insert Articles (mixing different times to create a realistic feed)
INSERT INTO articles (id, feed_id, title, content, summary, author, published, url, thumbnail_url, starred) VALUES
-- Recent unread articles (within last few hours)
('art001', 'hn001', 'Show HN: I built a distributed key-value store in Rust', '<p>Hey HN! I spent the last 6 months building a distributed key-value store in Rust. It supports:</p><ul><li>Raft consensus</li><li>Automatic sharding</li><li>ACID transactions</li></ul><p>Performance benchmarks show 100k ops/sec on commodity hardware.</p>', 'A new distributed key-value store implementation in Rust with Raft consensus and automatic sharding...', 'rustacean42', datetime('now', '-1 hours'), 'https://github.com/example/kvstore', NULL, 0),

('art002', 'reddit-prog', 'The Architecture of Open Source Applications', '<p>Found this amazing resource that breaks down the architecture of popular open source projects. Really helpful for understanding how large-scale applications are structured.</p>', 'Amazing resource breaking down architectures of popular open source projects...', 'codemaster99', datetime('now', '-2 hours'), 'https://aosabook.org/', NULL, 0),

('art003', 'arstech', 'Apple Silicon M4 benchmarks leaked: 20% faster than M3', '<p>Early benchmarks of Apple''s upcoming M4 chip have surfaced, showing significant performance improvements over the current M3 generation. Single-core performance is up 20%, while multi-core shows a 35% improvement.</p>', 'Early M4 benchmarks show 20% single-core and 35% multi-core improvements over M3...', 'Samuel Axon', datetime('now', '-3 hours'), 'https://arstechnica.com/gadgets/2024/apple-m4', 'https://cdn.arstechnica.net/m4-chip.jpg', 1),

('art004', 'github-trending', 'awesome-rust: A curated list of Rust code and resources', '<p>Curated list of Rust code and resources. Updated daily with new libraries, tools, and learning materials.</p>', 'Comprehensive collection of Rust libraries, tools, and learning resources...', 'rust-unofficial', datetime('now', '-4 hours'), 'https://github.com/rust-unofficial/awesome-rust', NULL, 0),

('art005', 'techcrunch', 'OpenAI announces GPT-5 with 10x parameter count', '<p>OpenAI has announced GPT-5, featuring 1.7 trillion parameters and breakthrough reasoning capabilities. The model shows significant improvements in mathematical reasoning and code generation.</p>', 'OpenAI''s GPT-5 features 1.7 trillion parameters with breakthrough reasoning capabilities...', 'Kyle Wiggers', datetime('now', '-5 hours'), 'https://techcrunch.com/2024/openai-gpt5', NULL, 0),

-- Yesterday's articles (mix of read and unread)
('art006', 'lobsters', 'Writing a compiler in Zig', '<p>Tutorial series on building a compiler from scratch using Zig. Part 1 covers lexical analysis and tokenization.</p>', 'Comprehensive tutorial on building a compiler from scratch using Zig programming language...', 'zigdev', datetime('now', '-1 days'), 'https://example.com/zig-compiler', NULL, 0),

('art007', 'slashdot', 'Linux 6.8 Released With Major Performance Improvements', '<p>Linus Torvalds announced the release of Linux kernel 6.8, featuring significant performance improvements for AMD and Intel processors, better support for Rust modules, and enhanced security features.</p>', 'Linux 6.8 brings major performance improvements and enhanced Rust support...', 'BeauHD', datetime('now', '-1 days'), 'https://kernel.org/linux-6.8', NULL, 0),

('art008', 'dev-to', 'Understanding WebAssembly: A Practical Guide', '<p>WebAssembly (WASM) is revolutionizing web development. This guide covers everything from basic concepts to advanced optimization techniques.</p><pre><code>// Example WASM module\n(module\n  (func $add (param $a i32) (param $b i32) (result i32)\n    local.get $a\n    local.get $b\n    i32.add))</code></pre>', 'Comprehensive guide to WebAssembly from basics to advanced optimization...', 'wasmwizard', datetime('now', '-1 days'), 'https://dev.to/wasm-guide', NULL, 1),

('art009', 'hn001', 'Ask HN: What are you working on? (March 2024)', '<p>It''s that time again! Share what you''re working on - side projects, startups, research, whatever!</p>', 'Monthly thread for sharing current projects and getting feedback from the community...', 'dang', datetime('now', '-1 days'), 'https://news.ycombinator.com/item?id=38999', NULL, 0),

('art010', 'reddit-prog', '[AMA] I maintain a 20-year-old open source project', '<p>I''ve been maintaining an open source parsing library for 20 years. Happy to answer questions about long-term maintenance, dealing with breaking changes, community management, etc.</p>', 'AMA with maintainer of 20-year-old open source parsing library...', 'oldschooldev', datetime('now', '-1 days'), 'https://reddit.com/r/programming/ama20year', NULL, 0),

-- Two days ago (mostly read)
('art011', 'arstech', 'The rise of RISC-V: Open source takes on ARM and x86', '<p>RISC-V adoption is accelerating as major tech companies invest in the open instruction set architecture. Google, Intel, and others are contributing to the ecosystem.</p>', 'RISC-V gains momentum with support from major tech companies...', 'Jim Salter', datetime('now', '-2 days'), 'https://arstechnica.com/gadgets/riscv-rise', NULL, 0),

('art012', 'github-trending', 'htmx - high power tools for HTML', '<p>htmx gives you access to AJAX, CSS Transitions, WebSockets and Server Sent Events directly in HTML, using attributes.</p>', 'Access AJAX, WebSockets, and more directly in HTML using attributes...', 'bigskysoftware', datetime('now', '-2 days'), 'https://github.com/bigskysoftware/htmx', NULL, 0),

('art013', 'techcrunch', 'Rust Foundation announces $1M grant program', '<p>The Rust Foundation announced a new $1 million grant program to support critical Rust infrastructure projects and maintainers.</p>', 'Rust Foundation launches grant program for infrastructure and maintainers...', 'Frederic Lardinois', datetime('now', '-2 days'), 'https://techcrunch.com/rust-foundation-grants', NULL, 0),

('art014', 'lobsters', 'Database indexing strategies: B-trees vs LSM trees', '<p>Comprehensive comparison of B-tree and LSM tree indexing strategies, with benchmarks across different workloads.</p>', 'In-depth comparison of B-tree and LSM tree database indexing strategies...', 'dbexpert', datetime('now', '-2 days'), 'https://example.com/btree-vs-lsm', NULL, 0),

('art015', 'slashdot', 'Firefox 124 Adds Experimental Support for WebGPU', '<p>Mozilla Firefox 124 introduces experimental WebGPU support, enabling high-performance graphics and compute workloads in the browser.</p>', 'Firefox 124 brings experimental WebGPU support for browser-based graphics...', 'msmash', datetime('now', '-2 days'), 'https://mozilla.org/firefox-124', NULL, 0),

-- Three days ago
('art016', 'dev-to', 'Building a Real-time Collaboration Tool with WebRTC', '<p>Learn how to build a real-time collaboration tool using WebRTC, including peer-to-peer connections, data channels, and screen sharing.</p>', 'Tutorial on building real-time collaboration with WebRTC...', 'webrtcdev', datetime('now', '-3 days'), 'https://dev.to/webrtc-collab', NULL, 0),

('art017', 'hn001', 'Show HN: Terminal-based system monitor written in Go', '<p>I created a terminal-based system monitor in Go with real-time CPU, memory, disk, and network statistics. Features a responsive TUI built with Bubble Tea.</p>', 'Terminal system monitor in Go with real-time statistics and responsive TUI...', 'gopher2024', datetime('now', '-3 days'), 'https://github.com/example/gomonitor', NULL, 0),

('art018', 'reddit-prog', 'The most important programming book I''ve ever read', '<p>After 15 years in the industry, I finally read "Structure and Interpretation of Computer Programs" and it completely changed how I think about code.</p>', 'Why SICP remains relevant after decades in the industry...', 'wisdomseeker', datetime('now', '-3 days'), 'https://reddit.com/r/programming/sicp', NULL, 1),

('art019', 'arstech', 'Quantum computing hits new milestone: 1000 qubit processor', '<p>IBM announces successful test of 1000+ qubit quantum processor, marking significant progress toward practical quantum computing applications.</p>', 'IBM achieves 1000+ qubit quantum processor milestone...', 'John Timmer', datetime('now', '-3 days'), 'https://arstechnica.com/science/quantum-1000', NULL, 0),

('art020', 'github-trending', 'LocalLLM - Run LLMs on your own hardware', '<p>Framework for running large language models locally with optimized inference, quantization support, and easy model management.</p>', 'Run LLMs locally with optimized inference and model management...', 'localai-team', datetime('now', '-3 days'), 'https://github.com/localai/localllm', NULL, 0);

-- Set read status for some articles (older ones are more likely to be read)
INSERT INTO read_status (article_id, is_read, read_at) VALUES
('art007', 1, datetime('now', '-1 days')),
('art008', 1, datetime('now', '-1 days')),
('art010', 1, datetime('now', '-1 days')),
('art011', 1, datetime('now', '-2 days')),
('art012', 1, datetime('now', '-2 days')),
('art013', 1, datetime('now', '-2 days')),
('art014', 1, datetime('now', '-2 days')),
('art015', 1, datetime('now', '-2 days')),
('art016', 1, datetime('now', '-3 days')),
('art017', 1, datetime('now', '-3 days')),
('art019', 1, datetime('now', '-3 days')),
('art020', 1, datetime('now', '-3 days'));

-- Assign feeds to categories
INSERT INTO feed_categories (feed_id, category_id) VALUES
('hn001', 'tech'),
('hn001', 'programming'),
('reddit-prog', 'programming'),
('reddit-prog', 'opensource'),
('arstech', 'tech'),
('github-trending', 'opensource'),
('github-trending', 'programming'),
('techcrunch', 'tech'),
('lobsters', 'programming'),
('lobsters', 'web'),
('slashdot', 'tech'),
('slashdot', 'opensource'),
('dev-to', 'programming'),
('dev-to', 'web');

-- Add some more varied content to match the screenshot density
INSERT INTO articles (id, feed_id, title, content, summary, author, published, url, thumbnail_url, starred) VALUES
('art021', 'hn001', 'PostgreSQL 17 Beta Released with JSON_TABLE Support', '<p>PostgreSQL 17 beta includes SQL/JSON standard JSON_TABLE support, improved query performance, and better parallel query execution.</p>', 'PostgreSQL 17 beta brings JSON_TABLE support and performance improvements...', 'pg_enthusiast', datetime('now', '-6 hours'), 'https://postgresql.org/pg17-beta', NULL, 0),

('art022', 'dev-to', 'CSS Grid vs Flexbox: When to Use Each', '<p>Comprehensive guide comparing CSS Grid and Flexbox with practical examples and use cases for modern web layouts.</p>', 'Practical guide for choosing between CSS Grid and Flexbox...', 'cssmaster', datetime('now', '-7 hours'), 'https://dev.to/grid-vs-flex', NULL, 0),

('art023', 'reddit-prog', 'My experience porting 100k LOC from Python to Rust', '<p>Detailed write-up on porting a large Python codebase to Rust, including performance gains, challenges faced, and lessons learned.</p>', 'Lessons learned porting 100k lines from Python to Rust...', 'oxidizer', datetime('now', '-8 hours'), 'https://reddit.com/python-to-rust', NULL, 0),

('art024', 'techcrunch', 'GitHub Copilot adds support for additional languages', '<p>GitHub announces Copilot support for Rust, Swift, and Kotlin, along with improved context awareness and code generation quality.</p>', 'GitHub Copilot expands language support and improves code generation...', 'Sarah Perez', datetime('now', '-9 hours'), 'https://techcrunch.com/copilot-languages', NULL, 0),

('art025', 'lobsters', 'Understanding memory ordering in C++', '<p>Deep dive into C++ memory ordering, atomics, and the happens-before relationship with practical examples.</p>', 'Comprehensive guide to C++ memory ordering and atomics...', 'cppwizard', datetime('now', '-10 hours'), 'https://example.com/cpp-memory', NULL, 0);