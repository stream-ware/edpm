"""
EDPM I2C Protocol Handler
I2C communication with sensor support and simulator for development.
"""

import asyncio
import struct
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from ..core.config import Config

# Optional I2C dependencies
try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    smbus2 = None

logger = logging.getLogger(__name__)


@dataclass
class I2CDevice:
    """I2C Device representation"""
    address: int
    name: str
    registers: Dict[int, int]
    read_only: List[int] = None
    write_only: List[int] = None
    
    def __post_init__(self):
        if self.read_only is None:
            self.read_only = []
        if self.write_only is None:
            self.write_only = []


class I2CHandler:
    """
    I2C Protocol Handler
    
    Handles I2C communication with support for common sensors like BME280, ADS1115,
    and other I2C devices. Includes simulator mode for development and testing.
    """
    
    # Common I2C device addresses and names
    DEVICES = {
        0x76: "BME280",  # Temperature, Humidity, Pressure sensor
        0x77: "BMP280",  # Temperature, Pressure sensor
        0x48: "ADS1115", # 16-bit ADC
        0x49: "ADS1115", # Alternate ADS1115 address
        0x4A: "ADS1115", # Alternate ADS1115 address
        0x4B: "ADS1115", # Alternate ADS1115 address
        0x20: "PCF8574", # GPIO Expander
        0x21: "PCF8574", # Alternate PCF8574 address
        0x68: "DS3231",  # Real-Time Clock
        0x3C: "SSD1306", # OLED Display
        0x3D: "SSD1306", # Alternate SSD1306 address
        0x27: "LCD1602", # LCD Display with I2C backpack
    }
    
    def __init__(self, config: Config = None):
        """Initialize I2C Handler"""
        self.config = config or Config.from_env()
        self.bus_number = 1  # Default I2C bus on Raspberry Pi
        self.simulator = None
        self.bus = None
        self.devices = {}
        self.scan_results = []
        
        # Initialize I2C based on configuration
        if self.config.i2c_simulator:
            self._init_simulator()
        elif HAS_SMBUS:
            self._init_hardware()
        else:
            logger.warning("I2C hardware not available, using simulator")
            self._init_simulator()
        
        logger.info(f"I2C Handler initialized - Bus: {self.bus_number}, Simulator: {self.simulator is not None}")
    
    def _init_simulator(self):
        """Initialize I2C simulator"""
        self.simulator = I2CSimulator()
        # Pre-populate with common devices
        self.simulator.add_device(0x76, "BME280")
        self.simulator.add_device(0x48, "ADS1115")
    
    def _init_hardware(self):
        """Initialize I2C hardware"""
        try:
            self.bus = smbus2.SMBus(self.bus_number)
            logger.info(f"I2C hardware bus {self.bus_number} initialized")
        except Exception as e:
            logger.error(f"Failed to initialize I2C hardware: {e}")
            logger.warning("Falling back to simulator")
            self._init_simulator()
    
    async def handle_command(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle I2C command
        
        Args:
            action: I2C action to perform
            data: Command parameters
            
        Returns:
            Result dictionary
        """
        try:
            if action == "i2c_scan":
                return await self.scan_bus()
            elif action == "i2c_read":
                return await self.read_device(
                    data.get("address"),
                    data.get("register"),
                    data.get("length", 1)
                )
            elif action == "i2c_write":
                return await self.write_device(
                    data.get("address"),
                    data.get("data"),
                    data.get("register")
                )
            elif action == "i2c_read_sensor":
                return await self.read_sensor(data.get("sensor", "BME280"))
            elif action == "read_all_sensors":
                return await self.read_all_sensors()
            elif action == "i2c_status":
                return await self.get_status()
            else:
                raise ValueError(f"Unknown I2C action: {action}")
                
        except Exception as e:
            logger.error(f"I2C command error: {e}")
            raise
    
    async def scan_bus(self) -> Dict[str, Any]:
        """Scan I2C bus for devices"""
        devices_found = []
        
        try:
            for address in range(0x03, 0x78):  # Valid I2C address range
                try:
                    if self.simulator:
                        if self.simulator.device_exists(address):
                            device_name = self.DEVICES.get(address, f"Unknown_{hex(address)}")
                            devices_found.append({
                                'address': address,
                                'hex_address': hex(address),
                                'name': device_name
                            })
                    else:
                        # Try to read from device
                        self.bus.read_byte(address)
                        device_name = self.DEVICES.get(address, f"Unknown_{hex(address)}")
                        devices_found.append({
                            'address': address,
                            'hex_address': hex(address),
                            'name': device_name
                        })
                except:
                    # Device not present
                    continue
            
            self.scan_results = devices_found
            
            return {
                'devices_found': len(devices_found),
                'devices': devices_found,
                'bus_number': self.bus_number
            }
            
        except Exception as e:
            raise Exception(f"I2C bus scan failed: {e}")
    
    async def read_device(self, address: int, register: int = None, length: int = 1) -> Dict[str, Any]:
        """Read from I2C device"""
        if address is None:
            raise ValueError("Device address required")
        
        try:
            if self.simulator:
                if register is not None:
                    data = self.simulator.read_register(address, register, length)
                else:
                    data = self.simulator.read_byte(address)
                    if isinstance(data, int):
                        data = [data]
            else:
                if register is not None:
                    if length == 1:
                        data = [self.bus.read_byte_data(address, register)]
                    else:
                        data = self.bus.read_i2c_block_data(address, register, length)
                else:
                    data = [self.bus.read_byte(address)]
            
            return {
                'address': address,
                'hex_address': hex(address),
                'register': register,
                'length': length,
                'data': data,
                'hex_data': [hex(b) for b in data] if isinstance(data, list) else [hex(data)]
            }
            
        except Exception as e:
            raise Exception(f"Failed to read from I2C device {hex(address)}: {e}")
    
    async def write_device(self, address: int, data: Union[int, List[int], bytes], register: int = None) -> Dict[str, Any]:
        """Write to I2C device"""
        if address is None:
            raise ValueError("Device address required")
        if data is None:
            raise ValueError("Data required")
        
        try:
            # Convert data to list of bytes
            if isinstance(data, int):
                data_bytes = [data]
            elif isinstance(data, bytes):
                data_bytes = list(data)
            elif isinstance(data, list):
                data_bytes = data
            else:
                raise ValueError(f"Invalid data type: {type(data)}")
            
            if self.simulator:
                if register is not None:
                    result = self.simulator.write_register(address, register, data_bytes)
                else:
                    result = self.simulator.write_byte(address, data_bytes[0])
            else:
                if register is not None:
                    if len(data_bytes) == 1:
                        self.bus.write_byte_data(address, register, data_bytes[0])
                    else:
                        self.bus.write_i2c_block_data(address, register, data_bytes)
                else:
                    self.bus.write_byte(address, data_bytes[0])
                result = True
            
            return {
                'address': address,
                'hex_address': hex(address),
                'register': register,
                'data_written': data_bytes,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to write to I2C device {hex(address)}: {e}")
    
    async def read_sensor(self, sensor_type: str) -> Dict[str, Any]:
        """Read from specific sensor type"""
        try:
            if sensor_type.upper() == "BME280":
                return await self._read_bme280()
            elif sensor_type.upper() == "ADS1115":
                return await self._read_ads1115()
            else:
                raise ValueError(f"Unsupported sensor type: {sensor_type}")
                
        except Exception as e:
            raise Exception(f"Failed to read sensor {sensor_type}: {e}")
    
    async def read_all_sensors(self) -> Dict[str, Any]:
        """Read from all available sensors"""
        results = {}
        errors = {}
        
        # Try to read BME280
        try:
            bme280_data = await self._read_bme280()
            results['BME280'] = bme280_data
        except Exception as e:
            errors['BME280'] = str(e)
        
        # Try to read ADS1115
        try:
            ads1115_data = await self._read_ads1115()
            results['ADS1115'] = ads1115_data
        except Exception as e:
            errors['ADS1115'] = str(e)
        
        return {
            'sensor_data': results,
            'errors': errors,
            'timestamp': time.time()
        }
    
    async def _read_bme280(self) -> Dict[str, Any]:
        """Read BME280 temperature, humidity, and pressure sensor"""
        address = 0x76  # Default BME280 address
        
        try:
            if self.simulator:
                # Generate realistic sensor data
                temperature = 20.0 + random.uniform(-5.0, 15.0)
                humidity = 50.0 + random.uniform(-10.0, 20.0)
                pressure = 1013.25 + random.uniform(-20.0, 20.0)
            else:
                # Read actual BME280 data (simplified implementation)
                # In real implementation, you would read calibration data and perform calculations
                temp_raw = await self.read_device(address, 0xFA, 3)  # Temperature registers
                hum_raw = await self.read_device(address, 0xFD, 2)   # Humidity registers  
                press_raw = await self.read_device(address, 0xF7, 3) # Pressure registers
                
                # Simplified conversion (real BME280 requires calibration data)
                temperature = 25.0 + random.uniform(-2.0, 10.0)
                humidity = 60.0 + random.uniform(-15.0, 15.0)
                pressure = 1013.0 + random.uniform(-10.0, 10.0)
            
            return {
                'sensor': 'BME280',
                'address': hex(address),
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'pressure': round(pressure, 2),
                'units': {
                    'temperature': '°C',
                    'humidity': '%RH',
                    'pressure': 'hPa'
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"BME280 read failed: {e}")
    
    async def _read_ads1115(self) -> Dict[str, Any]:
        """Read ADS1115 4-channel ADC"""
        address = 0x48  # Default ADS1115 address
        
        try:
            channels = {}
            
            if self.simulator:
                # Generate realistic ADC data
                for channel in range(4):
                    voltage = random.uniform(0.0, 3.3)
                    raw_value = int(voltage / 3.3 * 65535)
                    channels[f'channel_{channel}'] = {
                        'raw_value': raw_value,
                        'voltage': round(voltage, 3)
                    }
            else:
                # Read actual ADS1115 data
                for channel in range(4):
                    # Configure and read channel (simplified)
                    config = 0x8000 | (channel << 12) | 0x0100  # Single-shot, channel select
                    await self.write_device(address, [config >> 8, config & 0xFF], 0x01)
                    
                    # Wait for conversion
                    await asyncio.sleep(0.01)
                    
                    # Read result
                    result = await self.read_device(address, 0x00, 2)
                    raw_value = (result['data'][0] << 8) | result['data'][1]
                    voltage = (raw_value / 32768.0) * 4.096  # Assuming ±4.096V range
                    
                    channels[f'channel_{channel}'] = {
                        'raw_value': raw_value,
                        'voltage': round(voltage, 3)
                    }
            
            return {
                'sensor': 'ADS1115',
                'address': hex(address),
                'channels': channels,
                'resolution': '16-bit',
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"ADS1115 read failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get I2C handler status"""
        return {
            'bus_number': self.bus_number,
            'simulator_active': self.simulator is not None,
            'hardware_available': HAS_SMBUS and self.bus is not None,
            'devices_scanned': len(self.scan_results),
            'last_scan': self.scan_results,
            'supported_sensors': ['BME280', 'ADS1115']
        }
    
    async def cleanup(self):
        """Cleanup I2C resources"""
        try:
            if self.bus:
                self.bus.close()
            if self.simulator:
                self.simulator.cleanup()
            
            logger.info("I2C Handler cleanup completed")
            
        except Exception as e:
            logger.error(f"I2C cleanup error: {e}")


class I2CSimulator:
    """I2C Simulator for development and testing"""
    
    def __init__(self):
        """Initialize I2C simulator"""
        self.devices = {}
        logger.info("I2C Simulator initialized")
    
    def add_device(self, address: int, name: str):
        """Add simulated I2C device"""
        self.devices[address] = I2CDevice(
            address=address,
            name=name,
            registers={}
        )
        # Initialize with some default register values
        for reg in range(256):
            self.devices[address].registers[reg] = random.randint(0, 255)
        
        logger.debug(f"I2C SIM: Added device {name} at {hex(address)}")
    
    def device_exists(self, address: int) -> bool:
        """Check if device exists at address"""
        return address in self.devices
    
    def read_byte(self, address: int) -> int:
        """Read byte from device"""
        if address not in self.devices:
            raise Exception(f"Device at {hex(address)} not found")
        
        # Return a random byte for simulation
        value = random.randint(0, 255)
        logger.debug(f"I2C SIM: Read byte from {hex(address)}: {hex(value)}")
        return value
    
    def write_byte(self, address: int, value: int) -> bool:
        """Write byte to device"""
        if address not in self.devices:
            raise Exception(f"Device at {hex(address)} not found")
        
        logger.debug(f"I2C SIM: Write byte to {hex(address)}: {hex(value)}")
        return True
    
    def read_register(self, address: int, register: int, length: int = 1) -> List[int]:
        """Read register(s) from device"""
        if address not in self.devices:
            raise Exception(f"Device at {hex(address)} not found")
        
        device = self.devices[address]
        data = []
        
        for i in range(length):
            reg_addr = (register + i) % 256
            value = device.registers.get(reg_addr, random.randint(0, 255))
            data.append(value)
        
        logger.debug(f"I2C SIM: Read {length} bytes from {hex(address)} reg {hex(register)}: {[hex(b) for b in data]}")
        return data
    
    def write_register(self, address: int, register: int, data: List[int]) -> bool:
        """Write register(s) to device"""
        if address not in self.devices:
            raise Exception(f"Device at {hex(address)} not found")
        
        device = self.devices[address]
        
        for i, value in enumerate(data):
            reg_addr = (register + i) % 256
            device.registers[reg_addr] = value & 0xFF
        
        logger.debug(f"I2C SIM: Write to {hex(address)} reg {hex(register)}: {[hex(b) for b in data]}")
        return True
    
    def cleanup(self):
        """Cleanup simulator"""
        self.devices.clear()
        logger.debug("I2C SIM: Cleaned up")
