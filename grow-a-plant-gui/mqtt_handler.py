"""
MQTT Handler Module
Handles all MQTT communication including listening to topics and processing messages
"""
import paho.mqtt.client as mqtt
import json
import time


class MQTTHandler:
    def __init__(self, host, port, app_state, socketio):
        self.host = host
        self.port = port
        self.app_state = app_state
        self.socketio = socketio
        self.client = None

    def on_message(self, client, userdata, message):
        """Handle incoming MQTT messages"""
        try:
            payload = json.loads(message.payload.decode())
            topic = message.topic

            # Handle sensor data from simulation
            if "sensors/soil_moisture" in topic:
                self.app_state['metrics']['soil_moisture'] = payload.get('value', 0)
                print(f"[MQTT] Received soil moisture: {payload.get('value')}%")
            elif "sensors/temperature" in topic:
                self.app_state['metrics']['temperature'] = payload.get('value', 0)
                print(f"[MQTT] Received temperature: {payload.get('value')}°C")
            elif "faucet/command" in topic:
                # Track faucet status - handle both formats
                if isinstance(payload, dict):
                    # Controller format: {"command": 1}
                    faucet_cmd = int(payload.get('command', 0))
                elif isinstance(payload, (int, str)):
                    # GUI format: "1" or 1
                    faucet_cmd = int(payload)
                else:
                    faucet_cmd = 0

                self.app_state['metrics']['faucet_status'] = faucet_cmd
                status = "ON" if faucet_cmd == 1 else "OFF"
                print(f"[MQTT] Faucet command: {status}")
            elif "watering_hours" in topic:
                self.app_state['metrics']['watering_hours'] = payload.get('value', 0)
            elif "currently_watering" in topic:
                self.app_state['metrics']['currently_watering'] = payload.get('value', 0)
            elif "health" in topic:
                self.app_state['metrics']['plant_health'] = payload.get('value', 0)

            self.socketio.emit('metrics_update', self.app_state['metrics'])
        except Exception as e:
            print(f"Message processing error: {e}")

    def on_disconnect(self, client, userdata, rc, properties=None):
        """Handle MQTT disconnection"""
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection (code: {rc}). Will attempt to reconnect...")

    def start_listener(self):
        """Start MQTT listener in background thread"""
        while True:
            try:
                print("[MQTT] Attempting to connect to broker...")
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                self.client.on_message = self.on_message
                self.client.on_disconnect = self.on_disconnect

                # Try to connect with timeout
                try:
                    self.client.connect(self.host, self.port, 60)
                except (ConnectionRefusedError, OSError) as e:
                    print(f"[MQTT] Broker not available: {e}. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue

                # If connection successful, subscribe
                self.client.subscribe("sensors/#")  # Subscribe to sensor data from simulation
                self.client.subscribe("plant/#")    # Subscribe to plant metrics from controller
                self.client.subscribe("faucet/#")   # Subscribe to faucet commands
                print("[MQTT] Connected and subscribed to topics: sensors/#, plant/#, faucet/#")

                # Run loop - this will block until disconnected
                self.client.loop_forever()

            except KeyboardInterrupt:
                print("[MQTT] Listener interrupted by user")
                break
            except Exception as e:
                print(f"[MQTT] Listener error: {e}")
                time.sleep(5)

    def publish_faucet_command(self, command):
        """Publish a faucet command (0=OFF, 1=ON)"""
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.connect(self.host, self.port, 60)
            # Publish with QoS 1 to ensure delivery
            result = client.publish("faucet/command", str(command), qos=1)
            # Wait for the message to be sent before disconnecting
            result.wait_for_publish(timeout=2.0)
            print(f"[MQTT-HANDLER] Published manual faucet command: {command} (msg_id: {result.mid})")
            client.disconnect()
            return True
        except (ConnectionRefusedError, OSError) as e:
            print(f"[MQTT] Broker not available for faucet command: {e}")
            return False
        except Exception as e:
            print(f"[MQTT] Error publishing faucet command: {e}")
            return False
