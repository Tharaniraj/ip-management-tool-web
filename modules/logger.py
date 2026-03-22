"""Error logging and debugging utilities."""

import os
import logging

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def _ensure_log_dir() -> None:
    """Ensure log directory exists."""
    os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger() -> logging.Logger:
    """
    Configure and return the application logger.
    Logs are written to both file and console.
    """
    _ensure_log_dir()

    logger = logging.getLogger("IPManagementTool")
    if logger.handlers:          # Already configured — avoid duplicate handlers on re-import
        return logger
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


# Global logger instance
logger = setup_logger()


def log_error(message: str, exception: Exception = None) -> None:
    """Log an error message with optional exception."""
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True)
    else:
        logger.error(message)


def log_info(message: str) -> None:
    """Log an info message."""
    logger.info(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)


def get_log_file_path() -> str:
    """Return the path to the log file."""
    return LOG_FILE


def view_logs() -> str:
    """Return the content of the current log file."""
    if not os.path.exists(LOG_FILE):
        return "No logs available."
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Could not read log file: {str(e)}"
