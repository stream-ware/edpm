"""
RS485/Modbus Protocol Handler with USB adapter support
Supports: Modbus RTU, Modbus ASCII, custom protocols
"""
import asyncio
import struct
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger('RS485')

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
    coils: Dict[int, bool]  # Discrete outputs
    discrete_inputs: Dict[int, bool]  # Discrete inputs
    holding_registers: Dict[int, int]  # Read/Write registers
    input_registers: Dict[int, int]  # Read-only registers

class RS485Handler:
    """RS485/Modbus Protocol Handler"""
    
    def __init__(self, 
                 port: str = "/dev/ttyUSB0",
                 baudrate: int = 9600,
                 simulator: bool = False):
        self.port = port
        self.baudrate = baudrate
        self.simulator = simulator
        self.serial = None
        self.devices = {}
        
        # Modbus settings
        self.timeout = 1.0
        
        if not simulator:
            try:
                import serial
                self.serial_lib = serial
                self.serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    parity=serial.PARITY_EVEN,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=self.timeout
                )
                logger.info(f"RS485 initialized on {port} at {baudrate} baud")
            except Exception as e:
                logger.warning(f"Serial port error: {e}, using simulator")
                self.simulator = True
        
        if self.simulator:
            self._init_simulator()
    
    def _init_simulator(self):
        """Initialize RS485 simulator with virtual devices"""
        logger.info("RS485/Modbus Simulator initialized")
        
        # Simulate temperature controller
        self.devices[1] = ModbusDevice(
            slave_id=1,
            name="Temperature Controller",
            coils={i: False for i in range(16)},  # Outputs
            discrete_inputs={i: False for i in range(16)},  # Inputs
            holding_registers={  # Read/Write registers
                0: 250,  # Setpoint (25.0°C * 10)
                1: 245,  # Current temp (24.5°C * 10)
                2: 50,   # Output %
                3: 1,    # Status (1=running)
                4: 0,    # Alarms
            },
            input_registers={  # Read-only registers
                0: 245,  # Temperature sensor 1
                1: 246,  # Temperature sensor 2
                2: 50,   # Humidity
                3: 1013, # Pressure
            }
        )
        
        # Simulate power meter
        self.devices[2] = ModbusDevice(
            slave_id=2,
            name="Power Meter",
            coils={i: False for i in range(8)},
            discrete_inputs={i: False for i in range(8)},
            holding_registers={
                0: 2300,  # Voltage (230.0V * 10)
                1: 150,   # Current (15.0A * 10)
                2: 3450,  # Power (3.45kW * 1000)
                3: 980,   # Power factor (0.98 * 1000)
            },
            input_registers={
                0: 2300,  # Voltage L1
                1: 2305,  # Voltage L2
                2: 2295,  # Voltage L3
                3: 150,   # Current L1
                4: 148,   # Current L2
                5: 152,   # Current L3
            }
        )
        
        # Simulate VFD (Variable Frequency Drive)
        self.devices[3] = ModbusDevice(
            slave_id=3,
            name="VFD Motor Controller",
            coils={
                0: False,  # Start/Stop
                1: False,  # Forward/Reverse
                2: False,  # Local/Remote
            },
            discrete_inputs={
                0: False,  # Running status
                1: False,  # Fault status
                2: True,   # Ready status
            },
            holding_registers={
                0: 5000,  # Frequency setpoint (50.00Hz * 100)
                1: 4980,  # Actual frequency (49.80Hz * 100)
                2: 750,   # Motor speed (750 RPM)
                3: 50,    # Speed reference %
                4: 0,     # Fault code
            },
            input_registers={
                0: 4980,  # Output frequency
                1: 2300,  # Motor voltage
                2: 125,   # Motor current
                3: 2800,  # Motor power (2.8kW)
                4: 750,   # Motor speed
            }
        )
    
    def _calculate_crc16(self, data: bytes) -> int:
        """Calculate Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _build_modbus_frame(self, slave_id: int, function: int, data: bytes) -> bytes:
        """Build Modbus RTU frame with CRC"""
        frame = struct.pack('BB', slave_id, function) + data
        crc = self._calculate_crc16(frame)
        frame += struct.pack('<H', crc)  # Little endian CRC
        return frame
    
    def _parse_modbus_frame(self, frame: bytes) -> Tuple[int, int, bytes, bool]:
        """Parse Modbus RTU frame and verify CRC"""
        if len(frame) < 4:
            return 0, 0, b'', False
        
        slave_id = frame[0]
        function = frame[1]
        data = frame[2:-2]
        received_crc = struct.unpack('<H', frame[-2:])[0]
        
        calculated_crc = self._calculate_crc16(frame[:-2])
        crc_valid = received_crc == calculated_crc
        
        return slave_id, function, data, crc_valid
    
    def read_coils(self, slave_id: int, address: int, count: int) -> List[bool]:
        """Read coils (discrete outputs) - Function 0x01"""
        if self.simulator:
            if slave_id in self.devices:
                device = self.devices[slave_id]
                result = []
                for i in range(count):
                    coil_addr = address + i
                    result.append(device.coils.get(coil_addr, False))
                logger.debug(f"Read {count} coils from device {slave_id} starting at {address}")
                return result
            else:
                raise Exception(f"Device {slave_id} not found")
        
        # Real Modbus communication
        data = struct.pack('>HH', address, count)
        frame = self._build_modbus_frame(slave_id, ModbusFunction.READ_COILS.value, data)
        
        self.serial.write(frame)
        response = self.serial.read(100)  # Read up to 100 bytes
        
        slave, func, resp_data, crc_ok = self._parse_modbus_frame(response)
        if not crc_ok:
            raise Exception("CRC error in response")
        
        byte_count = resp_data[0]
        coil_bytes = resp_data[1:1+byte_count]
        
        # Unpack bits
        result = []
        for i in range(count):
            byte_idx = i // 8
            bit_idx = i % 8
            if byte_idx < len(coil_bytes):
                result.append(bool(coil_bytes[byte_idx] & (1 << bit_idx)))
            else:
                result.append(False)
        
        return result
    
    def write_single_coil(self, slave_id: int, address: int, value: bool):
        """Write single coil - Function 0x05"""
        if self.simulator:
            if slave_id in self.devices:
                self.devices[slave_id].coils[address] = value
                logger.debug(f"Write coil {address} = {value} on device {slave_id}")
                
                # Simulate device behavior
                if slave_id == 3 and address == 0:  # VFD start/stop
                    self.devices[3].discrete_inputs[0] = value  # Running status
                return
            else:
                raise Exception(f"Device {slave_id} not found")
        
        # Real Modbus communication
        coil_value = 0xFF00 if value else 0x0000
        data = struct.pack('>HH', address, coil_value)
        frame = self._build_modbus_frame(slave_id, ModbusFunction.WRITE_SINGLE_COIL.value, data)
        
        self.serial.write(frame)
        response = self.serial.read(8)  # Fixed response length
        
        slave, func, resp_data, crc_ok = self._parse_modbus_frame(response)
        if not crc_ok:
            raise Exception("CRC error in response")
    
    def read_holding_registers(self, slave_id: int, address: int, count: int) -> List[int]:
        """Read holding registers - Function 0x03"""
        if self.simulator:
            if slave_id in self.devices:
                device = self.devices[slave_id]
                result = []
                for i in range(count):
                    reg_addr = address + i
                    value = device.holding_registers.get(reg_addr, 0)
                    
                    # Add some variation to simulate real devices
                    if slave_id == 1 and reg_addr == 1:  # Temperature
                        value += random.randint(-5, 5)
                    elif slave_id == 2 and reg_addr in [1, 2]:  # Power meter
                        value += random.randint(-10, 10)
                    elif slave_id == 3 and reg_addr == 1:  # VFD actual frequency
                        value += random.randint(-20, 20)
                    
                    result.append(max(0, min(65535, value)))  # Clamp to 16-bit
                
                logger.debug(f"Read {count} registers from device {slave_id} starting at {address}")
                return result
            else:
                raise Exception(f"Device {slave_id} not found")
        
        # Real Modbus communication
        data = struct.pack('>HH', address, count)
        frame = self._build_modbus_frame(slave_id, ModbusFunction.READ_HOLDING_REGISTERS.value, data)
        
        self.serial.write(frame)
        response = self.serial.read(100)
        
        slave, func, resp_data, crc_ok = self._parse_modbus_frame(response)
        if not crc_ok:
            raise Exception("CRC error in response")
        
        byte_count = resp_data[0]
        reg_bytes = resp_data[1:1+byte_count]
        
        # Unpack 16-bit registers (big endian)
        result = []
        for i in range(0, len(reg_bytes), 2):
            if i+1 < len(reg_bytes):
                value = struct.unpack('>H', reg_bytes[i:i+2])[0]
                result.append(value)
        
        return result
    
    def write_single_register(self, slave_id: int, address: int, value: int):
        """Write single register - Function 0x06"""
        if self.simulator:
            if slave_id in self.devices:
                self.devices[slave_id].holding_registers[address] = value
                logger.debug(f"Write register {address} = {value} on device {slave_id}")
                
                # Simulate device behavior
                if slave_id == 3 and address == 0:  # VFD frequency setpoint
                    # Update actual frequency with some lag
                    self.devices[3].holding_registers[1] = int(value * 0.99)
                return
            else:
                raise Exception(f"Device {slave_id} not found")
        
        # Real Modbus communication
        data = struct.pack('>HH', address, value)
        frame = self._build_modbus_frame(slave_id, ModbusFunction.WRITE_SINGLE_REGISTER.value, data)
        
        self.serial.write(frame)
        response = self.serial.read(8)
        
        slave, func, resp_data, crc_ok = self._parse_modbus_frame(response)
        if not crc_ok:
            raise Exception("CRC error in response")
    
    def scan_devices(self, max_address: int = 247) -> List[int]:
        """Scan for Modbus devices"""
        if self.simulator:
            return list(self.devices.keys())
        
        found_devices = []
        for addr in range(1, min(max_address + 1, 248)):
            try:
                # Try to read one register
                self.read_holding_registers(addr, 0, 1)
                found_devices.append(addr)
                logger.info(f"Found Modbus device at address {addr}")
            except:
                pass  # Device not responding
            
            time.sleep(0.01)  # Small delay between scans
        
        return found_devices
    
    def get_device_info(self, slave_id: int) -> Dict:
        """Get information about a specific device"""
        if self.simulator and slave_id in self.devices:
            device = self.devices[slave_id]
            return {
                "slave_id": slave_id,
                "name": device.name,
                "coils": len(device.coils),
                "discrete_inputs": len(device.discrete_inputs),
                "holding_registers": len(device.holding_registers),
                "input_registers": len(device.input_registers)
            }
        return {"slave_id": slave_id, "name": f"Device {slave_id}"}
    
    async def continuous_monitoring(self, callback, devices: List[int] = None, interval: float = 1.0):
        """Start continuous monitoring of RS485/Modbus devices"""
        if devices is None:
            devices = list(self.devices.keys()) if self.simulator else self.scan_devices()
        
        while True:
            try:
                for slave_id in devices:
                    data = {"slave_id": slave_id}
                    
                    try:
                        # Read some key registers from each device
                        if slave_id == 1:  # Temperature controller
                            regs = self.read_holding_registers(slave_id, 0, 5)
                            data.update({
                                "setpoint": regs[0] / 10.0,
                                "temperature": regs[1] / 10.0,
                                "output_percent": regs[2],
                                "status": regs[3],
                                "alarms": regs[4]
                            })
                        elif slave_id == 2:  # Power meter
                            regs = self.read_holding_registers(slave_id, 0, 4)
                            data.update({
                                "voltage": regs[0] / 10.0,
                                "current": regs[1] / 10.0,
                                "power": regs[2] / 1000.0,
                                "power_factor": regs[3] / 1000.0
                            })
                        elif slave_id == 3:  # VFD
                            regs = self.read_holding_registers(slave_id, 0, 5)
                            coils = self.read_coils(slave_id, 0, 3)
                            data.update({
                                "frequency_setpoint": regs[0] / 100.0,
                                "frequency_actual": regs[1] / 100.0,
                                "motor_speed": regs[2],
                                "speed_reference": regs[3],
                                "fault_code": regs[4],
                                "running": coils[0],
                                "forward": coils[1]
                            })
                        
                        await callback(data)
                        
                    except Exception as e:
                        logger.error(f"Error reading device {slave_id}: {e}")
                        data["error"] = str(e)
                        await callback(data)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"RS485 monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def __del__(self):
        """Cleanup serial connection"""
        if self.serial and hasattr(self.serial, 'close'):
            self.serial.close()
