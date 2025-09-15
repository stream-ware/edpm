#!/usr/bin/env python3
"""
I2C Sensor Monitoring Example for EDPM Lite
Demonstrates comprehensive I2C sensor communication with real-time data collection.
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from edpm import EDPMClient, Config, Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Sensor reading data structure"""
    sensor_address: int
    sensor_name: str
    sensor_type: str
    timestamp: float
    data: Dict[str, Any]
    unit: Dict[str, str]


class I2CSensorMonitor:
    """I2C Sensor Monitoring Application"""
    
    def __init__(self, config_path: str = "config.json", sensor_config_path: str = "sensor_configs.json"):
        """Initialize the I2C sensor monitor"""
        self.config_path = Path(config_path)
        self.sensor_config_path = Path(sensor_config_path)
        self.config = self.load_config()
        self.sensor_configs = self.load_sensor_configs()
        self.client = None
        self.running = False
        self.sensor_readings = []
        self.detected_sensors = []
    
    def load_config(self) -> dict:
        """Load main configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "edpm_endpoint": "ipc:///tmp/edpm.ipc",
                "websocket_url": "ws://localhost:8080/ws",
                "transport": "zmq",
                "i2c_bus": 1,
                "scan_range": {"start": 0x08, "end": 0x77},
                "monitoring_interval": 5.0,
                "data_retention_hours": 24,
                "alert_thresholds": {
                    "temperature": {"min": -10, "max": 50},
                    "humidity": {"min": 10, "max": 90}
                }
            }
    
    def load_sensor_configs(self) -> dict:
        """Load sensor configurations from file"""
        if self.sensor_config_path.exists():
            with open(self.sensor_config_path) as f:
                return json.load(f)
        else:
            # Default sensor configurations
            return {
                "0x76": {
                    "name": "BME280",
                    "type": "environmental",
                    "description": "Temperature, Humidity, Pressure Sensor",
                    "registers": {
                        "chip_id": {"address": 0xD0, "expected": 0x60},
                        "temp_raw": {"address": 0xFA, "bytes": 3},
                        "pressure_raw": {"address": 0xF7, "bytes": 3},
                        "humidity_raw": {"address": 0xFD, "bytes": 2}
                    },
                    "calibration_registers": {
                        "start": 0x88,
                        "end": 0x9F
                    }
                },
                "0x68": {
                    "name": "MPU6050",
                    "type": "motion",
                    "description": "6-axis Accelerometer and Gyroscope",
                    "registers": {
                        "who_am_i": {"address": 0x75, "expected": 0x68},
                        "accel_x": {"address": 0x3B, "bytes": 2},
                        "accel_y": {"address": 0x3D, "bytes": 2},
                        "accel_z": {"address": 0x3F, "bytes": 2},
                        "temp": {"address": 0x41, "bytes": 2},
                        "gyro_x": {"address": 0x43, "bytes": 2},
                        "gyro_y": {"address": 0x45, "bytes": 2},
                        "gyro_z": {"address": 0x47, "bytes": 2}
                    }
                },
                "0x57": {
                    "name": "DS3231",
                    "type": "rtc",
                    "description": "Real-Time Clock",
                    "registers": {
                        "seconds": {"address": 0x00},
                        "minutes": {"address": 0x01},
                        "hours": {"address": 0x02},
                        "temperature": {"address": 0x11, "bytes": 2}
                    }
                }
            }
    
    async def connect(self):
        """Connect to EDPM server"""
        try:
            # Create EDPM client
            edpm_config = Config()
            edpm_config.endpoint = self.config["edpm_endpoint"]
            
            self.client = EDPMClient(edpm_config, transport=self.config["transport"])
            await self.client.connect()
            
            logger.info(f"Connected to EDPM server via {self.config['transport']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to EDPM server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from EDPM server"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from EDPM server")
    
    async def log_message(self, level: str, message: str):
        """Send log message to EDPM server"""
        try:
            if self.client:
                log_msg = Message.log(level, message)
                await self.client.send_message(log_msg)
            logger.info(f"{level.upper()}: {message}")
        except Exception as e:
            logger.error(f"Failed to send log message: {e}")
    
    async def scan_i2c_devices(self) -> List[int]:
        """Scan for I2C devices on the bus"""
        logger.info("Scanning for I2C devices...")
        await self.log_message("info", "Starting I2C device scan")
        
        try:
            scan_result = await self.client.send_command("i2c", {
                "action": "scan_devices",
                "bus": self.config["i2c_bus"]
            })
            
            if scan_result and "devices" in scan_result:
                devices = scan_result["devices"]
                logger.info(f"Found {len(devices)} I2C devices: {[hex(addr) for addr in devices]}")
                await self.log_message("info", f"Found {len(devices)} I2C devices")
                return devices
            else:
                logger.warning("No I2C devices found")
                return []
                
        except Exception as e:
            logger.error(f"Error scanning I2C devices: {e}")
            await self.log_message("error", f"I2C scan failed: {e}")
            return []
    
    async def identify_sensors(self, devices: List[int]) -> List[Dict[str, Any]]:
        """Identify detected sensors based on known configurations"""
        identified_sensors = []
        
        for device_addr in devices:
            addr_hex = f"0x{device_addr:02X}"
            
            if addr_hex in self.sensor_configs:
                sensor_config = self.sensor_configs[addr_hex]
                
                # Try to verify sensor identity
                try:
                    if "who_am_i" in sensor_config.get("registers", {}):
                        who_am_i_reg = sensor_config["registers"]["who_am_i"]
                        result = await self.client.i2c_read(
                            device_addr, 
                            who_am_i_reg["address"], 
                            1
                        )
                        
                        if result and len(result) > 0:
                            read_value = result[0]
                            expected_value = who_am_i_reg.get("expected")
                            
                            if expected_value and read_value == expected_value:
                                identified_sensors.append({
                                    "address": device_addr,
                                    "name": sensor_config["name"],
                                    "type": sensor_config["type"],
                                    "description": sensor_config["description"],
                                    "verified": True
                                })
                                logger.info(f"Verified sensor {sensor_config['name']} at 0x{device_addr:02X}")
                            else:
                                logger.warning(f"Sensor at 0x{device_addr:02X} failed verification")
                    else:
                        # Add sensor without verification
                        identified_sensors.append({
                            "address": device_addr,
                            "name": sensor_config["name"],
                            "type": sensor_config["type"],
                            "description": sensor_config["description"],
                            "verified": False
                        })
                        
                except Exception as e:
                    logger.error(f"Error verifying sensor at 0x{device_addr:02X}: {e}")
            else:
                # Unknown device
                identified_sensors.append({
                    "address": device_addr,
                    "name": f"Unknown_0x{device_addr:02X}",
                    "type": "unknown",
                    "description": "Unidentified I2C device",
                    "verified": False
                })
        
        return identified_sensors
    
    async def read_bme280_sensor(self, address: int) -> Optional[SensorReading]:
        """Read BME280 environmental sensor data"""
        try:
            # Read raw temperature data
            temp_data = await self.client.i2c_read(address, 0xFA, 3)
            # Read raw pressure data
            pressure_data = await self.client.i2c_read(address, 0xF7, 3)
            # Read raw humidity data
            humidity_data = await self.client.i2c_read(address, 0xFD, 2)
            
            if temp_data and pressure_data and humidity_data:
                # Simplified conversion (would normally require calibration data)
                temp_raw = (temp_data[0] << 16) | (temp_data[1] << 8) | temp_data[2]
                pressure_raw = (pressure_data[0] << 16) | (pressure_data[1] << 8) | pressure_data[2]
                humidity_raw = (humidity_data[0] << 8) | humidity_data[1]
                
                # Simplified calculations (actual BME280 requires complex calibration)
                temperature = (temp_raw / 5120.0) - 40.0  # Approximation
                pressure = pressure_raw / 256.0  # Approximation
                humidity = humidity_raw / 512.0  # Approximation
                
                return SensorReading(
                    sensor_address=address,
                    sensor_name="BME280",
                    sensor_type="environmental",
                    timestamp=time.time(),
                    data={
                        "temperature": round(temperature, 2),
                        "pressure": round(pressure, 2),
                        "humidity": round(humidity, 2)
                    },
                    unit={
                        "temperature": "°C",
                        "pressure": "hPa",
                        "humidity": "%"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error reading BME280 sensor at 0x{address:02X}: {e}")
        
        return None
    
    async def read_mpu6050_sensor(self, address: int) -> Optional[SensorReading]:
        """Read MPU6050 motion sensor data"""
        try:
            # Read accelerometer data
            accel_x_data = await self.client.i2c_read(address, 0x3B, 2)
            accel_y_data = await self.client.i2c_read(address, 0x3D, 2)
            accel_z_data = await self.client.i2c_read(address, 0x3F, 2)
            
            # Read gyroscope data
            gyro_x_data = await self.client.i2c_read(address, 0x43, 2)
            gyro_y_data = await self.client.i2c_read(address, 0x45, 2)
            gyro_z_data = await self.client.i2c_read(address, 0x47, 2)
            
            # Read temperature
            temp_data = await self.client.i2c_read(address, 0x41, 2)
            
            if all([accel_x_data, accel_y_data, accel_z_data, 
                   gyro_x_data, gyro_y_data, gyro_z_data, temp_data]):
                
                # Convert 16-bit signed values
                def to_signed_16(data):
                    val = (data[0] << 8) | data[1]
                    return val - 65536 if val > 32767 else val
                
                accel_x = to_signed_16(accel_x_data) / 16384.0  # ±2g scale
                accel_y = to_signed_16(accel_y_data) / 16384.0
                accel_z = to_signed_16(accel_z_data) / 16384.0
                
                gyro_x = to_signed_16(gyro_x_data) / 131.0  # ±250°/s scale
                gyro_y = to_signed_16(gyro_y_data) / 131.0
                gyro_z = to_signed_16(gyro_z_data) / 131.0
                
                temperature = (to_signed_16(temp_data) / 340.0) + 36.53
                
                return SensorReading(
                    sensor_address=address,
                    sensor_name="MPU6050",
                    sensor_type="motion",
                    timestamp=time.time(),
                    data={
                        "accel_x": round(accel_x, 3),
                        "accel_y": round(accel_y, 3),
                        "accel_z": round(accel_z, 3),
                        "gyro_x": round(gyro_x, 3),
                        "gyro_y": round(gyro_y, 3),
                        "gyro_z": round(gyro_z, 3),
                        "temperature": round(temperature, 2)
                    },
                    unit={
                        "accel_x": "g", "accel_y": "g", "accel_z": "g",
                        "gyro_x": "°/s", "gyro_y": "°/s", "gyro_z": "°/s",
                        "temperature": "°C"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error reading MPU6050 sensor at 0x{address:02X}: {e}")
        
        return None
    
    async def read_sensor_data(self, sensor: Dict[str, Any]) -> Optional[SensorReading]:
        """Read data from a specific sensor"""
        address = sensor["address"]
        sensor_name = sensor["name"]
        
        try:
            if sensor_name == "BME280":
                return await self.read_bme280_sensor(address)
            elif sensor_name == "MPU6050":
                return await self.read_mpu6050_sensor(address)
            else:
                # Generic sensor reading
                data = await self.client.i2c_read(address, 0x00, 4)
                if data:
                    return SensorReading(
                        sensor_address=address,
                        sensor_name=sensor_name,
                        sensor_type=sensor.get("type", "unknown"),
                        timestamp=time.time(),
                        data={"raw": data},
                        unit={"raw": "bytes"}
                    )
        
        except Exception as e:
            logger.error(f"Error reading sensor {sensor_name} at 0x{address:02X}: {e}")
        
        return None
    
    async def monitor_sensors(self):
        """Main sensor monitoring loop"""
        logger.info("Starting sensor monitoring...")
        await self.log_message("info", "Starting I2C sensor monitoring")
        
        # Initial device scan and identification
        devices = await self.scan_i2c_devices()
        self.detected_sensors = await self.identify_sensors(devices)
        
        if not self.detected_sensors:
            logger.warning("No sensors detected, monitoring will use simulated data")
            await self.log_message("warning", "No I2C sensors detected, using simulator")
        
        # Monitoring loop
        monitor_interval = self.config["monitoring_interval"]
        
        while self.running:
            readings_batch = []
            
            for sensor in self.detected_sensors:
                reading = await self.read_sensor_data(sensor)
                if reading:
                    readings_batch.append(reading)
                    
                    # Log significant readings
                    data_summary = ", ".join([f"{k}:{v}" for k, v in reading.data.items()])
                    logger.info(f"{reading.sensor_name}: {data_summary}")
            
            # Store readings
            self.sensor_readings.extend(readings_batch)
            
            # Send readings to server for dashboard display
            for reading in readings_batch:
                try:
                    await self.client.send_command("log", {
                        "level": "data",
                        "sensor": reading.sensor_name,
                        "address": f"0x{reading.sensor_address:02X}",
                        "data": reading.data,
                        "units": reading.unit,
                        "timestamp": reading.timestamp
                    })
                except Exception as e:
                    logger.error(f"Failed to send reading to server: {e}")
            
            # Check alerts
            await self.check_alerts(readings_batch)
            
            # Clean old readings
            self.cleanup_old_readings()
            
            # Wait for next monitoring cycle
            await asyncio.sleep(monitor_interval)
    
    async def check_alerts(self, readings: List[SensorReading]):
        """Check sensor readings against alert thresholds"""
        thresholds = self.config.get("alert_thresholds", {})
        
        for reading in readings:
            for param, value in reading.data.items():
                if param in thresholds and isinstance(value, (int, float)):
                    threshold = thresholds[param]
                    min_val = threshold.get("min")
                    max_val = threshold.get("max")
                    
                    if min_val is not None and value < min_val:
                        alert_msg = f"LOW {param}: {value} < {min_val} on {reading.sensor_name}"
                        logger.warning(alert_msg)
                        await self.log_message("warning", alert_msg)
                    
                    elif max_val is not None and value > max_val:
                        alert_msg = f"HIGH {param}: {value} > {max_val} on {reading.sensor_name}"
                        logger.warning(alert_msg)
                        await self.log_message("warning", alert_msg)
    
    def cleanup_old_readings(self):
        """Remove old sensor readings to limit memory usage"""
        retention_hours = self.config.get("data_retention_hours", 24)
        cutoff_time = time.time() - (retention_hours * 3600)
        
        original_count = len(self.sensor_readings)
        self.sensor_readings = [r for r in self.sensor_readings if r.timestamp > cutoff_time]
        
        if len(self.sensor_readings) < original_count:
            removed = original_count - len(self.sensor_readings)
            logger.debug(f"Cleaned up {removed} old sensor readings")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "running": self.running,
            "detected_sensors": len(self.detected_sensors),
            "total_readings": len(self.sensor_readings),
            "sensors": [
                {
                    "name": s["name"],
                    "address": f"0x{s['address']:02X}",
                    "type": s["type"],
                    "verified": s["verified"]
                }
                for s in self.detected_sensors
            ],
            "monitoring_interval": self.config["monitoring_interval"],
            "i2c_bus": self.config["i2c_bus"]
        }
    
    async def run_monitoring(self):
        """Run the complete I2C sensor monitoring application"""
        self.running = True
        
        try:
            await self.log_message("info", "I2C Sensor Monitor started")
            
            # Connect to EDPM server
            if not await self.connect():
                logger.error("Cannot connect to EDPM server, exiting...")
                return
            
            # Get initial I2C status
            i2c_status = await self.client.send_command("i2c", {"action": "i2c_status"})
            logger.info(f"I2C status: {i2c_status}")
            
            # Start sensor monitoring
            await self.monitor_sensors()
            
            await self.log_message("info", "I2C Sensor Monitor completed")
            logger.info("Monitoring completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
            await self.log_message("info", "I2C monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await self.log_message("error", f"I2C monitoring error: {e}")
        finally:
            self.running = False
            await self.disconnect()
    
    def stop(self):
        """Stop the monitoring"""
        self.running = False


async def main():
    """Main entry point"""
    print("EDPM Lite I2C Sensor Monitoring Example")
    print("=" * 45)
    print("This example demonstrates I2C sensor communication using EDPM Lite")
    print("Press Ctrl+C to stop the monitoring")
    print()
    
    # Create and run the sensor monitor
    monitor = I2CSensorMonitor()
    
    # Setup signal handling
    import signal
    def signal_handler(sig, frame):
        logger.info("Received stop signal...")
        monitor.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the monitoring
    await monitor.run_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
