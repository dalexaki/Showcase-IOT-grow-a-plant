"""
Configuration Manager Module
Handles reading and updating controller configuration files
"""
import json
import os


class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'iot-grow-a-plant-controller',
            'grow_a_plant_config.json'
        )

    def get_config(self):
        """Load and return the controller configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return {'success': True, 'config': config}
        except Exception as e:
            return {'success': False, 'message': f'Error loading config: {str(e)}'}

    def update_config(self, data):
        """Update the controller configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Update thresholds
            config['message_flows'][0]['thresholds'] = data['thresholds']

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            return {'success': True, 'message': 'Configuration updated! Restart controller to apply changes.'}
        except Exception as e:
            return {'success': False, 'message': f'Error updating config: {str(e)}'}
