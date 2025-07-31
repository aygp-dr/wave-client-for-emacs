#!/usr/bin/env bash
# Quick SQLite queries for Wave server database

DB_FILE="${1:-wave_server.db}"

if [ ! -f "$DB_FILE" ]; then
    echo "Database $DB_FILE not found!"
    exit 1
fi

echo "=== Wave Server Database Quick Queries ==="
echo "Database: $DB_FILE"
echo ""

echo "1. Table structure:"
sqlite3 "$DB_FILE" ".schema"
echo ""

echo "2. Wave count:"
sqlite3 "$DB_FILE" "SELECT COUNT(*) as wave_count FROM waves;"
echo ""

echo "3. Wavelet count:"
sqlite3 "$DB_FILE" "SELECT COUNT(*) as wavelet_count FROM wavelets;"
echo ""

echo "4. Recent wavelets:"
sqlite3 "$DB_FILE" <<EOF
.mode column
.headers on
SELECT 
    id,
    wave_id,
    wavelet_id,
    creator,
    version,
    datetime(creation_time) as created
FROM wavelets 
ORDER BY creation_time DESC 
LIMIT 5;
EOF
echo ""

echo "5. Document content preview:"
sqlite3 "$DB_FILE" <<EOF
.mode list
SELECT 
    wavelet_id,
    substr(docs, 1, 100) || '...' as docs_preview
FROM wavelets 
WHERE docs IS NOT NULL AND docs != '{}'
LIMIT 3;
EOF
echo ""

echo "6. Recent updates:"
sqlite3 "$DB_FILE" <<EOF
.mode column
.headers on
SELECT 
    id,
    wave_id,
    channel_id,
    datetime(timestamp) as time
FROM wavelet_updates 
ORDER BY timestamp DESC 
LIMIT 5;
EOF