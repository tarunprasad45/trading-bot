import logging
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

class StructuredFormatter(logging.Formatter):
    """
    Emits each log record as a single-line JSON object.
    Structured logs make it trivial to grep, filter, and pipe into
    downstream tooling — a basic requirement for any real execution system.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": "trading-bot",
        }

        # If the message is already a dict, merge it in directly
        if isinstance(record.msg, dict):
            payload.update(record.msg)
        else:
            payload["msg"] = record.getMessage()

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that writes structured JSON to both a rotating log file
    and to stderr. File gets everything (DEBUG+); stderr gets INFO+.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — avoid duplicate handlers on re-import
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = StructuredFormatter()

    # --- File handler ---
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    fh = RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # --- Stderr handler (INFO+ only, so CLI output stays clean) ---
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    return logger


