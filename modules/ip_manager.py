from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from modules.validator import (
    validate_ip, validate_subnet, normalize_subnet, VALID_STATUSES,
    validate_hostname_unique
)

DATA_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "ip_data.json")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_records() -> List[Dict]:
    """Load all IP records from the JSON data file."""
    _ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_records(records: List[Dict]) -> None:
    """Persist all IP records to the JSON data file."""
    _ensure_data_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


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
    records: List[Dict],
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
    records: List[Dict],
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
    records: List[Dict],
    index: int,
) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Delete record at index.
    Returns (updated_records, deleted_record). deleted_record is None on failure.
    """
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
