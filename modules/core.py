"""Core application initialization and utilities."""

from modules.ip_manager import load_records, get_summary
from modules.validator import VALID_STATUSES


def start_app() -> dict:
    """
    Initialize the application and load initial data.
    Returns a status dictionary with initial app state.
    """
    records = load_records()
    summary = get_summary(records)
    return {
        "initialized": True,
        "records_loaded": len(records),
        "summary": summary,
        "valid_statuses": VALID_STATUSES,
    }