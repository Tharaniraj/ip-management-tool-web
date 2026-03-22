"""Bulk import/export utilities for IP records."""

import csv
import json
import os
from typing import List, Dict, Tuple
from datetime import datetime

from modules.validator import validate_ip, validate_subnet, normalize_subnet


def import_csv(file_path: str) -> Tuple[List[Dict], List[str]]:
    """
    Import IP records from a CSV file.
    Expected columns: ip, subnet, hostname, description, status
    Returns (records, error_messages).
    """
    records = []
    errors = []
    
    if not os.path.exists(file_path):
        return records, ["File not found"]
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return records, ["Invalid CSV: no header row"]
            
            for row_num, row in enumerate(reader, start=2):
                ip = row.get("ip", "").strip()
                subnet = row.get("subnet", "").strip()
                hostname = row.get("hostname", "").strip()
                description = row.get("description", "").strip()
                status = row.get("status", "Active").strip()
                
                # Validate
                if not ip:
                    errors.append(f"Row {row_num}: IP address is required")
                    continue
                if not validate_ip(ip):
                    errors.append(f"Row {row_num}: Invalid IP '{ip}'")
                    continue
                if not subnet:
                    errors.append(f"Row {row_num}: Subnet is required")
                    continue
                if not validate_subnet(subnet):
                    errors.append(f"Row {row_num}: Invalid subnet '{subnet}'")
                    continue
                
                # Check for duplicates within import
                if any(r["ip"] == ip for r in records):
                    errors.append(f"Row {row_num}: Duplicate IP '{ip}' in import")
                    continue
                
                records.append({
                    "ip": ip,
                    "subnet": normalize_subnet(subnet),
                    "hostname": hostname,
                    "description": description,
                    "status": status if status in {"Active", "Inactive", "Reserved"} else "Active",
                    "added_on": datetime.now().strftime("%Y-%m-%d"),
                })
    
    except Exception as e:
        return records, [f"CSV import error: {str(e)}"]
    
    return records, errors


def import_json(file_path: str) -> Tuple[List[Dict], List[str]]:
    """
    Import IP records from a JSON file.
    Expected format: array of objects with ip, subnet, hostname, description, status.
    Returns (records, error_messages).
    """
    records = []
    errors = []
    
    if not os.path.exists(file_path):
        return records, ["File not found"]
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            if not isinstance(data, list):
                return records, ["JSON must contain an array of records"]
            
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"Item {idx}: Not a dictionary")
                    continue
                
                ip = item.get("ip", "").strip()
                subnet = item.get("subnet", "").strip()
                hostname = item.get("hostname", "").strip()
                description = item.get("description", "").strip()
                status = item.get("status", "Active").strip()
                
                # Validate
                if not ip:
                    errors.append(f"Item {idx}: IP address is required")
                    continue
                if not validate_ip(ip):
                    errors.append(f"Item {idx}: Invalid IP '{ip}'")
                    continue
                if not subnet:
                    errors.append(f"Item {idx}: Subnet is required")
                    continue
                if not validate_subnet(subnet):
                    errors.append(f"Item {idx}: Invalid subnet '{subnet}'")
                    continue
                
                # Check for duplicates within import
                if any(r["ip"] == ip for r in records):
                    errors.append(f"Item {idx}: Duplicate IP '{ip}' in import")
                    continue
                
                records.append({
                    "ip": ip,
                    "subnet": normalize_subnet(subnet),
                    "hostname": hostname,
                    "description": description,
                    "status": status if status in {"Active", "Inactive", "Reserved"} else "Active",
                    "added_on": datetime.now().strftime("%Y-%m-%d"),
                })
    
    except json.JSONDecodeError as e:
        return records, [f"Invalid JSON: {str(e)}"]
    except Exception as e:
        return records, [f"JSON import error: {str(e)}"]
    
    return records, errors


def detect_import_conflicts(new_records: List[Dict], existing_records: List[Dict]) -> List[str]:
    """
    Check for IP conflicts between new and existing records.
    Returns list of conflict messages.
    """
    conflicts = []
    existing_ips = {r.get("ip"): r for r in existing_records}
    
    for rec in new_records:
        ip = rec.get("ip")
        if ip in existing_ips:
            conflicts.append(f"IP '{ip}' already exists in database")
    
    return conflicts
