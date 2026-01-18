"""
Logger Configuration Module

Sets up structured logging for the Telegram bot.
"""

import sys
from pathlib import Path

# Ensure src is in path for imports
_src_path = Path(__file__).parent
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path.parent))

from loguru import logger

from config import get_config


def setup_logging():
    """Configure loguru logger with file and console output"""
    config = get_config()
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = Path(config.logging.dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Console output with colors
    logger.add(
        sys.stdout,
        format=config.logging.format,
        level=config.logging.level,
        colorize=True,
    )
    
    # Rotating file log
    log_file = log_dir / "bot_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level}: {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="gz",
        encoding="utf-8",
    )
    
    # Error-only log file
    error_log_file = log_dir / "errors_{time:YYYY-MM-DD}.log"
    logger.add(
        str(error_log_file),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level}: {message}",
        level="ERROR",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )
    
    logger.info("Logging configured successfully")


def get_logger():
    """Get the configured logger instance"""
    return logger
