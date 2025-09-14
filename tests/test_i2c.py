#!/usr/bin/env python3
"""
Test I2C protocol functionality
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from protocols.i2c_handler import I2CHandler
import edpm_lite

def test_i2c_basic():
    """Test basic I2C functionality"""
    print("🔌 Testing I2C Protocol Handler")
    print("=" * 50)
    
    # Initialize I2C handler in simulator mode
    i2c = I2CHandler(bus_number=1, simulator=True)
    
    # Test device scanning
    print("📡 Scanning I2C bus...")
    devices = i2c.scan()
    device_list = [f'0x{addr:02X} ({i2c.DEVICES.get(addr, "Unknown")})' for addr in devices]
    print(f"Found devices: {device_list}")
    
    if not devices:
        print("❌ No I2C devices found")
        return False
    
    # Test BME280 sensor reading
    if 0x76 in devices:
        print("\n🌡️ Testing BME280 sensor...")
        for i in range(3):
            bme_data = i2c.read_bme280()
            print(f"  Reading {i+1}: Temp={bme_data['temperature']}°C, "
                  f"Humidity={bme_data['humidity']}%, "
                  f"Pressure={bme_data['pressure']} hPa")
            time.sleep(1)
    
    # Test ADS1115 ADC
    if 0x48 in devices:
        print("\n⚡ Testing ADS1115 ADC...")
        for ch in range(4):
            voltage = i2c.read_ads1115(channel=ch)
            print(f"  Channel {ch}: {voltage:.3f}V")
    
    print("✅ I2C basic tests completed")
    return True

async def test_i2c_continuous():
    """Test continuous I2C monitoring"""
    print("\n🔄 Testing I2C continuous monitoring...")
    
    i2c = I2CHandler(bus_number=1, simulator=True)
    readings = []
    
    async def data_callback(data):
        readings.append(data)
        print(f"  📊 I2C Data: {data}")
    
    # Start monitoring for 5 seconds
    task = asyncio.create_task(i2c.continuous_monitoring(data_callback, interval=1.0))
    await asyncio.sleep(5)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    print(f"✅ Collected {len(readings)} I2C readings")
    return len(readings) > 0

def test_i2c_with_edpm():
    """Test I2C integration with EDPM"""
    print("\n🔗 Testing I2C with EDPM integration...")
    
    # Initialize EDPM client
    edpm = edpm_lite.EDPMLite(use_zmq=False)  # Offline mode
    i2c = I2CHandler(bus_number=1, simulator=True)
    
    # Read sensor and log to EDPM
    if 0x76 in i2c.scan():
        bme_data = i2c.read_bme280()
        
        # Log the reading
        edpm.log("info", "I2C sensor reading", **bme_data)
        
        # Emit event
        edpm.emit_event("sensor_reading", {
            "protocol": "I2C",
            "device": "BME280",
            **bme_data
        })
        
        print(f"📝 Logged sensor data to EDPM: {bme_data}")
    
    print("✅ I2C-EDPM integration test completed")
    return True

async def main():
    """Main test runner"""
    print("🚀 EDPM I2C Protocol Tests")
    print("=" * 50)
    
    tests = [
        ("Basic I2C Operations", test_i2c_basic),
        ("Continuous Monitoring", test_i2c_continuous),  
        ("EDPM Integration", test_i2c_with_edpm),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
            print(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append(False)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Success Rate: {(sum(results)/len(results)*100):.1f}%")
    
    if all(results):
        print("🎉 All I2C tests passed!")
        return 0
    else:
        print("⚠️ Some I2C tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
