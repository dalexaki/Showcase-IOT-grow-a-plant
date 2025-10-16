import json
from typing import Any, Callable
import paho.mqtt.client as mqtt
from threading import Thread
import time

from src.core.system_logger import SystemLogger

class IoTMessageBroker:
    """IoT message broker for MQTT publish/subscribe communication using paho-mqtt."""

    def __init__(self, host="127.0.0.1", port=1883, debug_level="INFO"):
        """Initialize MQTT broker connection."""
        self.host = host
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.callbacks = {}
        self.connected = False
        self.loop = None  # Store the event loop

        self.logger = SystemLogger(
            name=__name__,
            log_file=None,
            log_level="INFO",
            console_level=debug_level,
        ).get_logger()
        
        # Set up MQTT callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker."""
        self.connected = True
        self.logger.info(f"[MQTT] Connected to {self.host}:{self.port}")
        
        # Resubscribe to all topics
        for topic in self.callbacks.keys():
            client.subscribe(topic)
            self.logger.info(f"[MQTT SUBSCRIBE] Subscribed to {topic}")

    def _on_message(self, client, userdata, message):
        """Callback when message received."""
        topic = message.topic
        
        if topic in self.callbacks:
            try:
                payload = json.loads(message.payload.decode())
                self.logger.debug(f"[MQTT INCOMING] Topic: {topic}, Payload: {payload}")
                
                # Call the registered callback - schedule it in the event loop
                callback = self.callbacks[topic]
                if self.loop:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(callback(payload), self.loop)
            except json.JSONDecodeError:
                self.logger.error(f"[MQTT] Non-JSON payload on {topic}: {message.payload}")
            except Exception as e:
                self.logger.error(f"[MQTT] Error processing message: {e}")

    async def publish(self, topic: str, message: dict, qos: int = 0, retain: bool = False) -> None:
        """Publish JSON message to MQTT topic."""
        try:
            payload = json.dumps(message)
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"[MQTT PUBLISH] Sent to {topic}: {payload}")
            else:
                self.logger.error(f"[MQTT] Publish failed with code {result.rc}")
        except Exception as e:
            self.logger.error(f"[MQTT] Failed to publish to {topic}: {e}")

    async def subscribe(self, topic: str, callback: Callable, *args: Any, qos: int = 0, ignore_retained: bool = True, **kwargs: Any) -> None:
        """Subscribe to MQTT topic with callback."""
        try:
            self.callbacks[topic] = callback
            if self.connected:
                self.client.subscribe(topic, qos=qos)
                self.logger.info(f"[MQTT SUBSCRIBE] Subscribed to {topic}")
        except Exception as e:
            self.logger.error(f"[MQTT] Failed to subscribe to {topic}: {e}")

    async def connect(self) -> None:
        """Establish MQTT connection."""
        try:
            import asyncio
            # Store the event loop for scheduling callbacks
            self.loop = asyncio.get_event_loop()
            
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            self.logger.info(f"[MQTT] Connecting to {self.host}:{self.port}")
            
            # Wait for connection
            timeout = 5
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                await asyncio.sleep(0.1)
                
            if not self.connected:
                raise Exception("Connection timeout")
        except Exception as e:
            self.logger.error(f"[MQTT] Connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.logger.info("[MQTT] Disconnected")
        except Exception as e:
            self.logger.error(f"[MQTT] Disconnect error: {e}")
