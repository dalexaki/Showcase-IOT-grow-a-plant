import asyncio
import json
import platform
import os
import argparse
from src.messaging.broker_client import IoTMessageBroker
from src.monitors.monitor_builder import MonitorFactory
from src.core.system_logger import SystemLogger

# Optional debug output for asyncio
os.environ["PYTHONASYNCIODEBUG"] = "1"

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Grow-a-Plant IoT Controller')
    parser.add_argument('--config', type=str, default='grow_a_plant_config.json',
                      help='Path to the configuration file')
    parser.add_argument('--debug-level', type=str, default='INFO',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help='Debug level for logging')
    
    args = parser.parse_args()
    
    # Setup logger
    logger = SystemLogger(__name__, console_level=args.debug_level).get_logger()
    
    # Load configuration
    with open(args.config, "r") as f:
        config = json.load(f)
    
    # Setup the IoT message broker
    bus = IoTMessageBroker(
        host=config["broker"]["host"],
        port=config["broker"]["port"],
        debug_level=args.debug_level
    )
    logger.info("[MAIN] IoT Message Broker initialized")
    
    # Connect to MQTT broker
    await bus.connect()
    logger.info("[MAIN] Connected to MQTT broker")

    # Create monitors from configuration
    monitors = []
    for monitor_config in config["message_flows"]:
        try:
            monitor = MonitorFactory.create_monitor(monitor_config, bus)
            monitors.append(monitor)
            logger.info(f"[MAIN] Created monitor: {monitor_config['name']}")
        except Exception as e:
            logger.error(f"[MAIN] Error creating monitor {monitor_config['name']}: {e}")
    
    # Start all monitors
    monitor_tasks = []
    for monitor in monitors:
        try:
            task = asyncio.create_task(monitor.start())
            monitor_tasks.append(task)
            logger.info(f"[MAIN] Started monitor: {monitor.name}")
        except Exception as e:
            logger.error(f"[MAIN] Error starting monitor {monitor.name}: {e}")
    
    logger.info("[MAIN] All monitors started. Press Ctrl+C to stop.")

    try:
        await asyncio.gather(*monitor_tasks)
    except KeyboardInterrupt:
        logger.info("\n[MAIN] Shutting down...")
    finally:
        # Stop all monitors
        for monitor in monitors:
            try:
                await monitor.stop()
                logger.info(f"[MAIN] Stopped monitor: {monitor.name}")
            except Exception as e:
                logger.error(f"[MAIN] Error stopping monitor {monitor.name}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
