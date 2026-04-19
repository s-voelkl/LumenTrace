from logging.logger import Logger


class DummyPyLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class DummyMqttLogger:
    def __init__(self):
        self.messages = []
        self.stopped = False

    def log(self, message, qos=1):
        self.messages.append(("log", message, qos))

    def log_json(self, data, qos=1):
        self.messages.append(("log_json", data, qos))

    def stop(self):
        self.stopped = True


def test_logger_logs_to_both_backends(monkeypatch):
    dummy_pylogger = DummyPyLogger()
    dummy_mqtt_logger = DummyMqttLogger()

    monkeypatch.setattr("src.logging.logger.get_pylogger", lambda name="pylogger_example": dummy_pylogger)
    monkeypatch.setattr("src.logging.logger.get_mqtt_logger", lambda credentials_path=None: dummy_mqtt_logger)

    logger = Logger()

    logger.log("hello", qos=2)
    logger.log_json({"value": 1}, qos=0)

    assert dummy_pylogger.messages == ["hello", '{"value": 1}']
    assert dummy_mqtt_logger.messages == [
        ("log", "hello", 2),
        ("log_json", {"value": 1}, 0),
    ]