"""
Logging configuration for the GitLab Backport Bot Service.
"""

import sys
import logging
from typing import Optional
import structlog

from app.config import get_settings


def setup_logger(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Override log level (uses settings if not provided)
    """
    settings = get_settings()
    level = (log_level or settings.log_level).upper()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("gitlab").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None):
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (uses __name__ if not provided)
        
    Returns:
        structlog BoundLogger instance
    """
    return structlog.get_logger(name or __name__)
