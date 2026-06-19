"""Helpers for the configured Python logger."""

import logging
import logging.config
from pathlib import Path


_CONFIGURED = False


def _configure_pylogger() -> None:
	"""Load the logging configuration once."""
	global _CONFIGURED
	if _CONFIGURED:
		return

	try:
		log_dir = Path().resolve() / "logs"
		log_dir.mkdir(exist_ok=True)

		config_path = Path(__file__).resolve().with_name("pylogger_config.ini")
		logging.config.fileConfig(config_path, disable_existing_loggers=False)
	except Exception as e:
		print(f"Error configuring the logger: {e}")
		print("The file \"logs/app.log\" must exist and be writable for the logger to work.")
		raise e
	_CONFIGURED = True


def get_pylogger(name: str = "pylogger") -> logging.Logger:
	"""Return a configured stdlib logger."""
	_configure_pylogger()
	return logging.getLogger(name)


pylogger = get_pylogger()