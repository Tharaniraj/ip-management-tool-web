from __future__ import annotations
from typing import List, Dict


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
