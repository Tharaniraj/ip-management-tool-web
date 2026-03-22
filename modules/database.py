"""SQLite database backend for IP records (alternative to JSON)."""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_FILE = os.path.join(DB_DIR, "ip_records.db")


def _ensure_db_dir() -> None:
    """Ensure database directory exists."""
    os.makedirs(DB_DIR, exist_ok=True)


def init_database() -> bool:
    """Initialize or get the SQLite database, creating tables if needed."""
    _ensure_db_dir()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ip_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT UNIQUE NOT NULL,
                subnet TEXT NOT NULL,
                hostname TEXT,
                description TEXT,
                status TEXT NOT NULL,
                added_on TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ip ON ip_records(ip)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON ip_records(status)
        """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False


def load_records_sqlite() -> List[Dict]:
    """Load all IP records from SQLite database."""
    init_database()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT ip, subnet, hostname, description, status, added_on FROM ip_records ORDER BY ip")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception:
        return []


def save_records_sqlite(records: List[Dict]) -> bool:
    """Save all IP records to SQLite database (replaces all existing)."""
    init_database()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Clear existing records
        cursor.execute("DELETE FROM ip_records")
        
        # Insert new records
        for rec in records:
            cursor.execute("""
                INSERT INTO ip_records (ip, subnet, hostname, description, status, added_on)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rec.get("ip", ""),
                rec.get("subnet", ""),
                rec.get("hostname", ""),
                rec.get("description", ""),
                rec.get("status", "Active"),
                rec.get("added_on", datetime.now().strftime("%Y-%m-%d")),
            ))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_database_size() -> str:
    """Get human-readable database file size."""
    try:
        size = os.path.getsize(DB_FILE)
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    except Exception:
        return "0 bytes"


def export_db_to_json(json_file: str) -> bool:
    """Export SQLite database to JSON file."""
    try:
        records = load_records_sqlite()
        import json
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def import_json_to_db(json_file: str) -> bool:
    """Import JSON file into SQLite database."""
    try:
        import json
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)
        
        if isinstance(records, list):
            save_records_sqlite(records)
            return True
        return False
    except Exception:
        return False
