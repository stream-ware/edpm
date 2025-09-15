#!/usr/bin/env python3
"""
RS485/Modbus VFD Control Example for EDPM Lite
Demonstrates comprehensive VFD motor control and power monitoring using RS485/Modbus.
"""

import asyncio
import json
import time
import logging
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from edpm import EDPMClient, Config, Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VFDStatus(Enum):
    """VFD operational status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAULT = "fault"
    MAINTENANCE = "maintenance"


@dataclass
class VFDParameters:
    """VFD parameter data structure"""
    device_id: int
    name: str
    status: VFDStatus
    speed_reference: float  # Percentage 0-100
    actual_speed: float     # RPM
    output_frequency: float # Hz
    output_voltage: float   # V
    output_current: float   # A
    motor_power: float      # kW
    torque: float          # %
    temperature: float     # °C
    fault_code: int
    timestamp: float


@dataclass
class PowerMeterData:
    """Power meter measurement data"""
    device_id: int
    name: str
    voltage_l1: float      # V
    voltage_l2: float      # V
    voltage_l3: float      # V
    current_l1: float      # A
    current_l2: float      # A
    current_l3: float      # A
    active_power: float    # kW
    reactive_power: float  # kVAR
    apparent_power: float  # kVA
    power_factor: float    # -
    frequency: float       # Hz
    energy: float         # kWh
    timestamp: float


class RS485VFDController:
    """RS485/Modbus VFD Control Application"""
    
    def __init__(self, config_path: str = "config.json", devices_config_path: str = "modbus_devices.json"):
        """Initialize the RS485 VFD controller"""
        self.config_path = Path(config_path)
        self.devices_config_path = Path(devices_config_path)
        self.config = self.load_config()
        self.device_configs = self.load_device_configs()
        self.client = None
        self.running = False
        self.vfd_data = {}
        self.power_data = {}
        self.discovered_devices = []
    
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
                "rs485_settings": {
                    "port": "/dev/ttyUSB0",
                    "baudrate": 9600,
                    "parity": "N",
                    "stopbits": 1,
                    "bytesize": 8,
                    "timeout": 1.0
                },
                "modbus_scan": {
                    "start_address": 1,
                    "end_address": 10,
                    "timeout": 0.5
                },
                "vfd_control": {
                    "max_speed": 100.0,
                    "acceleration_time": 10.0,
                    "deceleration_time": 10.0,
                    "emergency_stop_enabled": True
                },
                "monitoring": {
                    "update_interval": 2.0,
                    "data_retention_hours": 24,
                    "alarm_thresholds": {
                        "motor_current": {"warning": 80, "alarm": 95},
                        "motor_temperature": {"warning": 70, "alarm": 85},
                        "power_factor": {"warning": 0.7, "alarm": 0.6}
                    }
                },
                "safety": {
                    "emergency_stop_address": 0,
                    "fault_reset_address": 1,
                    "enable_address": 2,
                    "interlock_monitoring": True
                }
            }
    
    def load_device_configs(self) -> dict:
        """Load Modbus device configurations from file"""
        if self.devices_config_path.exists():
            with open(self.devices_config_path) as f:
                return json.load(f)
        else:
            # Default device configurations
            return {
                "vfd_devices": {
                    "1": {
                        "name": "Main Motor VFD",
                        "type": "schneider_atv",
                        "rated_power": 5.5,
                        "rated_current": 12.0,
                        "rated_voltage": 380,
                        "registers": {
                            "speed_reference": {"address": 1, "type": "holding", "scale": 0.01},
                            "control_word": {"address": 0, "type": "holding"},
                            "status_word": {"address": 100, "type": "input"},
                            "actual_speed": {"address": 101, "type": "input", "scale": 0.1},
                            "output_frequency": {"address": 102, "type": "input", "scale": 0.01},
                            "output_current": {"address": 103, "type": "input", "scale": 0.01},
                            "motor_power": {"address": 104, "type": "input", "scale": 0.01},
                            "fault_code": {"address": 105, "type": "input"}
                        }
                    },
                    "2": {
                        "name": "Auxiliary Pump VFD",
                        "type": "abb_acs",
                        "rated_power": 2.2,
                        "rated_current": 5.5,
                        "rated_voltage": 380,
                        "registers": {
                            "speed_reference": {"address": 1, "type": "holding", "scale": 0.01},
                            "control_word": {"address": 0, "type": "holding"},
                            "status_word": {"address": 100, "type": "input"},
                            "actual_speed": {"address": 101, "type": "input", "scale": 0.1}
                        }
                    }
                },
                "power_meters": {
                    "10": {
                        "name": "Main Electrical Panel",
                        "type": "schneider_pm8000",
                        "registers": {
                            "voltage_l1": {"address": 200, "type": "input", "scale": 0.1},
                            "voltage_l2": {"address": 201, "type": "input", "scale": 0.1},
                            "voltage_l3": {"address": 202, "type": "input", "scale": 0.1},
                            "current_l1": {"address": 210, "type": "input", "scale": 0.001},
                            "current_l2": {"address": 211, "type": "input", "scale": 0.001},
                            "current_l3": {"address": 212, "type": "input", "scale": 0.001},
                            "active_power": {"address": 220, "type": "input", "scale": 0.001},
                            "reactive_power": {"address": 221, "type": "input", "scale": 0.001},
                            "power_factor": {"address": 222, "type": "input", "scale": 0.001}
                        }
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
    
    async def scan_modbus_devices(self) -> List[int]:
        """Scan for Modbus devices on the RS485 network"""
        logger.info("Scanning for Modbus devices...")
        await self.log_message("info", "Starting Modbus device scan")
        
        try:
            scan_config = self.config["modbus_scan"]
            
            result = await self.client.send_command("rs485", {
                "action": "scan_devices",
                "start_id": scan_config["start_address"],
                "end_id": scan_config["end_address"]
            })
            
            if result and "devices" in result:
                devices = [device["device_id"] for device in result["devices"]]
                logger.info(f"Found {len(devices)} Modbus devices: {devices}")
                await self.log_message("info", f"Found {len(devices)} Modbus devices")
                self.discovered_devices = devices
                return devices
            else:
                logger.warning("No Modbus devices found")
                return []
                
        except Exception as e:
            logger.error(f"Error scanning Modbus devices: {e}")
            await self.log_message("error", f"Modbus scan failed: {e}")
            return []
    
    async def read_vfd_parameters(self, device_id: int) -> Optional[VFDParameters]:
        """Read parameters from a VFD device"""
        try:
            device_config = self.device_configs["vfd_devices"].get(str(device_id))
            if not device_config:
                logger.warning(f"No configuration found for VFD device {device_id}")
                return None
            
            parameters = {}
            
            # Read all configured registers
            for param_name, reg_config in device_config["registers"].items():
                try:
                    if reg_config["type"] == "holding":
                        result = await self.client.send_command("rs485", {
                            "action": "modbus_read",
                            "device_id": device_id,
                            "function_code": 3,  # Read Holding Registers
                            "start_address": reg_config["address"],
                            "count": 1
                        })
                    else:  # input registers
                        result = await self.client.send_command("rs485", {
                            "action": "modbus_read",
                            "device_id": device_id,
                            "function_code": 4,  # Read Input Registers
                            "start_address": reg_config["address"],
                            "count": 1
                        })
                    
                    if result and "data" in result and result["data"]:
                        raw_value = result["data"][0]
                        # Apply scaling if configured
                        scale = reg_config.get("scale", 1.0)
                        parameters[param_name] = raw_value * scale
                    else:
                        parameters[param_name] = 0
                        
                except Exception as e:
                    logger.error(f"Error reading {param_name} from VFD {device_id}: {e}")
                    parameters[param_name] = 0
            
            # Determine VFD status based on status word
            status_word = parameters.get("status_word", 0)
            if status_word & 0x0001:  # Running bit
                status = VFDStatus.RUNNING
            elif status_word & 0x0002:  # Fault bit
                status = VFDStatus.FAULT
            elif status_word & 0x0004:  # Starting bit
                status = VFDStatus.STARTING
            else:
                status = VFDStatus.STOPPED
            
            # Create VFD parameters object
            vfd_params = VFDParameters(
                device_id=device_id,
                name=device_config["name"],
                status=status,
                speed_reference=parameters.get("speed_reference", 0),
                actual_speed=parameters.get("actual_speed", 0),
                output_frequency=parameters.get("output_frequency", 0),
                output_voltage=parameters.get("output_voltage", 0),
                output_current=parameters.get("output_current", 0),
                motor_power=parameters.get("motor_power", 0),
                torque=parameters.get("torque", 0),
                temperature=parameters.get("temperature", 0),
                fault_code=parameters.get("fault_code", 0),
                timestamp=time.time()
            )
            
            return vfd_params
            
        except Exception as e:
            logger.error(f"Error reading VFD parameters from device {device_id}: {e}")
            return None
    
    async def control_vfd(self, device_id: int, command: str, value: float = None) -> bool:
        """Control VFD operation"""
        try:
            device_config = self.device_configs["vfd_devices"].get(str(device_id))
            if not device_config:
                logger.error(f"No configuration found for VFD device {device_id}")
                return False
            
            if command == "start":
                logger.info(f"Starting VFD {device_id}")
                # Write control word to start the motor
                result = await self.client.send_command("rs485", {
                    "action": "start_vfd",
                    "device_id": device_id
                })
                
                await self.log_message("info", f"VFD {device_id} start command sent")
                
            elif command == "stop":
                logger.info(f"Stopping VFD {device_id}")
                result = await self.client.send_command("rs485", {
                    "action": "stop_vfd",
                    "device_id": device_id
                })
                
                await self.log_message("info", f"VFD {device_id} stop command sent")
                
            elif command == "set_speed" and value is not None:
                # Validate speed value
                max_speed = self.config["vfd_control"]["max_speed"]
                speed = max(0, min(max_speed, value))
                
                logger.info(f"Setting VFD {device_id} speed to {speed}%")
                result = await self.client.send_command("rs485", {
                    "action": "set_vfd_speed",
                    "device_id": device_id,
                    "speed": speed
                })
                
                await self.log_message("info", f"VFD {device_id} speed set to {speed}%")
                
            elif command == "emergency_stop":
                logger.warning(f"Emergency stop activated for VFD {device_id}")
                result = await self.client.send_command("rs485", {
                    "action": "stop_vfd",
                    "device_id": device_id
                })
                
                await self.log_message("warning", f"Emergency stop: VFD {device_id}")
                
            else:
                logger.error(f"Unknown VFD command: {command}")
                return False
            
            return result.get("success", False) if result else False
            
        except Exception as e:
            logger.error(f"Error controlling VFD {device_id}: {e}")
            await self.log_message("error", f"VFD control error: {e}")
            return False
    
    async def read_power_meter(self, device_id: int) -> Optional[PowerMeterData]:
        """Read data from power meter"""
        try:
            device_config = self.device_configs["power_meters"].get(str(device_id))
            if not device_config:
                logger.warning(f"No configuration found for power meter {device_id}")
                return None
            
            # Use the RS485 power meter reading function
            result = await self.client.send_command("rs485", {
                "action": "read_power_meter",
                "device_id": device_id
            })
            
            if result:
                power_data = PowerMeterData(
                    device_id=device_id,
                    name=device_config["name"],
                    voltage_l1=result.get("voltage", 0),
                    voltage_l2=result.get("voltage", 0),  # Simplified - would read L2, L3 separately
                    voltage_l3=result.get("voltage", 0),
                    current_l1=result.get("current", 0),
                    current_l2=result.get("current", 0),
                    current_l3=result.get("current", 0),
                    active_power=result.get("power", 0),
                    reactive_power=result.get("power", 0) * 0.3,  # Simplified calculation
                    apparent_power=result.get("power", 0) * 1.1,
                    power_factor=result.get("power_factor", 0),
                    frequency=50.0,  # Assumed frequency
                    energy=result.get("energy", 0),
                    timestamp=time.time()
                )
                
                return power_data
            
        except Exception as e:
            logger.error(f"Error reading power meter {device_id}: {e}")
        
        return None
    
    async def monitor_system_parameters(self):
        """Monitor all system parameters continuously"""
        logger.info("Starting system parameter monitoring...")
        await self.log_message("info", "Starting VFD system monitoring")
        
        while self.running:
            try:
                # Monitor all VFD devices
                for device_id_str in self.device_configs["vfd_devices"].keys():
                    device_id = int(device_id_str)
                    vfd_data = await self.read_vfd_parameters(device_id)
                    
                    if vfd_data:
                        self.vfd_data[device_id] = vfd_data
                        
                        # Check for alarms
                        await self.check_vfd_alarms(vfd_data)
                        
                        # Send data to dashboard
                        await self.send_vfd_data_to_dashboard(vfd_data)
                
                # Monitor power meters
                for device_id_str in self.device_configs["power_meters"].keys():
                    device_id = int(device_id_str)
                    power_data = await self.read_power_meter(device_id)
                    
                    if power_data:
                        self.power_data[device_id] = power_data
                        
                        # Check for power alarms
                        await self.check_power_alarms(power_data)
                        
                        # Send data to dashboard
                        await self.send_power_data_to_dashboard(power_data)
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config["monitoring"]["update_interval"])
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def check_vfd_alarms(self, vfd_data: VFDParameters):
        """Check VFD parameters for alarm conditions"""
        try:
            thresholds = self.config["monitoring"]["alarm_thresholds"]
            
            # Check motor current
            if "motor_current" in thresholds:
                current_threshold = thresholds["motor_current"]
                current_pct = (vfd_data.output_current / 12.0) * 100  # Assuming 12A rated
                
                if current_pct > current_threshold["alarm"]:
                    await self.log_message("alarm", f"VFD {vfd_data.device_id} motor current alarm: {current_pct:.1f}%")
                elif current_pct > current_threshold["warning"]:
                    await self.log_message("warning", f"VFD {vfd_data.device_id} motor current warning: {current_pct:.1f}%")
            
            # Check motor temperature
            if "motor_temperature" in thresholds and vfd_data.temperature > 0:
                temp_threshold = thresholds["motor_temperature"]
                
                if vfd_data.temperature > temp_threshold["alarm"]:
                    await self.log_message("alarm", f"VFD {vfd_data.device_id} temperature alarm: {vfd_data.temperature}°C")
                elif vfd_data.temperature > temp_threshold["warning"]:
                    await self.log_message("warning", f"VFD {vfd_data.device_id} temperature warning: {vfd_data.temperature}°C")
            
            # Check for fault codes
            if vfd_data.fault_code > 0:
                await self.log_message("alarm", f"VFD {vfd_data.device_id} fault code: {vfd_data.fault_code}")
            
        except Exception as e:
            logger.error(f"Error checking VFD alarms: {e}")
    
    async def check_power_alarms(self, power_data: PowerMeterData):
        """Check power parameters for alarm conditions"""
        try:
            thresholds = self.config["monitoring"]["alarm_thresholds"]
            
            # Check power factor
            if "power_factor" in thresholds:
                pf_threshold = thresholds["power_factor"]
                
                if power_data.power_factor < pf_threshold["alarm"]:
                    await self.log_message("alarm", f"Power meter {power_data.device_id} low power factor: {power_data.power_factor}")
                elif power_data.power_factor < pf_threshold["warning"]:
                    await self.log_message("warning", f"Power meter {power_data.device_id} low power factor: {power_data.power_factor}")
            
        except Exception as e:
            logger.error(f"Error checking power alarms: {e}")
    
    async def send_vfd_data_to_dashboard(self, vfd_data: VFDParameters):
        """Send VFD data to web dashboard"""
        try:
            await self.client.send_command("log", {
                "level": "data",
                "data_type": "vfd_parameters",
                "device_id": vfd_data.device_id,
                "device_name": vfd_data.name,
                "status": vfd_data.status.value,
                "speed_reference": vfd_data.speed_reference,
                "actual_speed": vfd_data.actual_speed,
                "output_current": vfd_data.output_current,
                "motor_power": vfd_data.motor_power,
                "timestamp": vfd_data.timestamp
            })
        except Exception as e:
            logger.error(f"Error sending VFD data to dashboard: {e}")
    
    async def send_power_data_to_dashboard(self, power_data: PowerMeterData):
        """Send power data to web dashboard"""
        try:
            await self.client.send_command("log", {
                "level": "data",
                "data_type": "power_meter",
                "device_id": power_data.device_id,
                "device_name": power_data.name,
                "active_power": power_data.active_power,
                "power_factor": power_data.power_factor,
                "energy": power_data.energy,
                "timestamp": power_data.timestamp
            })
        except Exception as e:
            logger.error(f"Error sending power data to dashboard: {e}")
    
    async def vfd_control_demo(self):
        """Demonstrate VFD control operations"""
        logger.info("=== VFD Control Demo ===")
        await self.log_message("info", "Starting VFD control demo")
        
        # Control first VFD
        vfd_ids = list(self.device_configs["vfd_devices"].keys())
        if not vfd_ids:
            logger.warning("No VFD devices configured")
            return
        
        vfd_id = int(vfd_ids[0])
        
        try:
            # Start VFD
            logger.info(f"Starting VFD {vfd_id}")
            await self.control_vfd(vfd_id, "start")
            await asyncio.sleep(3)
            
            # Ramp up speed gradually
            speeds = [25, 50, 75, 100, 75, 50, 25]
            for speed in speeds:
                if not self.running:
                    break
                
                logger.info(f"Setting VFD {vfd_id} speed to {speed}%")
                await self.control_vfd(vfd_id, "set_speed", speed)
                await asyncio.sleep(5)
                
                # Read parameters
                params = await self.read_vfd_parameters(vfd_id)
                if params:
                    logger.info(f"VFD Status: {params.status.value}, Speed: {params.actual_speed:.1f} RPM, Current: {params.output_current:.2f} A")
            
            # Stop VFD
            logger.info(f"Stopping VFD {vfd_id}")
            await self.control_vfd(vfd_id, "stop")
            
        except Exception as e:
            logger.error(f"Error in VFD control demo: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get RS485 status from server
            rs485_status = await self.client.send_command("rs485", {"action": "rs485_status"})
            
            return {
                "controller_running": self.running,
                "discovered_devices": len(self.discovered_devices),
                "vfd_devices": len(self.vfd_data),
                "power_meters": len(self.power_data),
                "rs485_status": rs485_status,
                "last_vfd_reading": list(self.vfd_data.values())[-1].__dict__ if self.vfd_data else None,
                "last_power_reading": list(self.power_data.values())[-1].__dict__ if self.power_data else None
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    async def run_vfd_control_system(self):
        """Run the complete RS485 VFD control system"""
        self.running = True
        
        try:
            await self.log_message("info", "RS485 VFD Controller started")
            
            # Connect to EDPM server
            if not await self.connect():
                logger.error("Cannot connect to EDPM server, exiting...")
                return
            
            # Get initial RS485 status
            status = await self.get_system_status()
            logger.info(f"Initial system status: {status}")
            
            # Discover Modbus devices
            await self.scan_modbus_devices()
            
            # Start monitoring task
            monitoring_task = asyncio.create_task(self.monitor_system_parameters())
            
            # Run VFD control demonstration
            demo_task = asyncio.create_task(self.vfd_control_demo())
            
            # Wait for tasks to complete or interruption
            await asyncio.gather(monitoring_task, demo_task, return_exceptions=True)
            
            await self.log_message("info", "RS485 VFD Controller completed")
            logger.info("VFD control system completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("VFD control system interrupted by user")
            await self.log_message("info", "RS485 VFD system interrupted by user")
        except Exception as e:
            logger.error(f"VFD control system error: {e}")
            await self.log_message("error", f"RS485 VFD system error: {e}")
        finally:
            self.running = False
            await self.disconnect()
    
    def stop(self):
        """Stop the VFD control system"""
        self.running = False


async def main():
    """Main entry point"""
    print("EDPM Lite RS485/Modbus VFD Control Example")
    print("=" * 55)
    print("This example demonstrates VFD motor control using RS485/Modbus with EDPM Lite")
    print("Press Ctrl+C to stop the VFD control system")
    print()
    
    # Create and run the VFD controller
    controller = RS485VFDController()
    
    # Setup signal handling
    import signal
    def signal_handler(sig, frame):
        logger.info("Received stop signal...")
        controller.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the VFD control system
    await controller.run_vfd_control_system()


if __name__ == "__main__":
    asyncio.run(main())
