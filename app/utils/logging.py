import hashlib
import logging
import os
import structlog


def mask_sensitive_field(value: str) -> str:
    """Return a one-way hash reference for a sensitive value.

    The original value is never stored or logged. Use this to produce
    a stable, correlation-safe identifier for log events.
    """
    digest = hashlib.sha256(value.encode()).hexdigest()[:8]
    return f"[ENTITY:{digest}]"


def get_logger(name: str) -> structlog.BoundLogger:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)
