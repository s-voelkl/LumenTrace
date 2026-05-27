"""MQTT Logger module for publishing and subscribing to MQTT topics."""

import json
import threading
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as paho
from paho import mqtt


class MQTTLogger:
    """MQTT Logger class for publishing and subscribing to MQTT topics."""

    def __init__(self, credentials_path: str | None = None):
        """Initialize the MQTT logger with credentials from the specified file."""
        credentials_file = Path(credentials_path) if credentials_path else Path(__file__).with_name("credentials.json")

        # Read credentials.json for MQTT credentials
        with open(credentials_file, "r", encoding="utf-8") as f:
            credentials = json.load(f)

        self._connected = threading.Event()
        self._topic = credentials["hivemq"]["topic"]
        self._active = True

        # Using MQTT version 5 here, for 3.1.1: MQTTv311, 3.1: MQTTv31
        self._client = paho.Client(client_id=f"lumentrace-{uuid4().hex[:8]}", userdata=None, protocol=paho.MQTTv5)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe
        self._client.on_message = self._on_message

        # Enable TLS for secure connection
        self._client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)  # type: ignore

        # Set username and password
        username = credentials["hivemq"]["username"]
        password = credentials["hivemq"]["password"]
        self._client.username_pw_set(username, password)

        # Connect to HiveMQ Cloud on port 8883 (default for MQTT)
        cluster_url = credentials["hivemq"]["clusterurl"]
        port = credentials["hivemq"].get("port", 8883)
        try:
            self._client.connect(cluster_url, port)
        except Exception as e:
            self._active = False
            print(f"MQTT-Logger: Failed to connect to MQTT broker: {e}")

        # Start the MQTT loop
        self._client.loop_start()
        print("MQTT-Logger: initialized.")

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties=None):
        """Prints the result of the connection with a reasoncode."""
        print(f"MQTT-Logger: CONNACK received with code {reason_code}.")
        is_success = str(reason_code) == "Success"
        if not is_success and hasattr(reason_code, "value"):
            is_success = reason_code.value == 0
        if is_success:
            self._connected.set()
            client.subscribe(self._topic, qos=1)

    def _on_disconnect(self, _client, _userdata, reason_code, _properties=None):
        """Clear connection state after a disconnect."""
        print(f"MQTT-Logger: Disconnected with reason code {reason_code}.")
        self._connected.clear()

    def _on_publish(self, _client, _userdata, mid, _properties=None):
        """Prints mid to stdout to reassure a successful publish."""
        # print(f"MQTT-Logger: Published: {mid}")

    def _on_subscribe(self, _client, _userdata, mid, granted_qos, _properties=None):
        """Prints a reassurance for successfully subscribing."""
        # print(f"MQTT-Logger: Subscribed: {mid} {granted_qos}")

    def _on_message(self, _client, _userdata, msg):
        """Prints a mqtt message to stdout."""
        # print(f"MQTT-Logger: Received: {msg.topic} {msg.qos} {msg.payload}")

    def _publish(self, payload: str, qos: int) -> None:
        """Publish only after a confirmed MQTT connection."""
        if not self._active:
            print("MQTT-Logger: Skipping publish due to missing broker connection.")
            return
        if not self._connected.wait(timeout=3):
            print("MQTT-Logger: publish skipped: no broker connection available.")
            return

        result = self._client.publish(self._topic, payload=payload, qos=qos)
        result.wait_for_publish(timeout=5)
        if result.rc != paho.MQTT_ERR_SUCCESS:
            print(f"MQTT-Logger: publish failed with rc={result.rc}.")

    def log(self, message: str, qos: int = 1) -> None:
        """Publish a message to the configured MQTT topic."""
        if not self._active:
            print("MQTT-Logger: Skipping log:", message)
            return
        # print("MQTT-Logger: Log:", message)
        self._publish(message, qos)

    def log_json(self, data: dict, qos: int = 1) -> None:
        """Publish a dictionary as JSON to the configured MQTT topic."""
        if not self._active:
            print("MQTT-Logger: Skipping JSON log:", data)
            return
        # print("MQTT-Logger: Log JSON:", data)
        self._publish(json.dumps(data), qos)

    def stop(self) -> None:
        """Stop the MQTT loop."""
        print("MQTT-Logger: Stopping MQTT Logger.")
        self._client.loop_stop()
        self._client.disconnect()


# Singleton instance for easy access
_mqtt_logger: MQTTLogger | None = None


def get_mqtt_logger(credentials_path: str | None = None) -> MQTTLogger:
    """Get or create the singleton MQTT logger instance."""
    global _mqtt_logger # pylint: disable=global-statement
    if _mqtt_logger is None:
        _mqtt_logger = MQTTLogger(credentials_path)
    return _mqtt_logger

