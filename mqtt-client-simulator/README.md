# Modbus Client Simulator

This is a standalone MQTT-based simulator that mimics IoT plant sensors and actuators.

## Features

- **Publishes sensor data** to MQTT topics:
  - `sensors/soil_moisture` - Current soil moisture percentage (10-100%)
  - `sensors/temperature` - Current temperature in Celsius

- **Subscribes to actuator commands**:
  - `faucet/command` - Controls the water faucet (0=OFF, 1=ON)

## Plant Simulation Behavior

- **Moisture decreases over time** (~30-40% per hour) simulating evaporation and plant consumption
- **Temperature varies** around a base of 22°C (±3°C fluctuation)
- **When faucet is ON**, moisture increases based on water flow rate (0.5L/s)
- Updates published every 2 seconds for responsive demo

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the simulator:
```bash
python simulator.py
```

The simulator will:
1. Connect to MQTT broker at `localhost:1883`
2. Subscribe to `faucet/command` topic
3. Begin publishing sensor data every 2 seconds
4. Respond to faucet control commands in real-time

Press `Ctrl+C` to stop the simulator gracefully.

## Configuration

Edit `simulator.py` to customize:
- `MQTT_HOST` and `MQTT_PORT` - MQTT broker connection
- `moisture_level` - Initial moisture percentage
- `base_temperature` - Base temperature in Celsius
- `liters_per_second` - Water flow rate when faucet is on

## Requirements

- Python 3.7+
- MQTT broker running (e.g., Mosquitto, Docker container)
- paho-mqtt library
