import asyncio
from typing import Dict, Any
from .sensor_base import SensorProcessor
from src.core.system_logger import SystemLogger

LOGGER = SystemLogger(
    name=__name__,
    log_file=None,
    log_level="INFO",
    console_level='INFO',
).get_logger()

class PlantHealthMonitor(SensorProcessor):
    """Advanced plant health monitoring system that processes soil moisture and temperature data."""
    
    def __init__(self, config: Dict[str, Any], msg_bus):
        super().__init__(config["name"], msg_bus)
        
        # Running flag
        self._running = False
        self._stop_event = asyncio.Event()
        
        # Faucet control state
        self._faucet_on = False
        
        # Input topics
        self.moisture_topic = config["input"]["soil_moisture_topic"]
        self.temperature_topic = config["input"]["temperature_topic"]
        
        # Output topics
        self.watering_hours_topic = config["output"]["watering_hours_topic"]
        self.currently_watering_topic = config["output"]["currently_watering_topic"]
        self.plant_health_topic = config["output"]["plant_health_topic"]
        self.faucet_command_topic = "faucet/command"
        
        # Thresholds
        self.moisture_low = config["thresholds"]["moisture_low"]
        self.moisture_optimal = config["thresholds"]["moisture_optimal"]
        self.temp_low = config["thresholds"]["temp_low"]
        self.temp_high = config["thresholds"]["temp_high"]
        
        LOGGER.info(f"[FLOW] {self.name} initialized with:")
        LOGGER.info(f"[FLOW] Moisture topic: {self.moisture_topic}")
        LOGGER.info(f"[FLOW] Temperature topic: {self.temperature_topic}")
        LOGGER.info(f"[FLOW] Thresholds: moisture_low={self.moisture_low}% (turn faucet ON), optimal={self.moisture_optimal}% (turn faucet OFF), temp_low={self.temp_low}°C, temp_high={self.temp_high}°C")

    async def _handle_moisture(self, message: Dict[str, Any]):
        """Handle incoming soil moisture data."""
        try:
            moisture = float(message.get("value", 0))
            await self.store_value("moisture", moisture)
            LOGGER.info(f"[FLOW] {self.name} Soil moisture updated: {moisture}%")
            await self._evaluate_plant_status()
        except Exception as e:
            LOGGER.error(f"[FLOW] {self.name} Error handling moisture: {e}")

    async def _handle_temperature(self, message: Dict[str, Any]):
        """Handle incoming temperature data."""
        try:
            temperature = float(message.get("value", 0))
            await self.store_value("temperature", temperature)
            LOGGER.info(f"[FLOW] {self.name} Temperature updated: {temperature}°C")
            await self._evaluate_plant_status()
        except Exception as e:
            LOGGER.error(f"[FLOW] {self.name} Error handling temperature: {e}")

    async def _evaluate_plant_status(self):
        """Evaluate plant status and publish results."""
        moisture = self.get_monitored_value("moisture")
        temperature = self.get_monitored_value("temperature")
        
        # Wait until we have both values
        if moisture is None or temperature is None:
            LOGGER.debug(f"[FLOW] {self.name} Waiting for all sensor data...")
            return
        
        # Calculate watering hours needed (0-24 hours)
        watering_hours = self._calculate_watering_hours(moisture, temperature)
        
        # Determine if currently watering (moisture below optimal)
        currently_watering = 1 if moisture < self.moisture_optimal else 0
        
        # Calculate plant health (0-100%)
        plant_health = self._calculate_plant_health(moisture, temperature)
        
        # Publish results
        await self.msg_bus.publish(
            self.watering_hours_topic,
            {"value": watering_hours}
        )
        
        await self.msg_bus.publish(
            self.currently_watering_topic,
            {"value": currently_watering}
        )
        
        await self.msg_bus.publish(
            self.plant_health_topic,
            {"value": plant_health}
        )
        
        # REALISTIC FAUCET-BASED AUTO-WATERING LOGIC
        if moisture <= self.moisture_low and not self._faucet_on:
            # Turn ON faucet - moisture is critically low
            LOGGER.warning(f"[FLOW] {self.name} CRITICAL MOISTURE ({moisture}%)! Turning faucet ON...")
            await self.msg_bus.publish(self.faucet_command_topic, {"command": 1})
            self._faucet_on = True

        elif moisture >= self.moisture_optimal and self._faucet_on:
            # Turn OFF faucet - target moisture reached
            LOGGER.info(f"[FLOW] {self.name} Target moisture reached ({moisture}%)! Turning faucet OFF...")
            await self.msg_bus.publish(self.faucet_command_topic, {"command": 0})
            self._faucet_on = False
        
        faucet_status = "ON" if self._faucet_on else "OFF"
        LOGGER.info(f"[FLOW] {self.name} Status: moisture={moisture}%, watering_hours={watering_hours}h, watering={currently_watering}, health={plant_health}%, faucet={faucet_status}")

    def _calculate_watering_hours(self, moisture: float, temperature: float) -> float:
        """
        Calculate hours until next watering needed based on moisture and temperature.
        
        Logic:
        - If moisture is optimal or above, less/no watering needed
        - If moisture is low, more watering needed
        - Higher temperatures increase water needs
        """
        if moisture >= self.moisture_optimal:
            # Plant is well hydrated
            base_hours = 24.0
        elif moisture >= self.moisture_low:
            # Plant needs water soon
            moisture_ratio = (moisture - self.moisture_low) / (self.moisture_optimal - self.moisture_low)
            base_hours = 12.0 + (moisture_ratio * 12.0)
        else:
            # Plant needs water urgently
            base_hours = max(0, moisture / self.moisture_low * 12.0)
        
        # Adjust for temperature (higher temp = more water needed sooner)
        if temperature > self.temp_high:
            temp_factor = 0.7  # Reduce time by 30%
        elif temperature < self.temp_low:
            temp_factor = 1.3  # Increase time by 30%
        else:
            temp_factor = 1.0
        
        return round(base_hours * temp_factor, 1)

    def _calculate_plant_health(self, moisture: float, temperature: float) -> int:
        """
        Calculate overall plant health (0-100%).
        
        Logic:
        - Optimal moisture and temperature = 100%
        - Deviations reduce health
        """
        # Moisture health score (0-50 points)
        if moisture >= self.moisture_optimal:
            moisture_score = 50
        elif moisture >= self.moisture_low:
            moisture_ratio = (moisture - self.moisture_low) / (self.moisture_optimal - self.moisture_low)
            moisture_score = 25 + (moisture_ratio * 25)
        else:
            moisture_score = max(0, (moisture / self.moisture_low) * 25)
        
        # Temperature health score (0-50 points)
        temp_optimal_mid = (self.temp_low + self.temp_high) / 2
        temp_range = self.temp_high - self.temp_low
        
        if self.temp_low <= temperature <= self.temp_high:
            # Within optimal range
            temp_deviation = abs(temperature - temp_optimal_mid) / (temp_range / 2)
            temp_score = 50 * (1 - temp_deviation * 0.3)
        else:
            # Outside optimal range
            if temperature < self.temp_low:
                deviation = (self.temp_low - temperature) / self.temp_low
            else:
                deviation = (temperature - self.temp_high) / self.temp_high
            temp_score = max(0, 50 * (1 - deviation))
        
        total_health = int(moisture_score + temp_score)
        return min(100, max(0, total_health))

    async def start(self):
        """Start subscriptions to sensor topics."""
        try:
            self._running = True
            self._stop_event.clear()
            
            # Subscribe to moisture sensor
            asyncio.create_task(
                self.msg_bus.subscribe(self.moisture_topic, self._handle_moisture)
            )
            
            # Subscribe to temperature sensor
            asyncio.create_task(
                self.msg_bus.subscribe(self.temperature_topic, self._handle_temperature)
            )
            
            LOGGER.info(f"[FLOW] {self.name} Started successfully")
            
            # Keep the monitor running until stop is called
            await self._stop_event.wait()
            
        except Exception as e:
            LOGGER.error(f"[FLOW] {self.name} Error starting: {e}")

    async def stop(self):
        """Stop the flow."""
        self._running = False
        self._stop_event.set()
        LOGGER.info(f"[FLOW] {self.name} Stopped")
