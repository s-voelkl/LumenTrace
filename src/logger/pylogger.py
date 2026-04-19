"""Helpers for the configured Python logger."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path


_CONFIGURED = False


def _configure_pylogger() -> None:
	"""Load the logging configuration once."""
	global _CONFIGURED
	if _CONFIGURED:
		return

	config_path = Path(__file__).resolve().with_name("pylogger_config.ini")
	logging.config.fileConfig(config_path, disable_existing_loggers=False)
	_CONFIGURED = True


def get_pylogger(name: str = "pylogger_example") -> logging.Logger:
	"""Return a configured stdlib logger."""
	_configure_pylogger()
	return logging.getLogger(name)


pylogger = get_pylogger()