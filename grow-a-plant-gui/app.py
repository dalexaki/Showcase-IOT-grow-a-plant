"""
Plant Monitor GUI Application
Main Flask application that orchestrates the IoT plant monitoring system
"""
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from threading import Thread

# Import custom modules
from mqtt_handler import MQTTHandler
from broker_manager import BrokerManager
from simulator_manager import SimulatorManager
from controller_manager import ControllerManager
from config_manager import ConfigManager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'plant-monitor-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
app_state = {
    'mqtt_broker_running': False,
    'simulation_running': False,
    'controller_running': False,
    'broker_process': None,
    'simulation_process': None,
    'controller_process': None,
    'metrics': {
        'soil_moisture': None,
        'temperature': None,
        'watering_hours': 0,
        'currently_watering': 0,
        'plant_health': 0,
        'faucet_status': 0
    }
}

# MQTT settings
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# Initialize managers
broker_manager = BrokerManager(app_state, socketio)
simulator_manager = SimulatorManager(app_state, socketio)
controller_manager = ControllerManager(app_state, socketio)
config_manager = ConfigManager()
mqtt_handler = MQTTHandler(MQTT_HOST, MQTT_PORT, app_state, socketio)


# ============================================================================
# ROUTES - Web Pages
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current system status"""
    return jsonify({
        'mqtt_broker_running': app_state['mqtt_broker_running'],
        'simulation_running': app_state['simulation_running'],
        'controller_running': app_state['controller_running'],
        'metrics': app_state['metrics']
    })


# ============================================================================
# ROUTES - MQTT Broker Management
# ============================================================================

@app.route('/api/start_broker', methods=['POST'])
def start_broker():
    """Start MQTT broker (Docker or native Mosquitto)"""
    result = broker_manager.start()
    return jsonify(result)


@app.route('/api/stop_broker', methods=['POST'])
def stop_broker():
    """Stop MQTT broker"""
    result = broker_manager.stop()
    return jsonify(result)


# ============================================================================
# ROUTES - Simulator Management
# ============================================================================

@app.route('/api/start_simulation', methods=['POST'])
def start_simulation():
    """Start the external simulator process"""
    result = simulator_manager.start()
    return jsonify(result)


@app.route('/api/stop_simulation', methods=['POST'])
def stop_simulation():
    """Stop the simulator process"""
    result = simulator_manager.stop()
    return jsonify(result)


# ============================================================================
# ROUTES - Controller Management
# ============================================================================

@app.route('/api/start_controller', methods=['POST'])
def start_controller():
    """Start the plant controller process"""
    result = controller_manager.start()
    return jsonify(result)


@app.route('/api/stop_controller', methods=['POST'])
def stop_controller():
    """Stop the controller process"""
    result = controller_manager.stop()
    return jsonify(result)


# ============================================================================
# ROUTES - Configuration Management
# ============================================================================

@app.route('/api/get_config', methods=['GET'])
def get_config():
    """Get controller configuration"""
    result = config_manager.get_config()
    return jsonify(result)


@app.route('/api/update_config', methods=['POST'])
def update_config():
    """Update controller configuration"""
    data = request.json
    result = config_manager.update_config(data)
    return jsonify(result)


# ============================================================================
# ROUTES - Manual Watering Control
# ============================================================================

@app.route('/api/water_plant', methods=['POST'])
def water_plant():
    """Turn on faucet to water the plant"""
    if not app_state['mqtt_broker_running']:
        return jsonify({'success': False, 'message': 'MQTT broker must be running'})

    if not app_state['simulation_running']:
        return jsonify({'success': False, 'message': 'Simulation must be running'})

    success = mqtt_handler.publish_faucet_command(1)
    if success:
        print("[WATER] Manual watering started - Faucet ON")
        return jsonify({'success': True, 'message': 'Faucet turned ON - Water is flowing!'})
    else:
        return jsonify({'success': False, 'message': 'Error controlling faucet'})


@app.route('/api/stop_faucet', methods=['POST'])
def stop_faucet():
    """Turn off faucet to stop watering"""
    if not app_state['mqtt_broker_running']:
        return jsonify({'success': False, 'message': 'MQTT broker must be running'})

    if not app_state['simulation_running']:
        return jsonify({'success': False, 'message': 'Simulation must be running'})

    success = mqtt_handler.publish_faucet_command(0)
    if success:
        print("[WATER] Manual watering stopped - Faucet OFF")
        return jsonify({'success': True, 'message': 'Faucet turned OFF - Watering stopped!'})
    else:
        return jsonify({'success': False, 'message': 'Error controlling faucet'})


# ============================================================================
# STARTUP INITIALIZATION
# ============================================================================

# Check if broker is already running on startup
broker_manager.check_status()

# Start MQTT listener in background thread
listener_thread = Thread(target=mqtt_handler.start_listener)
listener_thread.daemon = True
listener_thread.start()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
