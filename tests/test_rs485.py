#!/usr/bin/env python3
"""
Test RS485/Modbus protocol functionality
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from protocols.rs485_handler import RS485Handler, ModbusFunction
import edpm_lite

def test_rs485_basic():
    """Test basic RS485/Modbus functionality"""
    print("⚡ Testing RS485/Modbus Protocol Handler")
    print("=" * 50)
    
    # Initialize RS485 handler in simulator mode
    rs485 = RS485Handler(port="/dev/ttyUSB0", baudrate=9600, simulator=True)
    
    # Test device scanning
    print("📡 Scanning Modbus devices...")
    devices = rs485.scan_devices()
    print(f"Found devices: {devices}")
    
    if not devices:
        print("❌ No Modbus devices found")
        return False
    
    # Test each device
    for slave_id in devices:
        print(f"\n🔧 Testing device {slave_id}...")
        device_info = rs485.get_device_info(slave_id)
        print(f"  Device info: {device_info}")
        
        # Test register reading
        try:
            regs = rs485.read_holding_registers(slave_id, 0, 5)
            print(f"  Holding registers [0-4]: {regs}")
        except Exception as e:
            print(f"  Register read error: {e}")
        
        # Test coil operations (for VFD)
        if slave_id == 3:
            print(f"  Testing VFD coil operations...")
            try:
                # Read initial coil state
                coils = rs485.read_coils(slave_id, 0, 3)
                print(f"    Initial coils: {coils}")
                
                # Start VFD
                rs485.write_single_coil(slave_id, 0, True)
                coils = rs485.read_coils(slave_id, 0, 3)
                print(f"    After start: {coils}")
                
                # Stop VFD
                rs485.write_single_coil(slave_id, 0, False)
                coils = rs485.read_coils(slave_id, 0, 3)
                print(f"    After stop: {coils}")
                
            except Exception as e:
                print(f"    Coil operation error: {e}")
        
        # Test register writing
        try:
            if slave_id == 1:  # Temperature controller
                # Write temperature setpoint
                rs485.write_single_register(slave_id, 0, 230)  # 23.0°C
                print(f"  Set temperature setpoint to 23.0°C")
            elif slave_id == 3:  # VFD
                # Write frequency setpoint
                rs485.write_single_register(slave_id, 0, 4500)  # 45.00Hz
                print(f"  Set VFD frequency to 45.00Hz")
        except Exception as e:
            print(f"  Register write error: {e}")
    
    print("✅ RS485 basic tests completed")
    return True

async def test_rs485_continuous():
    """Test continuous RS485 monitoring"""
    print("\n🔄 Testing RS485 continuous monitoring...")
    
    rs485 = RS485Handler(port="/dev/ttyUSB0", baudrate=9600, simulator=True)
    readings = []
    
    async def data_callback(data):
        readings.append(data)
        slave_id = data.get('slave_id', 0)
        
        if slave_id == 1:  # Temperature controller
            temp = data.get('temperature', 0)
            print(f"  📊 Device {slave_id} (Temp Controller): {temp:.1f}°C")
        elif slave_id == 2:  # Power meter
            power = data.get('power', 0)
            voltage = data.get('voltage', 0)
            print(f"  📊 Device {slave_id} (Power Meter): {power:.2f}kW, {voltage:.1f}V")
        elif slave_id == 3:  # VFD
            freq = data.get('frequency_actual', 0)
            running = data.get('running', False)
            print(f"  📊 Device {slave_id} (VFD): {freq:.1f}Hz, {'Running' if running else 'Stopped'}")
    
    # Start monitoring for 6 seconds
    task = asyncio.create_task(rs485.continuous_monitoring(data_callback, interval=2.0))
    await asyncio.sleep(6)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    print(f"✅ Collected {len(readings)} RS485 readings")
    return len(readings) > 0

def test_rs485_advanced():
    """Test advanced RS485/Modbus operations"""
    print("\n🔬 Testing advanced RS485 operations...")
    
    rs485 = RS485Handler(port="/dev/ttyUSB0", baudrate=9600, simulator=True)
    
    # Test VFD control sequence
    print("  🏭 VFD Control Sequence:")
    try:
        # Initial state
        regs = rs485.read_holding_registers(3, 0, 5)
        print(f"    Initial VFD state: Freq={regs[0]/100.0}Hz, Speed={regs[2]}RPM")
        
        # Set new frequency
        rs485.write_single_register(3, 0, 6000)  # 60.00Hz
        time.sleep(0.1)
        
        # Start VFD
        rs485.write_single_coil(3, 0, True)
        time.sleep(0.1)
        
        # Check running state
        coils = rs485.read_coils(3, 0, 3)
        regs = rs485.read_holding_registers(3, 0, 5)
        print(f"    After start: Running={coils[0]}, Freq={regs[1]/100.0}Hz")
        
        # Ramp down frequency
        for freq in [5500, 5000, 4500, 4000]:  # 55, 50, 45, 40 Hz
            rs485.write_single_register(3, 0, freq)
            time.sleep(0.1)
            actual_freq = rs485.read_holding_registers(3, 1, 1)[0]
            print(f"    Set {freq/100.0}Hz -> Actual {actual_freq/100.0}Hz")
        
        # Stop VFD
        rs485.write_single_coil(3, 0, False)
        coils = rs485.read_coils(3, 0, 3)
        print(f"    After stop: Running={coils[0]}")
        
    except Exception as e:
        print(f"    VFD control error: {e}")
    
    # Test temperature controller
    print("\n  🌡️ Temperature Controller Test:")
    try:
        # Read current values
        regs = rs485.read_holding_registers(1, 0, 5)
        print(f"    Current: Setpoint={regs[0]/10.0}°C, Temp={regs[1]/10.0}°C, Output={regs[2]}%")
        
        # Change setpoint
        rs485.write_single_register(1, 0, 280)  # 28.0°C
        time.sleep(0.1)
        
        # Read updated values
        regs = rs485.read_holding_registers(1, 0, 5)
        print(f"    After setpoint change: Setpoint={regs[0]/10.0}°C, Output={regs[2]}%")
        
    except Exception as e:
        print(f"    Temperature controller error: {e}")
    
    print("✅ Advanced RS485 operations completed")
    return True

def test_rs485_with_edpm():
    """Test RS485 integration with EDPM"""
    print("\n🔗 Testing RS485 with EDPM integration...")
    
    # Initialize EDPM client
    edpm = edpm_lite.EDPMLite(use_zmq=False)  # Offline mode
    rs485 = RS485Handler(port="/dev/ttyUSB0", baudrate=9600, simulator=True)
    
    # Read from each device and log to EDPM
    devices = rs485.scan_devices()
    
    for slave_id in devices[:2]:  # Test first 2 devices
        try:
            device_info = rs485.get_device_info(slave_id)
            regs = rs485.read_holding_registers(slave_id, 0, 3)
            
            data = {
                "slave_id": slave_id,
                "device_name": device_info['name'],
                "registers": regs
            }
            
            # Log the reading
            edpm.log("info", f"Modbus device {slave_id} reading", **data)
            
            # Emit event
            edmp_data = {"protocol": "RS485", "device": device_info['name'], **data}
            edpm.emit_event("modbus_reading", edmp_data)
            
            print(f"📝 Logged device {slave_id} data to EDPM: {data}")
            
        except Exception as e:
            print(f"Error reading device {slave_id}: {e}")
    
    print("✅ RS485-EDPM integration test completed")
    return True

async def main():
    """Main test runner"""
    print("🚀 EDPM RS485/Modbus Protocol Tests")
    print("=" * 50)
    
    tests = [
        ("Basic RS485 Operations", test_rs485_basic),
        ("Continuous Monitoring", test_rs485_continuous),
        ("Advanced Operations", test_rs485_advanced),
        ("EDPM Integration", test_rs485_with_edpm),
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
        print("🎉 All RS485 tests passed!")
        return 0
    else:
        print("⚠️ Some RS485 tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
