"""
Controller Manager Module
Handles the lifecycle of the plant controller process
"""
import subprocess
import os
import signal
import time
from threading import Thread


class ControllerManager:
    def __init__(self, app_state, socketio):
        self.app_state = app_state
        self.socketio = socketio

    def start(self):
        """Start the plant controller process"""
        if self.app_state['controller_running']:
            return {'success': False, 'message': 'Controller already running'}

        try:
            controller_path = os.path.join(os.path.dirname(__file__), '..', 'iot-grow-a-plant-controller')

            print(f"[CONTROLLER] Starting in: {controller_path}")

            if os.name == 'nt':  # Windows
                self.app_state['controller_process'] = subprocess.Popen(
                    ['python', 'main.py'],
                    cwd=controller_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:  # Linux/Mac
                self.app_state['controller_process'] = subprocess.Popen(
                    ['python', 'main.py'],
                    cwd=controller_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )

            # Start thread to stream output
            output_thread = Thread(target=self._stream_output, args=(self.app_state['controller_process'],))
            output_thread.daemon = True
            output_thread.start()

            time.sleep(2)  # Wait a bit longer to see if it crashes

            # Check if process is still running
            if self.app_state['controller_process'].poll() is not None:
                # Process ended, get the error
                return {'success': False, 'message': 'Controller crashed on startup. Check Flask console for logs.'}

            self.app_state['controller_running'] = True
            self.socketio.emit('controller_status', {'running': True})
            return {'success': True, 'message': 'Plant controller started - check Flask console for logs'}
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[CONTROLLER ERROR] {error_details}")
            return {'success': False, 'message': f'Error starting controller: {str(e)}'}

    def stop(self):
        """Stop the controller process"""
        if not self.app_state['controller_running']:
            return {'success': False, 'message': 'Controller not running'}

        try:
            if self.app_state['controller_process']:
                if os.name == 'nt':
                    # On Windows, terminate the process tree to kill child processes too
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.app_state['controller_process'].pid)],
                                     capture_output=True, timeout=5)
                    except:
                        # Fallback to direct termination
                        self.app_state['controller_process'].terminate()
                else:
                    # On Linux/Mac, terminate the process gracefully
                    self.app_state['controller_process'].terminate()
                    # If terminate doesn't work after 2 seconds, force kill
                    try:
                        self.app_state['controller_process'].wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        print("[CONTROLLER] Process didn't terminate, forcing kill...")
                        self.app_state['controller_process'].kill()

                # Wait for process to actually terminate
                self.app_state['controller_process'].wait(timeout=3)
                self.app_state['controller_process'] = None

            self.app_state['controller_running'] = False
            self.socketio.emit('controller_status', {'running': False})
            return {'success': True, 'message': 'Plant controller stopped'}
        except Exception as e:
            return {'success': False, 'message': f'Error stopping controller: {str(e)}'}

    def _stream_output(self, process):
        """Stream controller output to console"""
        for line in iter(process.stdout.readline, b''):
            if line:
                try:
                    # Try UTF-8 first, fallback to latin-1 for Windows special chars
                    log_line = line.decode('utf-8', errors='replace').strip()
                except:
                    log_line = line.decode('latin-1', errors='replace').strip()
                print(f"[CONTROLLER] {log_line}")
                # Also emit to frontend
                self.socketio.emit('controller_log', {'message': log_line})
