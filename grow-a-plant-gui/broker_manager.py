"""
Broker Manager Module
Handles MQTT broker lifecycle (start/stop) via Docker or native Mosquitto
"""
import subprocess
import os
import signal
import time


class BrokerManager:
    def __init__(self, app_state, socketio):
        self.app_state = app_state
        self.socketio = socketio
        self.broker_process = None

    def start(self):
        """Start MQTT broker (Docker or native Mosquitto)"""
        if self.app_state['mqtt_broker_running']:
            return {'success': False, 'message': 'Broker already running'}

        try:
            # Try Docker first (preferred method - no installation needed)
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return self._start_docker_broker()
        except FileNotFoundError:
            pass  # Docker not found, try native approach
        except Exception as e:
            print(f"[BROKER] Docker error: {e}")

        # Fallback: Try native Mosquitto installation
        return self._start_native_broker()

    def _start_docker_broker(self):
        """Start MQTT broker in Docker container"""
        print("[BROKER] Starting MQTT broker in Docker container...")

        # Check if container already exists and remove it
        subprocess.run(['docker', 'rm', '-f', 'plant-mqtt-broker'], capture_output=True)

        # Start new container with proper configuration and process isolation
        docker_cmd = [
            'docker', 'run', '--name', 'plant-mqtt-broker',
            '-p', '1883:1883',
            '-v', 'mosquitto_data:/mosquitto/data',
            '--rm',
            'eclipse-mosquitto:2.0',
            'sh', '-c',
            'mkdir -p /mosquitto/config && '
            'echo "listener 1883 0.0.0.0" > /mosquitto/config/mosquitto.conf && '
            'echo "allow_anonymous true" >> /mosquitto/config/mosquitto.conf && '
            'mosquitto -c /mosquitto/config/mosquitto.conf -v'
        ]

        # On Windows, create new process group to prevent signal propagation
        if os.name == 'nt':
            self.app_state['broker_process'] = subprocess.Popen(
                docker_cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            self.app_state['broker_process'] = subprocess.Popen(docker_cmd)

        time.sleep(2)  # Wait for container to start
        self.app_state['mqtt_broker_running'] = True
        self.socketio.emit('broker_status', {'running': True})
        return {'success': True, 'message': 'MQTT broker started in Docker container'}

    def _start_native_broker(self):
        """Start native Mosquitto broker"""
        try:
            print("[BROKER] Docker not available, trying native Mosquitto...")
            if os.name == 'nt':  # Windows
                self.app_state['broker_process'] = subprocess.Popen(
                    ['mosquitto', '-v'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:  # Linux/Mac
                self.app_state['broker_process'] = subprocess.Popen(
                    ['mosquitto', '-v'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            time.sleep(1)  # Wait for broker to start
            self.app_state['mqtt_broker_running'] = True
            self.socketio.emit('broker_status', {'running': True})
            return {'success': True, 'message': 'MQTT broker started (native)'}
        except FileNotFoundError:
            return {
                'success': False,
                'message': 'Neither Docker nor Mosquitto found. Please install Docker for automatic setup, or install Mosquitto manually.'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error starting broker: {str(e)}'}

    def stop(self):
        """Stop MQTT broker"""
        try:
            # Always try to stop Docker container (even if we don't have process handle)
            print("[BROKER] Attempting to stop Docker container...")
            try:
                result = subprocess.run(['docker', 'stop', 'plant-mqtt-broker'],
                                      capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    print("[BROKER] Successfully stopped Docker container")
                else:
                    print(f"[BROKER] Docker stop returned code {result.returncode}: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("[BROKER] Docker stop timed out")
            except Exception as e:
                print(f"[BROKER] Error stopping Docker: {e}")

            # Also try process if we have it (Docker or native)
            if self.app_state['broker_process']:
                try:
                    # Use terminate() for all processes - it's safer
                    self.app_state['broker_process'].terminate()
                    # Give it a moment to terminate gracefully
                    try:
                        self.app_state['broker_process'].wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate
                        self.app_state['broker_process'].kill()
                    print("[BROKER] Stopped process")
                except Exception as e:
                    print(f"[BROKER] Error stopping process: {e}")
                finally:
                    self.app_state['broker_process'] = None

            # Update state
            self.app_state['mqtt_broker_running'] = False
            self.socketio.emit('broker_status', {'running': False})

            # Verify it's actually stopped
            time.sleep(0.5)
            try:
                check_result = subprocess.run(['docker', 'ps', '--filter', 'name=plant-mqtt-broker', '--format', '{{.Names}}'],
                                             capture_output=True, text=True, timeout=5)
                if 'plant-mqtt-broker' in check_result.stdout:
                    return {'success': False, 'message': 'Container is still running. Try: docker stop plant-mqtt-broker'}
            except Exception as e:
                print(f"[BROKER] Error checking container status: {e}")

            return {'success': True, 'message': 'MQTT broker stopped'}

        except Exception as e:
            print(f"[BROKER] Unexpected error in stop(): {e}")
            # Still try to update state even if there was an error
            self.app_state['mqtt_broker_running'] = False
            self.socketio.emit('broker_status', {'running': False})
            return {'success': False, 'message': f'Error stopping broker: {str(e)}'}

    def check_status(self):
        """Check if MQTT broker is already running"""
        try:
            result = subprocess.run(['docker', 'ps', '--filter', 'name=plant-mqtt-broker', '--format', '{{.Names}}'],
                                  capture_output=True, text=True)
            if 'plant-mqtt-broker' in result.stdout:
                self.app_state['mqtt_broker_running'] = True
                print("[BROKER] Detected running MQTT broker container")
                return True
        except:
            pass
        return False
