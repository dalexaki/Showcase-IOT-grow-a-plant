from typing import Dict, Any
from src.monitors.health_analyzer import PlantHealthMonitor
from src.core.system_logger import SystemLogger

LOGGER = SystemLogger(
    name=__name__,
    log_file=None,
    log_level="INFO",
    console_level='INFO',
).get_logger()

class MonitorFactory:
    """Factory for creating sensor monitor instances based on configuration."""
    
    @staticmethod
    def create_monitor(config: Dict[str, Any], msg_bus):
        """
        Create a sensor monitor instance based on the configuration type.
        
        Args:
            config: Monitor configuration dictionary
            msg_bus: IoT message broker instance
            
        Returns:
            Monitor instance
            
        Raises:
            ValueError: If monitor type is not supported
        """
        monitor_type = config.get("type")
        
        if monitor_type == "plant":
            return PlantHealthMonitor(config, msg_bus)
        else:
            raise ValueError(f"Unknown monitor type: {monitor_type}")
