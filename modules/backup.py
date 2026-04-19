"""Data backup and recovery utilities."""

import os
import json
import shutil
import threading
from datetime import datetime
from pathlib import Path

from modules.db_encryption import encrypt_data, decrypt_data

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "ip_data.enc")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
DELETED_FILE = os.path.join(DATA_DIR, "deleted_records.enc")
LEGACY_DELETED_FILE = os.path.join(DATA_DIR, "deleted_records.json")

BACKUP_LOCK = threading.RLock()


def _ensure_backup_dir() -> None:
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup() -> bool:
    """
    Create a timestamped backup of the current data file.
    Returns True if backup was created successfully, False otherwise.
    """
    with BACKUP_LOCK:
        if not os.path.exists(DATA_FILE):
            return False
        
        _ensure_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"ip_data_backup_{timestamp}.enc")
        
        try:
            shutil.copy2(DATA_FILE, backup_path)
            return True
        except Exception:
            return False


def cleanup_old_backups(keep_count: int = 10) -> None:
    """
    Remove old backup files, keeping only the most recent `keep_count` backups.
    """
    with BACKUP_LOCK:
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
    with BACKUP_LOCK:
        os.makedirs(DATA_DIR, exist_ok=True)
        
        try:
            deleted = []
            if os.path.exists(DELETED_FILE):
                try:
                    with open(DELETED_FILE, "rb") as f:
                        deleted = json.loads(decrypt_data(f.read()))
                except Exception:
                    pass
            
            record_copy = record.copy()
            record_copy["deleted_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deleted.append(record_copy)
            
            json_str = json.dumps(deleted, indent=2, ensure_ascii=False)
            with open(DELETED_FILE, "wb") as f:
                f.write(encrypt_data(json_str))
            
            return True
        except Exception:
            return False


def get_deleted_records() -> list:
    """Load all deleted records from the deleted_records file."""
    with BACKUP_LOCK:
        # Migration logic
        if not os.path.exists(DELETED_FILE) and os.path.exists(LEGACY_DELETED_FILE):
            try:
                with open(LEGACY_DELETED_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                deleted = data if isinstance(data, list) else []
                # Save to encrypted format
                json_str = json.dumps(deleted, indent=2, ensure_ascii=False)
                with open(DELETED_FILE, "wb") as f:
                    f.write(encrypt_data(json_str))
                os.rename(LEGACY_DELETED_FILE, LEGACY_DELETED_FILE + ".bak")
                return deleted
            except Exception:
                pass

        if not os.path.exists(DELETED_FILE):
            return []
        
        try:
            with open(DELETED_FILE, "rb") as f:
                encrypted_data = f.read()
            data = json.loads(decrypt_data(encrypted_data))
            return data if isinstance(data, list) else []
        except Exception:
            return []


def clear_deleted_records() -> bool:
    """Clear the deleted records file."""
    with BACKUP_LOCK:
        if os.path.exists(DELETED_FILE):
            try:
                os.remove(DELETED_FILE)
                return True
            except Exception:
                return False
        return True
