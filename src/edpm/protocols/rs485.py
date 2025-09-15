"""
EDPM RS485/Modbus Protocol Handler
RS485 communication with Modbus RTU support and VFD control capabilities.
"""

import asyncio
import struct
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from ..core.config import Config

# Optional serial dependencies
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    serial = None

logger = logging.getLogger(__name__)


class ModbusFunction(Enum):
    """Modbus function codes"""
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10


@dataclass
class ModbusDevice:
    """Modbus device representation"""
    slave_id: int
    name: str
    coils: Dict[int, bool] = None  # Discrete outputs
    discrete_inputs: Dict[int, bool] = None  # Discrete inputs
    holding_registers: Dict[int, int] = None  # Read/Write registers
    input_registers: Dict[int, int] = None  # Read-only registers
    
    def __post_init__(self):
        if self.coils is None:
            self.coils = {}
        if self.discrete_inputs is None:
            self.discrete_inputs = {}
        if self.holding_registers is None:
            self.holding_registers = {}
        if self.input_registers is None:
            self.input_registers = {}


class RS485Handler:
    """
    RS485/Modbus Protocol Handler
    
    Handles RS485 communication with support for Modbus RTU protocol,
    VFD (Variable Frequency Drive) control, and power monitoring.
    Includes simulator mode for development and testing.
    """
    
    def __init__(self, config: Config = None):
        """Initialize RS485 Handler"""
        self.config = config or Config.from_env()
        self.port = "/dev/ttyUSB0"  # Default RS485 port
        self.baudrate = 9600
        self.bytesize = 8
        self.parity = 'N'
        self.stopbits = 1
        self.timeout = 1.0
        
        # Connection state
        self.serial_connection = None
        self.simulator = None
        self.devices = {}
        
        # Initialize RS485 based on configuration
        if self.config.rs485_simulator:
            self._init_simulator()
        elif HAS_SERIAL:
            self._init_hardware()
        else:
            logger.warning("pySerial not available, using simulator")
            self._init_simulator()
        
        logger.info(f"RS485 Handler initialized - Port: {self.port}, Baud: {self.baudrate}, Simulator: {self.simulator is not None}")
    
    def _init_simulator(self):
        """Initialize RS485 simulator"""
        self.simulator = RS485Simulator()
        # Pre-populate with common devices
        self.simulator.add_device(1, "VFD_Motor_1")
        self.simulator.add_device(2, "Power_Meter_1")
        self.simulator.add_device(3, "Temperature_Controller_1")
    
    def _init_hardware(self):
        """Initialize RS485 hardware"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            logger.info(f"RS485 hardware initialized on {self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize RS485 hardware: {e}")
            logger.warning("Falling back to simulator")
            self._init_simulator()
    
    async def handle_command(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle RS485 command
        
        Args:
            action: RS485 action to perform
            data: Command parameters
            
        Returns:
            Result dictionary
        """
        try:
            if action == "modbus_read":
                return await self.modbus_read(
                    data.get("device_id"),
                    data.get("function_code", ModbusFunction.READ_HOLDING_REGISTERS),
                    data.get("start_address", 0),
                    data.get("count", 1)
                )
            elif action == "modbus_write":
                return await self.modbus_write(
                    data.get("device_id"),
                    data.get("function_code", ModbusFunction.WRITE_SINGLE_REGISTER),
                    data.get("address"),
                    data.get("value")
                )
            elif action == "set_vfd_speed":
                return await self.set_vfd_speed(
                    data.get("device_id", 1),
                    data.get("speed")
                )
            elif action == "start_vfd":
                return await self.start_vfd(data.get("device_id", 1))
            elif action == "stop_vfd":
                return await self.stop_vfd(data.get("device_id", 1))
            elif action == "read_power_meter":
                return await self.read_power_meter(data.get("device_id", 2))
            elif action == "scan_devices":
                return await self.scan_devices(
                    data.get("start_id", 1),
                    data.get("end_id", 10)
                )
            elif action == "rs485_status":
                return await self.get_status()
            elif action == "list_serial_ports":
                return await self.list_serial_ports()
            else:
                raise ValueError(f"Unknown RS485 action: {action}")
                
        except Exception as e:
            logger.error(f"RS485 command error: {e}")
            raise
    
    async def modbus_read(self, device_id: int, function_code: Union[ModbusFunction, int], 
                         start_address: int, count: int = 1) -> Dict[str, Any]:
        """Read from Modbus device"""
        if device_id is None:
            raise ValueError("Device ID required")
        if start_address is None:
            raise ValueError("Start address required")
        
        try:
            # Convert function code to int if needed
            if isinstance(function_code, ModbusFunction):
                func_code = function_code.value
            else:
                func_code = int(function_code)
            
            if self.simulator:
                data = self.simulator.modbus_read(device_id, func_code, start_address, count)
            else:
                data = await self._hardware_modbus_read(device_id, func_code, start_address, count)
            
            return {
                'device_id': device_id,
                'function_code': func_code,
                'start_address': start_address,
                'count': count,
                'data': data,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Modbus read failed: {e}")
    
    async def modbus_write(self, device_id: int, function_code: Union[ModbusFunction, int], 
                          address: int, value: Union[int, List[int]]) -> Dict[str, Any]:
        """Write to Modbus device"""
        if device_id is None:
            raise ValueError("Device ID required")
        if address is None:
            raise ValueError("Address required")
        if value is None:
            raise ValueError("Value required")
        
        try:
            # Convert function code to int if needed
            if isinstance(function_code, ModbusFunction):
                func_code = function_code.value
            else:
                func_code = int(function_code)
            
            if self.simulator:
                result = self.simulator.modbus_write(device_id, func_code, address, value)
            else:
                result = await self._hardware_modbus_write(device_id, func_code, address, value)
            
            return {
                'device_id': device_id,
                'function_code': func_code,
                'address': address,
                'value': value,
                'success': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Modbus write failed: {e}")
    
    async def set_vfd_speed(self, device_id: int, speed: int) -> Dict[str, Any]:
        """Set VFD (Variable Frequency Drive) speed"""
        if device_id is None:
            raise ValueError("Device ID required")
        if speed is None:
            raise ValueError("Speed required")
        
        # Validate speed range (0-100%)
        speed = max(0, min(100, int(speed)))
        
        try:
            # Write to VFD speed register (typically holding register 1)
            result = await self.modbus_write(
                device_id,
                ModbusFunction.WRITE_SINGLE_REGISTER,
                1,  # Speed register
                int(speed * 655.35)  # Convert percentage to 16-bit value
            )
            
            return {
                'device_id': device_id,
                'speed_percent': speed,
                'speed_raw': int(speed * 655.35),
                'success': result['success'],
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"VFD speed set failed: {e}")
    
    async def start_vfd(self, device_id: int) -> Dict[str, Any]:
        """Start VFD motor"""
        try:
            # Write to VFD control register (typically holding register 0)
            result = await self.modbus_write(
                device_id,
                ModbusFunction.WRITE_SINGLE_REGISTER,
                0,  # Control register
                1   # Start command
            )
            
            return {
                'device_id': device_id,
                'command': 'start',
                'success': result['success'],
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"VFD start failed: {e}")
    
    async def stop_vfd(self, device_id: int) -> Dict[str, Any]:
        """Stop VFD motor"""
        try:
            # Write to VFD control register
            result = await self.modbus_write(
                device_id,
                ModbusFunction.WRITE_SINGLE_REGISTER,
                0,  # Control register
                0   # Stop command
            )
            
            return {
                'device_id': device_id,
                'command': 'stop',
                'success': result['success'],
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"VFD stop failed: {e}")
    
    async def read_power_meter(self, device_id: int) -> Dict[str, Any]:
        """Read power meter data"""
        try:
            # Read multiple registers from power meter
            voltage_result = await self.modbus_read(device_id, ModbusFunction.READ_HOLDING_REGISTERS, 10, 1)
            current_result = await self.modbus_read(device_id, ModbusFunction.READ_HOLDING_REGISTERS, 11, 1)
            power_result = await self.modbus_read(device_id, ModbusFunction.READ_HOLDING_REGISTERS, 12, 1)
            energy_result = await self.modbus_read(device_id, ModbusFunction.READ_HOLDING_REGISTERS, 13, 1)
            
            # Convert raw values to real units (simplified conversion)
            voltage = voltage_result['data'][0] / 10.0  # Voltage in V
            current = current_result['data'][0] / 100.0  # Current in A
            power = power_result['data'][0]  # Power in W
            energy = energy_result['data'][0] / 10.0  # Energy in kWh
            
            return {
                'device_id': device_id,
                'voltage': round(voltage, 2),
                'current': round(current, 3),
                'power': power,
                'energy': round(energy, 2),
                'power_factor': round(power / (voltage * current) if voltage * current > 0 else 0.0, 2),
                'units': {
                    'voltage': 'V',
                    'current': 'A',
                    'power': 'W',
                    'energy': 'kWh',
                    'power_factor': ''
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Power meter read failed: {e}")
    
    async def scan_devices(self, start_id: int = 1, end_id: int = 10) -> Dict[str, Any]:
        """Scan for Modbus devices"""
        devices_found = []
        
        try:
            for device_id in range(start_id, end_id + 1):
                try:
                    # Try to read holding register 0 from device
                    result = await self.modbus_read(
                        device_id, 
                        ModbusFunction.READ_HOLDING_REGISTERS, 
                        0, 
                        1
                    )
                    
                    if result and 'data' in result:
                        device_type = "Unknown"
                        if device_id == 1:
                            device_type = "VFD"
                        elif device_id == 2:
                            device_type = "Power Meter"
                        elif device_id == 3:
                            device_type = "Temperature Controller"
                        
                        devices_found.append({
                            'device_id': device_id,
                            'type': device_type,
                            'responsive': True,
                            'first_register_value': result['data'][0]
                        })
                        
                except:
                    # Device not responsive
                    continue
            
            return {
                'devices_found': len(devices_found),
                'devices': devices_found,
                'scan_range': f"{start_id}-{end_id}",
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Device scan failed: {e}")
    
    async def list_serial_ports(self) -> Dict[str, Any]:
        """List available serial ports"""
        ports = []
        
        try:
            if HAS_SERIAL:
                available_ports = serial.tools.list_ports.comports()
                for port in available_ports:
                    ports.append({
                        'device': port.device,
                        'name': port.name,
                        'description': port.description,
                        'hwid': port.hwid
                    })
            else:
                # Simulator mode
                ports = [
                    {'device': '/dev/ttyUSB0', 'name': 'USB Serial', 'description': 'Simulated RS485 Port'},
                    {'device': '/dev/ttyUSB1', 'name': 'USB Serial', 'description': 'Simulated RS485 Port'}
                ]
            
            return {
                'ports': ports,
                'count': len(ports)
            }
            
        except Exception as e:
            raise Exception(f"Failed to list serial ports: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get RS485 handler status"""
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'bytesize': self.bytesize,
            'parity': self.parity,
            'stopbits': self.stopbits,
            'timeout': self.timeout,
            'simulator_active': self.simulator is not None,
            'hardware_available': HAS_SERIAL and self.serial_connection is not None,
            'connection_open': self.serial_connection.is_open if self.serial_connection else False,
            'devices_configured': len(self.devices),
            'supported_functions': [func.name for func in ModbusFunction]
        }
    
    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    
    async def _hardware_modbus_read(self, device_id: int, function_code: int, 
                                  start_address: int, count: int) -> List[int]:
        """Read from hardware Modbus device"""
        try:
            # Build Modbus RTU request
            request = struct.pack('>BBHH', device_id, function_code, start_address, count)
            crc = self._calculate_crc16(request)
            request += struct.pack('<H', crc)
            
            # Send request
            self.serial_connection.write(request)
            
            # Read response
            response = self.serial_connection.read(1000)  # Read with timeout
            
            if len(response) < 5:
                raise Exception("Invalid response length")
            
            # Parse response (simplified)
            resp_device_id, resp_func_code, byte_count = struct.unpack('>BBB', response[:3])
            
            if resp_device_id != device_id or resp_func_code != function_code:
                raise Exception("Response mismatch")
            
            # Extract data
            data = []
            for i in range(count):
                if i * 2 + 4 < len(response):
                    value = struct.unpack('>H', response[3 + i * 2:5 + i * 2])[0]
                    data.append(value)
            
            return data
            
        except Exception as e:
            logger.error(f"Hardware Modbus read error: {e}")
            raise
    
    async def _hardware_modbus_write(self, device_id: int, function_code: int, 
                                   address: int, value: Union[int, List[int]]) -> bool:
        """Write to hardware Modbus device"""
        try:
            if isinstance(value, int):
                # Single register write
                request = struct.pack('>BBHH', device_id, function_code, address, value)
            else:
                # Multiple registers write (simplified)
                request = struct.pack('>BBHH', device_id, function_code, address, len(value))
                for v in value:
                    request += struct.pack('>H', v)
            
            crc = self._calculate_crc16(request)
            request += struct.pack('<H', crc)
            
            # Send request
            self.serial_connection.write(request)
            
            # Read response
            response = self.serial_connection.read(100)
            
            # Validate response (simplified)
            return len(response) >= 6  # Minimum valid response
            
        except Exception as e:
            logger.error(f"Hardware Modbus write error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup RS485 resources"""
        try:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            if self.simulator:
                self.simulator.cleanup()
            
            logger.info("RS485 Handler cleanup completed")
            
        except Exception as e:
            logger.error(f"RS485 cleanup error: {e}")


class RS485Simulator:
    """RS485/Modbus Simulator for development and testing"""
    
    def __init__(self):
        """Initialize RS485 simulator"""
        self.devices = {}
        logger.info("RS485 Simulator initialized")
    
    def add_device(self, device_id: int, name: str):
        """Add simulated Modbus device"""
        device = ModbusDevice(slave_id=device_id, name=name)
        
        # Initialize with realistic data based on device type
        if "VFD" in name:
            device.holding_registers[0] = 0  # Control register (stopped)
            device.holding_registers[1] = 0  # Speed register (0%)
            device.holding_registers[2] = random.randint(0, 1000)  # Status
        elif "Power" in name:
            device.holding_registers[10] = random.randint(2200, 2400)  # Voltage * 10
            device.holding_registers[11] = random.randint(50, 200)    # Current * 100
            device.holding_registers[12] = random.randint(1000, 5000) # Power (W)
            device.holding_registers[13] = random.randint(100, 1000)  # Energy * 10
        else:
            # Generic device
            for i in range(10):
                device.holding_registers[i] = random.randint(0, 65535)
        
        self.devices[device_id] = device
        logger.debug(f"RS485 SIM: Added device {name} (ID: {device_id})")
    
    def modbus_read(self, device_id: int, function_code: int, start_address: int, count: int) -> List[int]:
        """Simulate Modbus read operation"""
        if device_id not in self.devices:
            raise Exception(f"Device {device_id} not found")
        
        device = self.devices[device_id]
        data = []
        
        if function_code == ModbusFunction.READ_HOLDING_REGISTERS.value:
            for i in range(count):
                addr = start_address + i
                value = device.holding_registers.get(addr, 0)
                # Add some realistic variation for certain registers
                if "VFD" in device.name and addr == 2:  # Status register
                    value += random.randint(-10, 10)
                elif "Power" in device.name:
                    value += random.randint(-5, 5)
                data.append(max(0, min(65535, value)))
        
        elif function_code == ModbusFunction.READ_INPUT_REGISTERS.value:
            for i in range(count):
                addr = start_address + i
                value = device.input_registers.get(addr, random.randint(0, 1000))
                data.append(value)
        
        elif function_code == ModbusFunction.READ_COILS.value:
            for i in range(count):
                addr = start_address + i
                value = 1 if device.coils.get(addr, False) else 0
                data.append(value)
        
        else:
            # Default response
            data = [random.randint(0, 65535) for _ in range(count)]
        
        logger.debug(f"RS485 SIM: Read from device {device_id}, func {function_code}, addr {start_address}, count {count} -> {data}")
        return data
    
    def modbus_write(self, device_id: int, function_code: int, address: int, value: Union[int, List[int]]) -> bool:
        """Simulate Modbus write operation"""
        if device_id not in self.devices:
            raise Exception(f"Device {device_id} not found")
        
        device = self.devices[device_id]
        
        if function_code == ModbusFunction.WRITE_SINGLE_REGISTER.value:
            device.holding_registers[address] = int(value)
            logger.debug(f"RS485 SIM: Write to device {device_id}, reg {address} = {value}")
            
        elif function_code == ModbusFunction.WRITE_MULTIPLE_REGISTERS.value:
            if isinstance(value, list):
                for i, v in enumerate(value):
                    device.holding_registers[address + i] = int(v)
            else:
                device.holding_registers[address] = int(value)
        
        elif function_code == ModbusFunction.WRITE_SINGLE_COIL.value:
            device.coils[address] = bool(value)
        
        logger.debug(f"RS485 SIM: Write to device {device_id}, func {function_code}, addr {address}, value {value}")
        return True
    
    def cleanup(self):
        """Cleanup simulator"""
        self.devices.clear()
        logger.debug("RS485 SIM: Cleaned up")
