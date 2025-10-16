"""
Test script to simulate sensor data for the plant monitoring system.
Run this after starting main.py to see the system in action.
"""
import asyncio
import json
import platform
from aiomqtt import Client

# Fix for Windows asyncio compatibility
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_plant_system():
    """Simulate various plant conditions."""
    
    print("=" * 60)
    print("Plant Monitoring System - Test Script")
    print("=" * 60)
    print("\nMake sure main.py is running in another terminal!")
    print("This script will publish test sensor data...\n")
    
    async with Client(hostname="localhost", port=1883) as client:
        
        # Test 1: Healthy plant
        print("\n[TEST 1] Healthy plant conditions")
        print("-" * 40)
        await client.publish("sensors/soil_moisture", json.dumps({"value": 65}))
        print("Published: Moisture = 65%")
        await asyncio.sleep(0.5)
        await client.publish("sensors/temperature", json.dumps({"value": 22}))
        print("Published: Temperature = 22°C")
        print("Expected: watering_hours=24.0h, watering=0, health=100%")
        await asyncio.sleep(3)
        
        # Test 2: Plant needs water
        print("\n[TEST 2] Plant needs water")
        print("-" * 40)
        await client.publish("sensors/soil_moisture", json.dumps({"value": 45}))
        print("Published: Moisture = 45%")
        await asyncio.sleep(0.5)
        await client.publish("sensors/temperature", json.dumps({"value": 22}))
        print("Published: Temperature = 22°C")
        print("Expected: watering_hours=18.0h, watering=1, health=~75%")
        await asyncio.sleep(3)
        
        # Test 3: Urgent watering needed
        print("\n[TEST 3] Urgent watering needed")
        print("-" * 40)
        await client.publish("sensors/soil_moisture", json.dumps({"value": 20}))
        print("Published: Moisture = 20%")
        await asyncio.sleep(0.5)
        await client.publish("sensors/temperature", json.dumps({"value": 25}))
        print("Published: Temperature = 25°C")
        print("Expected: watering_hours=~8.0h, watering=1, health=~50%")
        await asyncio.sleep(3)
        
        # Test 4: Hot temperature increases water needs
        print("\n[TEST 4] Hot temperature")
        print("-" * 40)
        await client.publish("sensors/soil_moisture", json.dumps({"value": 50}))
        print("Published: Moisture = 50%")
        await asyncio.sleep(0.5)
        await client.publish("sensors/temperature", json.dumps({"value": 32}))
        print("Published: Temperature = 32°C (hot!)")
        print("Expected: watering_hours reduced by 30%, watering=1")
        await asyncio.sleep(3)
        
        # Test 5: Cold temperature reduces water needs
        print("\n[TEST 5] Cold temperature")
        print("-" * 40)
        await client.publish("sensors/soil_moisture", json.dumps({"value": 50}))
        print("Published: Moisture = 50%")
        await asyncio.sleep(0.5)
        await client.publish("sensors/temperature", json.dumps({"value": 12}))
        print("Published: Temperature = 12°C (cold!)")
        print("Expected: watering_hours increased by 30%, watering=1")
        await asyncio.sleep(3)
        
        print("\n" + "=" * 60)
        print("Test completed! Check the main.py output for results.")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_plant_system())
