"""Data backup and recovery utilities."""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "ip_data.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
DELETED_FILE = os.path.join(DATA_DIR, "deleted_records.json")


def _ensure_backup_dir() -> None:
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup() -> bool:
    """
    Create a timestamped backup of the current data file.
    Returns True if backup was created successfully, False otherwise.
    """
    if not os.path.exists(DATA_FILE):
        return False
    
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"ip_data_backup_{timestamp}.json")
    
    try:
        shutil.copy2(DATA_FILE, backup_path)
        return True
    except Exception:
        return False


def cleanup_old_backups(keep_count: int = 10) -> None:
    """
    Remove old backup files, keeping only the most recent `keep_count` backups.
    """
    _ensure_backup_dir()
    
    try:
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith("ip_data_backup_")],
            reverse=True
        )
        
        # Delete backups beyond the keep_count limit
        for backup in backups[keep_count:]:
            backup_path = os.path.join(BACKUP_DIR, backup)
            try:
                os.remove(backup_path)
            except Exception:
                pass
    except Exception:
        pass


def save_deleted_record(record: dict) -> bool:
    """
    Save a deleted record to the deleted_records file for recovery.
    Returns True on success.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    try:
        deleted = []
        if os.path.exists(DELETED_FILE):
            with open(DELETED_FILE, "r", encoding="utf-8") as f:
                deleted = json.load(f)
        
        record_copy = record.copy()
        record_copy["deleted_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        deleted.append(record_copy)
        
        with open(DELETED_FILE, "w", encoding="utf-8") as f:
            json.dump(deleted, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception:
        return False


def get_deleted_records() -> list:
    """Load all deleted records from the deleted_records file."""
    if not os.path.exists(DELETED_FILE):
        return []
    
    try:
        with open(DELETED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def clear_deleted_records() -> bool:
    """Clear the deleted records file."""
    if os.path.exists(DELETED_FILE):
        try:
            os.remove(DELETED_FILE)
            return True
        except Exception:
            return False
    return True
