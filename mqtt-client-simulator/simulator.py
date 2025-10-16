"""
Modbus Client Simulator for IoT Plant Monitoring System
This simulator publishes sensor data (soil moisture, temperature) via MQTT
and listens for faucet control commands.
"""
import paho.mqtt.client as mqtt
import json
import time
import random
import signal
import sys

# MQTT settings
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# Global state for the plant simulation
plant_state = {
    'last_watered': time.time(),
    'moisture_level': 70.0,  # Initial moisture level
    'base_temperature': 22.0,  # Base temperature in Celsius
    'faucet_on': False,  # Faucet status
    'liters_per_second': 0.5  # Realistic water flow rate
}

# Global flag for clean shutdown
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C for graceful shutdown"""
    global running
    print("\n[SIMULATOR] Shutting down gracefully...")
    running = False


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("[SIMULATOR] Connected to MQTT broker successfully")
        # Subscribe to faucet commands
        client.subscribe("faucet/command")
        print("[SIMULATOR] Subscribed to faucet/command")
    else:
        print(f"[SIMULATOR] Connection failed with code {rc}")


def on_message(client, userdata, message):
    """Handle incoming MQTT messages (faucet commands)"""
    try:
        print(f"[SIMULATOR] Received MQTT message on topic: {message.topic}, payload: {message.payload}")
        if message.topic == "faucet/command":
            payload_str = message.payload.decode()

            # Handle multiple formats: JSON dict {"command": 1}, JSON int "1", or plain string "1"
            try:
                data = json.loads(payload_str)
                # Check if it's a dict with "command" key or just an integer
                if isinstance(data, dict):
                    command = int(data.get("command", 0))
                else:
                    # It's a JSON-encoded integer like "1"
                    command = int(data)
            except (json.JSONDecodeError, ValueError):
                # Fall back to plain string format
                command = int(payload_str)

            plant_state['faucet_on'] = (command == 1)
            status = "ON" if command == 1 else "OFF"
            print(f"[SIMULATOR] Faucet command received: {command} -> Faucet turned {status}")
    except Exception as e:
        print(f"[SIMULATOR] Error processing faucet command: {e}")
        import traceback
        traceback.print_exc()


def on_publish(client, userdata, mid, reason_code=None, properties=None):
    """Callback when message is published"""
    print(f"[SIMULATOR] Message {mid} delivered")


def run_simulation():
    """Main simulation loop"""
    global running

    # Set up MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish

    try:
        print(f"[SIMULATOR] Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()

        # Wait for connection to establish
        time.sleep(1)

        iteration = 0
        while running:
            try:
                iteration += 1
                print(f"\n[SIMULATOR] === Iteration {iteration} ===")

                # Check if faucet is on for watering
                faucet_on = plant_state['faucet_on']
                liters_per_sec = plant_state['liters_per_second']

                if faucet_on:
                    # WATERING MODE: Moisture increases based on flow rate
                    # 0.5 liters/sec = ~5% moisture increase per 2 seconds
                    moisture_increase_per_cycle = (liters_per_sec * 2) * 5  # 5% per 0.5L * 2sec
                    new_moisture = min(100, plant_state['moisture_level'] + moisture_increase_per_cycle)
                    plant_state['moisture_level'] = new_moisture
                    current_moisture = round(new_moisture, 1)

                    # Reset the watering timestamp - we're actively watering now
                    plant_state['last_watered'] = time.time()

                    print(f"[SIMULATOR] FAUCET ON - Adding water: +{moisture_increase_per_cycle:.1f}% | Current: {current_moisture}% | Flow: {liters_per_sec}L/s")
                else:
                    # NORMAL MODE: Moisture decreases (evaporation + plant consumption)
                    time_since_watering = time.time() - plant_state['last_watered']
                    hours_since_watering = time_since_watering / 3600

                    # Fast moisture decrease for demo: ~30-40% per hour depending on temperature
                    temp = plant_state['base_temperature']
                    temp_factor = 1.0 + (temp - 22) * 0.05  # Hotter = faster evaporation
                    moisture_loss_per_hour = 35.0 * temp_factor

                    # Calculate current moisture (minimum 10%)
                    moisture = max(10, plant_state['moisture_level'] - (moisture_loss_per_hour * hours_since_watering))

                    # Update the plant state with current moisture
                    plant_state['moisture_level'] = moisture
                    current_moisture = round(moisture, 1)

                    print(f"[SIMULATOR] Faucet OFF - Moisture decreasing: {current_moisture}% | Hours since watering: {hours_since_watering:.2f}h")

                # Temperature varies slightly throughout the day (±3°C)
                temperature = plant_state['base_temperature'] + random.uniform(-2, 3)

                # Publish sensor data to MQTT
                moisture_payload = json.dumps({"value": current_moisture})
                temp_payload = json.dumps({"value": round(temperature, 1)})

                result1 = client.publish("sensors/soil_moisture", moisture_payload)
                result2 = client.publish("sensors/temperature", temp_payload)

                print(f"[SIMULATOR] Publishing to MQTT:")
                print(f"  - sensors/soil_moisture = {current_moisture}% (msg_id: {result1.mid})")
                print(f"  - sensors/temperature = {round(temperature, 1)}°C (msg_id: {result2.mid})")

                # Sleep for 2 seconds before next iteration
                time.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[SIMULATOR] Simulation loop error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

    except Exception as e:
        print(f"[SIMULATOR] Connection error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[SIMULATOR] Stopping simulation...")
        client.loop_stop()
        client.disconnect()
        print("[SIMULATOR] Disconnected from MQTT broker")


if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("MODBUS CLIENT SIMULATOR")
    print("=" * 60)
    print("This simulator publishes plant sensor data via MQTT")
    print("Topics:")
    print("  - Publishes: sensors/soil_moisture, sensors/temperature")
    print("  - Subscribes: faucet/command")
    print("=" * 60)
    print()

    run_simulation()

    print("[SIMULATOR] Shutdown complete")
