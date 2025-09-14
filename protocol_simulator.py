#!/usr/bin/env python3
"""
EDPM Extended Protocol Simulator
Main entry point for running all protocol simulators
"""
import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any

# Add protocols directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'protocols'))

from protocols.i2c_handler import I2CHandler
from protocols.i2s_handler import I2SHandler, AudioConfig
from protocols.rs485_handler import RS485Handler
import edpm_lite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProtocolSimulator')

class ProtocolSimulator:
    """Main protocol simulator coordinator"""
    
    def __init__(self):
        self.running = False
        self.edpm_client = None
        
        # Protocol handlers
        self.i2c_handler = None
        self.i2s_handler = None
        self.rs485_handler = None
        
        # Monitoring tasks
        self.tasks = []
    
    async def initialize(self):
        """Initialize all protocol handlers and EDPM connection"""
        logger.info("🚀 Initializing EDPM Protocol Simulator...")
        
        # Initialize EDPM client
        try:
            self.edpm_client = edpm_lite.EDPMLite(use_zmq=True)
            logger.info("✅ EDPM client initialized")
        except Exception as e:
            logger.warning(f"EDPM connection failed: {e}, continuing with offline mode")
            self.edpm_client = edpm_lite.EDPMLite(use_zmq=False)
        
        # Initialize protocol handlers in simulator mode
        try:
            self.i2c_handler = I2CHandler(bus_number=1, simulator=True)
            logger.info("✅ I2C simulator initialized")
        except Exception as e:
            logger.error(f"I2C initialization failed: {e}")
        
        try:
            audio_config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
            self.i2s_handler = I2SHandler(config=audio_config, simulator=True)
            logger.info("✅ I2S audio simulator initialized")
        except Exception as e:
            logger.error(f"I2S initialization failed: {e}")
        
        try:
            self.rs485_handler = RS485Handler(port="/dev/ttyUSB0", baudrate=9600, simulator=True)
            logger.info("✅ RS485/Modbus simulator initialized")
        except Exception as e:
            logger.error(f"RS485 initialization failed: {e}")
        
        logger.info("🎉 All protocol simulators initialized!")
    
    async def start_monitoring(self):
        """Start continuous monitoring of all protocols"""
        if not self.running:
            return
        
        logger.info("📊 Starting protocol monitoring...")
        
        # Start I2C monitoring
        if self.i2c_handler:
            task = asyncio.create_task(
                self.i2c_handler.continuous_monitoring(self._i2c_callback, interval=2.0)
            )
            self.tasks.append(task)
        
        # Start I2S monitoring
        if self.i2s_handler:
            task = asyncio.create_task(
                self.i2s_handler.continuous_monitoring(self._i2s_callback, interval=1.0)
            )
            self.tasks.append(task)
        
        # Start RS485 monitoring
        if self.rs485_handler:
            task = asyncio.create_task(
                self.rs485_handler.continuous_monitoring(self._rs485_callback, interval=3.0)
            )
            self.tasks.append(task)
        
        logger.info("✅ All monitoring tasks started")
    
    async def _i2c_callback(self, data: Dict[str, Any]):
        """Handle I2C sensor data"""
        try:
            if self.edpm_client:
                # Log sensor readings
                if 'temperature' in data:
                    self.edpm_client.log("info", "I2C sensor reading", **data)
                
                # Emit sensor events
                self.edpm_client.emit_event("sensor_reading", {
                    "protocol": "I2C",
                    "timestamp": asyncio.get_event_loop().time(),
                    **data
                })
            
            logger.info(f"I2C: {data}")
            
        except Exception as e:
            logger.error(f"I2C callback error: {e}")
    
    async def _i2s_callback(self, data: Dict[str, Any]):
        """Handle I2S audio data"""
        try:
            if self.edpm_client:
                # Log audio analysis
                self.edpm_client.log("info", "Audio analysis", **data)
                
                # Emit audio events
                self.edpm_client.emit_event("audio_level", {
                    "protocol": "I2S",
                    "timestamp": asyncio.get_event_loop().time(),
                    **data
                })
            
            logger.info(f"I2S: Level={data.get('db_level', -120):.1f}dB, Freq={data.get('dominant_frequency', 0):.1f}Hz")
            
        except Exception as e:
            logger.error(f"I2S callback error: {e}")
    
    async def _rs485_callback(self, data: Dict[str, Any]):
        """Handle RS485/Modbus device data"""
        try:
            if self.edpm_client:
                # Log device readings
                self.edpm_client.log("info", f"Modbus device {data.get('slave_id', 'unknown')}", **data)
                
                # Emit device events
                self.edpm_client.emit_event("modbus_reading", {
                    "protocol": "RS485",
                    "timestamp": asyncio.get_event_loop().time(),
                    **data
                })
            
            slave_id = data.get('slave_id', 0)
            if slave_id == 1:  # Temperature controller
                temp = data.get('temperature', 0)
                logger.info(f"RS485: Device {slave_id} - Temperature: {temp:.1f}°C")
            elif slave_id == 2:  # Power meter
                power = data.get('power', 0)
                logger.info(f"RS485: Device {slave_id} - Power: {power:.2f}kW")
            elif slave_id == 3:  # VFD
                freq = data.get('frequency_actual', 0)
                logger.info(f"RS485: Device {slave_id} - Frequency: {freq:.1f}Hz")
            
        except Exception as e:
            logger.error(f"RS485 callback error: {e}")
    
    async def run_demo_sequence(self):
        """Run a demonstration sequence of all protocols"""
        logger.info("🎭 Running protocol demonstration sequence...")
        
        # I2C Demo
        if self.i2c_handler:
            logger.info("📡 I2C Demo: Reading sensors...")
            
            # Scan for devices
            devices = self.i2c_handler.scan()
            logger.info(f"I2C devices found: {[f'0x{addr:02X}' for addr in devices]}")
            
            # Read BME280 if available
            if 0x76 in devices:
                bme_data = self.i2c_handler.read_bme280()
                logger.info(f"BME280: {bme_data}")
            
            # Read ADS1115 if available
            if 0x48 in devices:
                for ch in range(4):
                    voltage = self.i2c_handler.read_ads1115(channel=ch)
                    logger.info(f"ADS1115 CH{ch}: {voltage:.3f}V")
        
        # I2S Demo
        if self.i2s_handler:
            logger.info("🔊 I2S Demo: Audio test sequence...")
            
            # List audio devices
            devices = self.i2s_handler.list_devices()
            logger.info(f"Audio devices: {len(devices)}")
            
            # Play test tones
            for freq in [440, 880, 1760]:
                logger.info(f"Playing {freq}Hz tone...")
                await self.i2s_handler.play_tone(freq, duration=0.5, amplitude=0.3)
                await asyncio.sleep(0.2)
        
        # RS485 Demo
        if self.rs485_handler:
            logger.info("⚡ RS485 Demo: Modbus device communication...")
            
            # Scan for devices
            devices = self.rs485_handler.scan_devices()
            logger.info(f"Modbus devices found: {devices}")
            
            # Read from each device
            for slave_id in devices[:3]:  # Limit to first 3 devices
                try:
                    device_info = self.rs485_handler.get_device_info(slave_id)
                    logger.info(f"Device {slave_id}: {device_info['name']}")
                    
                    # Read some registers
                    regs = self.rs485_handler.read_holding_registers(slave_id, 0, 3)
                    logger.info(f"Device {slave_id} registers: {regs}")
                    
                    # Test coil operations for VFD
                    if slave_id == 3:
                        logger.info("Testing VFD start/stop...")
                        self.rs485_handler.write_single_coil(slave_id, 0, True)  # Start
                        await asyncio.sleep(0.5)
                        coils = self.rs485_handler.read_coils(slave_id, 0, 3)
                        logger.info(f"VFD coils after start: {coils}")
                        
                        self.rs485_handler.write_single_coil(slave_id, 0, False)  # Stop
                        await asyncio.sleep(0.5)
                        coils = self.rs485_handler.read_coils(slave_id, 0, 3)
                        logger.info(f"VFD coils after stop: {coils}")
                
                except Exception as e:
                    logger.error(f"Error communicating with device {slave_id}: {e}")
        
        logger.info("✅ Demo sequence completed!")
    
    async def start(self):
        """Start the protocol simulator"""
        self.running = True
        
        await self.initialize()
        
        # Run demo sequence once
        await self.run_demo_sequence()
        
        # Start continuous monitoring
        await self.start_monitoring()
        
        # Keep running
        logger.info("🔄 Protocol simulator running... Press Ctrl+C to stop")
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the protocol simulator"""
        self.running = False
        
        logger.info("🛑 Stopping protocol simulator...")
        
        # Cancel all monitoring tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("✅ Protocol simulator stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    # The asyncio event loop will handle the KeyboardInterrupt

async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start simulator
    simulator = ProtocolSimulator()
    await simulator.start()

if __name__ == "__main__":
    # Handle environment variables
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))
    
    logger.info("🚀 Starting EDPM Extended Protocol Simulator")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
