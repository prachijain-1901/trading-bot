"""
logging_config.py — Configures structured logging to both console and file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up root logger with:
      - StreamHandler  → console (INFO and above)
      - RotatingFileHandler → logs/trading_bot.log (DEBUG and above)
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)          # capture everything; handlers filter

    if logger.handlers:                     # avoid duplicate handlers on re-import
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ──────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(fmt)

    # ── File handler (rotating, max 5 MB × 3 backups) ────────────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)    # always verbose in file
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
