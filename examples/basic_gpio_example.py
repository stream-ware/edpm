#!/usr/bin/env python3
"""
Basic GPIO Example for EDPM Lite
Demonstrates simple GPIO control and logging
"""
import time
import sys
import os

# Add parent directory to path to import edpm_lite
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edpm_lite import log, gpio_set, gpio_get

def main():
    """Basic GPIO control example"""
    print("EDPM Lite GPIO Example")
    print("=" * 30)
    
    # Log startup
    response = log("info", "Starting GPIO example")
    if response:
        print(f"✅ Logging works! Server response: {response.d.get('status')}")
    else:
        print("⚠️  No server response - running in offline mode")
    
    # GPIO pin to control
    pin = 17
    
    print(f"\n🔌 Testing GPIO pin {pin}")
    
    # Set pin HIGH
    print("Setting pin HIGH...")
    set_response = gpio_set(pin, 1)
    if set_response:
        print(f"✅ GPIO set response: {set_response.d}")
    
    # Read pin value
    print("Reading pin value...")
    value = gpio_get(pin)
    if value is not None:
        print(f"✅ Pin {pin} value: {value}")
    else:
        print("⚠️  Could not read pin value")
    
    time.sleep(1)
    
    # Set pin LOW
    print("Setting pin LOW...")
    gpio_set(pin, 0)
    value = gpio_get(pin)
    if value is not None:
        print(f"✅ Pin {pin} value: {value}")
    
    # Log completion
    log("info", "GPIO example completed successfully")
    
    print("\n✨ Example completed!")

if __name__ == "__main__":
    main()
