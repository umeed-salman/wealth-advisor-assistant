from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    handler.setFormatter(formatter)
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)
