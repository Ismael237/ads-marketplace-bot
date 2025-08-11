"""
Configure the logging system for the marketplace bot
"""
import sys
from loguru import logger as loguru_logger
from pathlib import Path
import config


def setup_logging():
    """Setup the logging system with loguru"""
    
    # Create the logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Remove the default loguru configuration
    loguru_logger.remove()
    
    # Get the log level from config.py
    log_level = config.LOG_LEVEL
    log_file = config.LOG_FILE
    
    # Custom log format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Logger for the console (stdout)
    loguru_logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Logger for the file
    loguru_logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="10 MB",  # Rotate at 10MB
        retention="30 days",  # Keep 30 days of history
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True
    )
    
    # Logger for critical errors
    loguru_logger.add(
        config.ERROR_LOG_FILE,
        format=log_format,
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    loguru_logger.info("Logging system initialized")
    return loguru_logger


def get_logger(name: str = None):
    """Return a logger instance with a specific name"""
    if name:
        return loguru_logger.bind(name=name)
    return loguru_logger

logger = setup_logging()