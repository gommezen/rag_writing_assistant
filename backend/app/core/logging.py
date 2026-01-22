"""Audit-friendly logging configuration.

Key principle: Never log raw document content or user data.
Log operational metadata only.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any

from ..config import get_settings


class AuditLogger:
    """Logger that ensures sensitive content is never logged."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure the logger based on settings."""
        settings = get_settings()

        self.logger.setLevel(settings.log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(settings.log_level)

            if settings.log_format == "json":
                handler.setFormatter(JsonFormatter())
            else:
                handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    )
                )

            self.logger.addHandler(handler)

    def _sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove any potentially sensitive fields from log data."""
        sensitive_fields = {
            "content",
            "raw_content",
            "text",
            "excerpt",
            "chunk_content",
            "prompt",
            "response",
        }

        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = f"[REDACTED - {len(str(value))} chars]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                sanitized[key] = [self._sanitize(item) for item in value]
            else:
                sanitized[key] = value

        return sanitized

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info with sanitized data."""
        self.logger.info(message, extra={"data": self._sanitize(kwargs)})

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning with sanitized data."""
        self.logger.warning(message, extra={"data": self._sanitize(kwargs)})

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error with sanitized data."""
        self.logger.error(message, extra={"data": self._sanitize(kwargs)})

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug with sanitized data."""
        self.logger.debug(message, extra={"data": self._sanitize(kwargs)})

    def audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log an auditable action without sensitive content."""
        audit_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": datetime.utcnow().isoformat(),
            **self._sanitize(kwargs),
        }
        self.logger.info(f"AUDIT: {action} on {resource_type}", extra={"audit": audit_data})


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "data"):
            log_data["data"] = record.data

        if hasattr(record, "audit"):
            log_data["audit"] = record.audit

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str) -> AuditLogger:
    """Get an audit-safe logger instance."""
    return AuditLogger(name)
