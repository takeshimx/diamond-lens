"""
Structured logging utility for Google Cloud Logging
Outputs JSON-formatted logs that are automatically parsed by Cloud Logging
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from backend.app.middleware.request_id import get_request_id


class StructuredLogger:
    """
    Structured logger that outputs JSON logs compatible with Google Cloud Logging

    Severity levels map to Cloud Logging severity:
    - DEBUG, INFO, WARNING, ERROR, CRITICAL
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove existing handlers
        self.logger.handlers = []

        # Add JSON formatter handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(handler)

    def _get_json_formatter(self) -> logging.Formatter:
        """Create a formatter that outputs JSON"""

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_obj = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "severity": record.levelname,
                    "message": record.getMessage(),
                    "logger": record.name,
                    "request_id": get_request_id(),
                }

                # Add extra fields if present
                if hasattr(record, "extra_fields"):
                    log_obj.update(record.extra_fields)

                # Add exception info if present
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_obj, ensure_ascii=False)

        return JsonFormatter()

    def _log(self, level: int, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Internal log method with extra fields support"""
        extra = {"extra_fields": extra_fields} if extra_fields else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, kwargs if kwargs else None)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, kwargs if kwargs else None)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, kwargs if kwargs else None)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, kwargs if kwargs else None)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, kwargs if kwargs else None)


# Singleton instance
_logger_instance: Optional[StructuredLogger] = None


def get_logger(name: str = "diamond-lens") -> StructuredLogger:
    """Get or create structured logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(name)
    return _logger_instance
