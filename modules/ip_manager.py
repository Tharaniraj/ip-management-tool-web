from __future__ import annotations
import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from modules.validator import (
    validate_ip, validate_subnet, normalize_subnet, VALID_STATUSES,
    validate_hostname_unique
)
from modules.db_encryption import encrypt_data, decrypt_data

DATA_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "ip_data.enc")
LEGACY_DATA_FILE = os.path.join(DATA_DIR, "ip_data.json")
DATA_LOCK = threading.RLock()


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_records() -> List[Dict]:
    """Load all IP records from the Encrypted JSON data file. Auto-migrates plaintext JSON."""
    with DATA_LOCK:
        _ensure_data_dir()
        
        # Migration logic
        if not os.path.exists(DATA_FILE) and os.path.exists(LEGACY_DATA_FILE):
            try:
                with open(LEGACY_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = data if isinstance(data, list) else []
                save_records(records)
                os.rename(LEGACY_DATA_FILE, LEGACY_DATA_FILE + ".bak")
                return records
            except Exception:
                pass
        
        if not os.path.exists(DATA_FILE):
            return []
            
        try:
            with open(DATA_FILE, "rb") as f:
                encrypted_data = f.read()
            json_str = decrypt_data(encrypted_data)
            data = json.loads(json_str)
            return data if isinstance(data, list) else []
        except Exception:
            return []


def save_records(records: List[Dict]) -> None:
    """Persist all IP records to the Encrypted JSON data file."""
    with DATA_LOCK:
        _ensure_data_dir()
        try:
            json_str = json.dumps(records, indent=2, ensure_ascii=False)
            encrypted_data = encrypt_data(json_str)
            with open(DATA_FILE, "wb") as f:
                f.write(encrypted_data)
        except Exception:
            pass


def _find_duplicate(records: List[Dict], ip: str, exclude_index: int = -1) -> bool:
    """Return True if ip already exists (ignoring exclude_index row)."""
    for i, rec in enumerate(records):
        if i == exclude_index:
            continue
        if rec.get("ip", "").strip() == ip.strip():
            return True
    return False


def validate_entry(
    ip: str,
    subnet: str,
    status: str,
    records: List[Dict],
    exclude_index: int = -1,
    hostname: str = "",
    hostname_required: bool = False,
) -> Tuple[bool, str]:
    """
    Validate an IP + subnet + status triple before insert/update.
    Optionally validate hostname uniqueness.
    Returns (is_valid, error_message).
    """
    if not ip.strip():
        return False, "IP address is required."
    if not validate_ip(ip):
        return False, f"Invalid IP address: '{ip}'. Expected format: 192.168.1.1"
    if not subnet.strip():
        return False, "Subnet is required."
    if not validate_subnet(subnet):
        return False, f"Invalid subnet: '{subnet}'. Use CIDR (e.g. 24) or mask (e.g. 255.255.255.0)"
    if status not in VALID_STATUSES:
        return False, f"Invalid status: '{status}'. Must be one of {VALID_STATUSES}"
    if _find_duplicate(records, ip, exclude_index=exclude_index):
        return False, f"IP address '{ip}' already exists in the database."
    if hostname_required and not hostname.strip():
        return False, "Hostname is required."
    if hostname and not validate_hostname_unique(hostname, records, exclude_index=exclude_index):
        return False, f"Hostname '{hostname}' is already in use."
    return True, ""


def add_record(
    ip: str,
    subnet: str,
    hostname: str = "",
    description: str = "",
    status: str = "Active",
) -> Tuple[List[Dict], str]:
    """
    Add a new record. Returns (updated_records, error_message).
    error_message is empty string on success.
    """
    with DATA_LOCK:
        records = load_records()
        ok, err = validate_entry(
            ip, subnet, status, records,
            hostname=hostname
        )
        if not ok:
            return records, err

        new_record = {
            "ip":          ip.strip(),
            "subnet":      normalize_subnet(subnet),
            "hostname":    hostname.strip(),
            "description": description.strip(),
            "status":      status,
            "added_on":    datetime.now().strftime("%Y-%m-%d"),
        }
        updated = records + [new_record]
        save_records(updated)
        return updated, ""


def update_record(
    index: int,
    ip: str,
    subnet: str,
    hostname: str = "",
    description: str = "",
    status: str = "Active",
) -> Tuple[List[Dict], str]:
    """
    Update record at index. Returns (updated_records, error_message).
    """
    with DATA_LOCK:
        records = load_records()
        if index < 0 or index >= len(records):
            return records, "Record index out of range."

        ok, err = validate_entry(
            ip, subnet, status, records,
            exclude_index=index,
            hostname=hostname
        )
        if not ok:
            return records, err

        updated = records.copy()
        updated[index] = {
            "ip":          ip.strip(),
            "subnet":      normalize_subnet(subnet),
            "hostname":    hostname.strip(),
            "description": description.strip(),
            "status":      status,
            "added_on":    records[index].get("added_on", datetime.now().strftime("%Y-%m-%d")),
        }
        save_records(updated)
        return updated, ""


def delete_record(
    index: int,
) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Delete record at index.
    Returns (updated_records, deleted_record). deleted_record is None on failure.
    """
    with DATA_LOCK:
        records = load_records()
        if index < 0 or index >= len(records):
            return records, None
        deleted = records[index]
        updated = records[:index] + records[index + 1:]
        save_records(updated)
        return updated, deleted


def get_summary(records: List[Dict]) -> Dict:
    """Return a summary dict for the status bar."""
    total    = len(records)
    active   = sum(1 for r in records if r.get("status") == "Active")
    inactive = sum(1 for r in records if r.get("status") == "Inactive")
    reserved = sum(1 for r in records if r.get("status") == "Reserved")
    return {
        "total":    total,
        "active":   active,
        "inactive": inactive,
        "reserved": reserved,
    }

def search_records(
    records: list[dict],
    query: str,
    fields: list[str] | None = None,
) -> list[dict]:
    """
    Return records where any of the given fields contain the query string.
    Case-insensitive. If fields is None, all fields are searched.
    Each returned dict is augmented with '_index' = original list position.
    """
    if fields is None:
        fields = ["ip", "subnet", "hostname", "description", "status", "added_on"]

    query = query.strip().lower()
    results = []

    for i, rec in enumerate(records):
        if not query:
            results.append({**rec, "_index": i})
            continue
        for field in fields:
            if query in str(rec.get(field, "")).lower():
                results.append({**rec, "_index": i})
                break

    return results

def filter_by_status(records: list[dict], status: str) -> list[dict]:
    """Filter records by exact status match."""
    return [r for r in records if r.get("status", "").lower() == status.lower()]

def sort_records(
    records: list[dict],
    key: str = "ip",
    reverse: bool = False,
) -> list[dict]:
    """Sort records by field. IP addresses sorted numerically."""
    if key == "ip":
        from modules.validator import ip_to_int
        def sort_key(r):
            try:
                return ip_to_int(r.get("ip", "0.0.0.0"))
            except Exception:
                return 0
    else:
        def sort_key(r):
            return str(r.get(key, "")).lower()

    return sorted(records, key=sort_key, reverse=reverse)
