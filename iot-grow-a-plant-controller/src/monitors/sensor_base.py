from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, Optional
from src.messaging.broker_client import IoTMessageBroker
from src.core.system_logger import SystemLogger

LOGGER = SystemLogger(
    name=__name__,
    log_file=None,
    log_level="INFO",
    console_level='INFO',
).get_logger()

class SensorProcessor(ABC):
    """Abstract base class for all sensor data processors."""
    
    def __init__(self, name: str, msg_bus: IoTMessageBroker):
        self.name = name
        self.msg_bus = msg_bus
        self.monitoring_data: Dict[str, float] = {}
        self.lock = asyncio.Lock()

    @abstractmethod
    async def start(self) -> None:
        """Initialize and start the flow processing."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Clean up and stop the flow processing."""
        pass

    def get_monitored_value(self, key: str) -> Optional[float]:
        """Get a value from monitoring storage."""
        return self.monitoring_data.get(key)

    async def store_value(self, key: str, value: float) -> None:
        """Thread-safe storage of monitored values."""
        async with self.lock:
            self.monitoring_data[key] = value
            LOGGER.debug(f"[FLOW] {self.name} stored {key}: {value}")

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate flow configuration."""
        return True
