"""Combined logger that writes to stdout/file and MQTT."""

import json
from typing import Any

from .mqtt_logger import get_mqtt_logger
from .pylogger import get_pylogger


class MultiLogger:
    """Forward log calls to the stdlib logger and MQTT logger."""

    # flag for deactivating the logger for better performance in time-critical code paths
    __logger_active = False

    def __init__(
        self, credentials_path: str | None = None, logger_name: str = "pylogger"
    ):
        if self.__logger_active:
            self._pylogger = get_pylogger(logger_name)
            self._mqtt_logger = get_mqtt_logger(credentials_path)

    def log(self, message: str, qos: int = 1) -> None:
        """Log a plain text message to both backends."""
        if self.__logger_active:
            self._pylogger.info(message)
            self._mqtt_logger.log(message, qos)

    def log_json(self, data: dict[str, Any], qos: int = 1) -> None:
        """Log a JSON payload to both backends."""
        if self.__logger_active:
            payload = json.dumps(data)
            self._pylogger.info(payload)
            self._mqtt_logger.log_json(data, qos)

    def stop(self) -> None:
        """Stop the MQTT backend."""
        if self.__logger_active:
            self._mqtt_logger.stop()


_logger: MultiLogger | None = None


def get_logger(
    credentials_path: str | None = None, logger_name: str = "pylogger"
) -> MultiLogger:
    """Get or create the shared combined logger instance."""
    global _logger  # pylint: disable=global-statement
    if _logger is None:
        _logger = MultiLogger(credentials_path, logger_name)
    return _logger


if __name__ == "__main__":
    # Example usage
    logger = get_logger()
    logger.log("This is a test log message.")
    logger.log_json({"event": "test", "value": 42})
    logger.stop()
