#!/usr/bin/env python3
"""Quick database inspection script for Wave server"""

import sqlite3
import json
from datetime import datetime
import sys
from pathlib import Path

def check_database(db_path="wave_server.db"):
    """Inspect the Wave server SQLite database"""
    
    if not Path(db_path).exists():
        print(f"Database {db_path} not found!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print(f"=== Wave Server Database Report ===")
    print(f"Database: {db_path}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # List all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables: {', '.join(tables)}")
    print()
    
    # Check waves table
    if 'waves' in tables:
        print("=== WAVES ===")
        cur.execute("SELECT COUNT(*) FROM waves")
        count = cur.fetchone()[0]
        print(f"Total waves: {count}")
        
        cur.execute("SELECT * FROM waves LIMIT 10")
        waves = cur.fetchall()
        for wave in waves:
            print(f"  - {dict(wave)}")
        print()
    
    # Check wavelets table
    if 'wavelets' in tables:
        print("=== WAVELETS ===")
        cur.execute("SELECT COUNT(*) FROM wavelets")
        count = cur.fetchone()[0]
        print(f"Total wavelets: {count}")
        
        cur.execute("SELECT * FROM wavelets LIMIT 10")
        wavelets = cur.fetchall()
        for wavelet in wavelets:
            data = dict(wavelet)
            # Pretty print JSON fields
            if data.get('docs'):
                data['docs'] = json.loads(data['docs']) if isinstance(data['docs'], str) else data['docs']
            if data.get('participants'):
                data['participants'] = json.loads(data['participants']) if isinstance(data['participants'], str) else data['participants']
            
            print(f"\n  Wavelet: {data['wavelet_id']}")
            print(f"    Wave ID: {data['wave_id']}")
            print(f"    Creator: {data['creator']}")
            print(f"    Version: {data['version']}")
            print(f"    Participants: {data['participants']}")
            if data.get('docs'):
                print(f"    Documents:")
                for doc_id, doc in data['docs'].items():
                    print(f"      - {doc_id}: {doc.get('content', [])[:50]}...")
        print()
    
    # Check wavelet_updates table
    if 'wavelet_updates' in tables:
        print("=== WAVELET UPDATES ===")
        cur.execute("SELECT COUNT(*) FROM wavelet_updates")
        count = cur.fetchone()[0]
        print(f"Total updates: {count}")
        
        cur.execute("SELECT * FROM wavelet_updates ORDER BY timestamp DESC LIMIT 5")
        updates = cur.fetchall()
        for update in updates:
            data = dict(update)
            print(f"\n  Update {data['id']}:")
            print(f"    Wave/Wavelet: {data['wave_id']}/{data['wavelet_id']}")
            print(f"    Channel: {data['channel_id']}")
            print(f"    Timestamp: {data['timestamp']}")
            if data.get('update_data'):
                print(f"    Data: {json.loads(data['update_data']) if isinstance(data['update_data'], str) else data['update_data']}")
    
    conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "wave_server.db"
    check_database(db_path)