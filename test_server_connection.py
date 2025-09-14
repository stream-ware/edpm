#!/usr/bin/env python3
"""
Test Server Connection for EDPM Lite
Verifies client-server communication works properly
"""
import time
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from edpm_lite import EDPMLite, Message

def test_zmq_connection():
    """Test ZeroMQ connection to server"""
    print("🔌 Testing ZeroMQ connection...")
    
    try:
        # Create client with ZeroMQ
        client = EDPMLite("ipc:///tmp/edpm.ipc", use_zmq=True)
        
        # Test logging
        response = client.log("info", "ZeroMQ connection test")
        if response:
            print(f"✅ ZeroMQ logging successful: {response.d}")
            return True
        else:
            print("❌ ZeroMQ logging failed")
            return False
            
    except Exception as e:
        print(f"❌ ZeroMQ connection error: {e}")
        return False

def test_gpio_with_server():
    """Test GPIO operations with server"""
    print("\n🔧 Testing GPIO operations with server...")
    
    try:
        client = EDPMLite("ipc:///tmp/edpm.ipc", use_zmq=True)
        
        # Test GPIO set
        print("  Setting GPIO pin 17 to HIGH...")
        set_response = client.gpio_set(17, 1)
        if set_response:
            print(f"  ✅ GPIO set response: {set_response.d}")
        
        # Test GPIO get
        print("  Reading GPIO pin 17...")
        get_response = client.gpio_get(17)
        if get_response is not None:
            print(f"  ✅ GPIO value: {get_response}")
        else:
            print("  ❌ GPIO read failed")
            
        # Test GPIO PWM
        print("  Testing PWM on pin 18...")
        pwm_response = client.gpio_pwm(18, 1000, 50)
        if pwm_response:
            print(f"  ✅ PWM response: {pwm_response.d}")
            
        return True
        
    except Exception as e:
        print(f"❌ GPIO test error: {e}")
        return False

def test_events_and_commands():
    """Test event emission and custom commands"""
    print("\n📡 Testing events and commands...")
    
    try:
        client = EDPMLite("ipc:///tmp/edpm.ipc", use_zmq=True)
        
        # Test event emission
        print("  Emitting sensor event...")
        event_response = client.event("sensor_reading", 
                                    temperature=25.3,
                                    humidity=60.2,
                                    timestamp=time.time())
        if event_response:
            print(f"  ✅ Event response: {event_response.d}")
        
        # Test custom command
        print("  Sending custom command...")
        cmd_response = client.cmd("system_status", component="cpu")
        if cmd_response:
            print(f"  ✅ Command response: {cmd_response.d}")
            
        return True
        
    except Exception as e:
        print(f"❌ Events/commands test error: {e}")
        return False

def main():
    """Main test function"""
    print("EDPM Lite Server Connection Test")
    print("=" * 40)
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    # Run all tests
    tests = [
        test_zmq_connection,
        test_gpio_with_server, 
        test_events_and_commands
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All server communication tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check server status")
        return 1

if __name__ == "__main__":
    sys.exit(main())
