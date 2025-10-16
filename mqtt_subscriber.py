#!/usr/bin/env python3
"""
MQTT Topic Subscriber - Debug Tool
Subscribe to all MQTT topics and display messages in real-time
Usage: python mqtt_subscriber.py
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

# MQTT Configuration
MQTT_HOST = "localhost"
MQTT_PORT = 1883

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("=" * 80)
        print(f"✅ Connected to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}")
        print("=" * 80)
        
        # Subscribe to ALL topics using wildcard
        client.subscribe("#")
        print("📡 Subscribed to ALL topics (#)")
        print("=" * 80)
        print("\n🔍 Listening for messages... (Press Ctrl+C to stop)\n")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, message):
    """Callback when a message is received"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    topic = message.topic
    
    try:
        # Try to parse as JSON
        payload = json.loads(message.payload.decode())
        payload_str = json.dumps(payload, indent=2)
    except:
        # If not JSON, display as raw string
        payload_str = message.payload.decode()
    
    # Color-coded output based on topic
    if "sensors" in topic:
        emoji = "🌡️"
        color = "\033[94m"  # Blue
    elif "plant" in topic:
        emoji = "🌱"
        color = "\033[92m"  # Green
    elif "actuators" in topic:
        emoji = "💧"
        color = "\033[93m"  # Yellow
    else:
        emoji = "📨"
        color = "\033[95m"  # Magenta
    
    reset = "\033[0m"
    
    print(f"{color}[{timestamp}] {emoji} {topic}{reset}")
    print(f"  └─ {payload_str}")
    print()

def on_disconnect(client, userdata, rc, properties=None):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        print(f"\n⚠️ Unexpected disconnection. Return code: {rc}")
        print("Attempting to reconnect...")

def main():
    """Main function to run the subscriber"""
    print("\n" + "=" * 80)
    print("🚀 MQTT TOPIC SUBSCRIBER - GROW A PLANT")
    print("=" * 80)
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="debug_subscriber")
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        print(f"🔌 Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        # Start the loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("⛔ Subscriber stopped by user")
        print("=" * 80)
        client.disconnect()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. MQTT broker is running (start from GUI)")
        print("  2. Host and port are correct")

if __name__ == "__main__":
    main()
