#!/usr/bin/env python3
"""
Logging Example for EDPM Lite
Demonstrates different log levels and structured logging
"""
import time
import sys
import os

# Add parent directory to path to import edpm_lite
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edpm_lite import get_client

def main():
    """Logging functionality example"""
    print("EDPM Lite Logging Example")
    print("=" * 35)
    
    # Get EDPM client
    client = get_client()
    
    # Test different log levels
    log_levels = ["debug", "info", "warning", "error"]
    
    print("📝 Testing different log levels...")
    for level in log_levels:
        message = f"This is a {level} message"
        response = client.log(level, message)
        
        if response:
            status = response.d.get("status", "unknown")
            print(f"  {level.upper():7} -> {status}")
        else:
            print(f"  {level.upper():7} -> offline")
        
        time.sleep(0.1)
    
    # Test structured logging with metadata
    print("\n📊 Testing structured logging...")
    
    # System metrics example
    try:
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        client.log("metrics", "System performance", 
                  cpu_usage=cpu_percent,
                  memory_usage=memory_percent, 
                  disk_usage=disk_percent)
        print("  ✅ System metrics logged")
    except ImportError:
        client.log("metrics", "System performance", 
                  cpu_usage=25.5,
                  memory_usage=67.3, 
                  disk_usage=45.1,
                  note="simulated_data")
        print("  ✅ Simulated metrics logged")
    
    # Application event logging
    client.log("info", "User action", 
              action="file_upload",
              user_id="user123", 
              file_size=1024000,
              duration_ms=2500)
    print("  ✅ Application event logged")
    
    # Error logging with context
    client.log("error", "Database connection failed",
              error_code="DB_CONN_001",
              host="localhost",
              port=5432,
              retry_count=3)
    print("  ✅ Error with context logged")
    
    # Test event emission
    print("\n📡 Testing event emission...")
    
    client.event("sensor_reading",
                temperature=23.5,
                humidity=45.2,
                pressure=1013.25,
                sensor_id="BME280_01")
    print("  ✅ Sensor event emitted")
    
    client.event("user_login",
                user_id="admin",
                ip_address="192.168.1.100",
                timestamp=time.time())
    print("  ✅ User event emitted")
    
    # Final completion log
    client.log("info", "Logging example completed successfully",
              examples_run=len(log_levels) + 4,
              duration=time.time())
    
    print("\n✨ Logging example completed!")

if __name__ == "__main__":
    main()
