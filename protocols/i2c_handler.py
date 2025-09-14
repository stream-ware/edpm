"""
I2C Protocol Handler with simulator support
Supports: BME280, BMP280, ADS1115, PCF8574, DS3231, etc.
"""
import asyncio
import struct
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger('I2C')

@dataclass
class I2CDevice:
    """I2C Device representation"""
    address: int
    name: str
    registers: Dict[int, int]
    read_only: List[int]
    write_only: List[int]

class I2CHandler:
    """I2C Protocol Handler with simulation support"""
    
    # Common I2C device addresses
    DEVICES = {
        0x76: "BME280",  # Temperature, Humidity, Pressure
        0x77: "BMP280",  # Temperature, Pressure
        0x48: "ADS1115", # 16-bit ADC
        0x20: "PCF8574", # GPIO Expander
        0x68: "DS3231",  # RTC
        0x3C: "SSD1306", # OLED Display
        0x27: "LCD1602", # LCD Display
    }
    
    def __init__(self, bus_number: int = 1, simulator: bool = False):
        self.bus_number = bus_number
        self.simulator = simulator
        self.bus = None
        self.devices = {}
        self.scan_results = []
        
        if not simulator:
            try:
                import smbus2
                self.bus = smbus2.SMBus(bus_number)
                logger.info(f"I2C bus {bus_number} initialized")
            except ImportError:
                logger.warning("smbus2 not found, using simulator")
                self.simulator = True
        
        if self.simulator:
            self._init_simulator()
    
    def _init_simulator(self):
        """Initialize I2C simulator with virtual devices"""
        logger.info("I2C Simulator initialized")
        
        # Simulate BME280 sensor
        self.devices[0x76] = I2CDevice(
            address=0x76,
            name="BME280",
            registers={
                0xD0: 0x60,  # Chip ID
                0xF7: 0x80,  # Pressure MSB
                0xF8: 0x00,  # Pressure LSB
                0xF9: 0x00,  # Pressure XLSB
                0xFA: 0x80,  # Temperature MSB
                0xFB: 0x00,  # Temperature LSB
                0xFC: 0x00,  # Temperature XLSB
                0xFD: 0x80,  # Humidity MSB
                0xFE: 0x00,  # Humidity LSB
            },
            read_only=[0xD0, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE],
            write_only=[]
        )
        
        # Simulate ADS1115 ADC
        self.devices[0x48] = I2CDevice(
            address=0x48,
            name="ADS1115",
            registers={
                0x00: 0x8000,  # Conversion register
                0x01: 0x0000,  # Config register
                0x02: 0x8000,  # Lo_thresh register
                0x03: 0x7FFF,  # Hi_thresh register
            },
            read_only=[0x00],
            write_only=[]
        )
        
        self.scan_results = list(self.devices.keys())
    
    def scan(self) -> List[int]:
        """Scan I2C bus for devices"""
        if self.simulator:
            return self.scan_results
        
        devices = []
        for addr in range(0x03, 0x78):
            try:
                self.bus.read_byte(addr)
                devices.append(addr)
            except:
                pass
        return devices
    
    def read_byte(self, address: int, register: int) -> int:
        """Read single byte from I2C device"""
        if self.simulator:
            if address in self.devices and register in self.devices[address].registers:
                value = self.devices[address].registers[register]
                # Add some realistic sensor variation
                if address == 0x76:  # BME280
                    if register in [0xFA, 0xFB, 0xFC]:  # Temperature
                        value += random.randint(-5, 5)
                    elif register in [0xFD, 0xFE]:  # Humidity
                        value += random.randint(-10, 10)
                return value & 0xFF
            else:
                raise IOError(f"Device 0x{address:02X} register 0x{register:02X} not found")
        
        return self.bus.read_byte_data(address, register)
    
    def write_byte(self, address: int, register: int, value: int):
        """Write single byte to I2C device"""
        if self.simulator:
            if address in self.devices:
                if register not in self.devices[address].read_only:
                    self.devices[address].registers[register] = value
                    logger.debug(f"I2C Write: 0x{address:02X}[0x{register:02X}] = 0x{value:02X}")
                else:
                    raise IOError(f"Register 0x{register:02X} is read-only")
            else:
                raise IOError(f"Device 0x{address:02X} not found")
            return
        
        self.bus.write_byte_data(address, register, value)
    
    def read_word(self, address: int, register: int) -> int:
        """Read 16-bit word from I2C device"""
        if self.simulator:
            msb = self.read_byte(address, register)
            lsb = self.read_byte(address, register + 1)
            return (msb << 8) | lsb
        
        return self.bus.read_word_data(address, register)
    
    def read_bme280(self, address: int = 0x76) -> Dict[str, float]:
        """Read BME280 sensor data (simplified)"""
        try:
            # Check chip ID
            chip_id = self.read_byte(address, 0xD0)
            if chip_id != 0x60:
                raise ValueError(f"Invalid BME280 chip ID: 0x{chip_id:02X}")
            
            if self.simulator:
                # Simulate realistic sensor values with some variation
                temp = 20.0 + random.uniform(-5, 15)  # 15-35°C
                humidity = 45.0 + random.uniform(-15, 25)  # 30-70%
                pressure = 1013.25 + random.uniform(-50, 50)  # ±50 hPa
                
                return {
                    'temperature': round(temp, 2),
                    'humidity': round(humidity, 1),
                    'pressure': round(pressure, 2)
                }
            
            # Real BME280 reading would need calibration coefficients
            # This is a simplified version
            temp_raw = self.read_word(address, 0xFA) >> 4
            humidity_raw = self.read_word(address, 0xFD)
            pressure_raw = self.read_word(address, 0xF7) >> 4
            
            # Convert to physical values (simplified)
            temperature = temp_raw / 100.0  # Simplified conversion
            humidity = humidity_raw / 1024.0  # Simplified conversion
            pressure = pressure_raw / 256.0   # Simplified conversion
            
            return {
                'temperature': temperature,
                'humidity': humidity, 
                'pressure': pressure
            }
            
        except Exception as e:
            logger.error(f"BME280 read error: {e}")
            return {'temperature': 0, 'humidity': 0, 'pressure': 0}
    
    def read_ads1115(self, address: int = 0x48, channel: int = 0) -> float:
        """Read ADS1115 ADC value"""
        try:
            if self.simulator:
                # Simulate ADC readings for different channels
                base_values = [2.45, 1.23, 3.78, 0.89]  # Different voltages per channel
                variation = random.uniform(-0.1, 0.1)
                return base_values[channel % 4] + variation
            
            # Configure for single-shot mode, channel selection
            config = 0x8000 | (channel << 12) | 0x0100  # Single-shot, channel, gain=1
            self.write_byte(address, 0x01, config >> 8)
            self.write_byte(address, 0x01, config & 0xFF)
            
            # Wait for conversion
            time.sleep(0.01)
            
            # Read conversion result
            result = self.read_word(address, 0x00)
            voltage = (result / 32767.0) * 4.096  # FS = 4.096V for gain=1
            
            return voltage
            
        except Exception as e:
            logger.error(f"ADS1115 read error: {e}")
            return 0.0
    
    async def continuous_monitoring(self, callback, interval: float = 1.0):
        """Start continuous monitoring of all I2C devices"""
        while True:
            try:
                # Read all available sensors
                data = {}
                
                if 0x76 in self.devices:  # BME280
                    bme_data = self.read_bme280(0x76)
                    data.update(bme_data)
                
                if 0x48 in self.devices:  # ADS1115
                    for ch in range(4):
                        voltage = self.read_ads1115(0x48, ch)
                        data[f'adc_ch{ch}'] = voltage
                
                # Call the callback with sensor data
                await callback(data)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"I2C monitoring error: {e}")
                await asyncio.sleep(interval)
