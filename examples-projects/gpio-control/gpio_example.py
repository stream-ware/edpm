#!/usr/bin/env python3
"""
GPIO Control Example for EDPM Lite
Demonstrates GPIO control using the refactored EDPM package with real-time monitoring.
"""

import asyncio
import json
import time
import logging
from pathlib import Path

from edpm import EDPMClient, Config, Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPIOControlExample:
    """GPIO Control Example Application"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the GPIO example"""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.client = None
        self.running = False
    
    def load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "edpm_endpoint": "ipc:///tmp/edpm.ipc",
                "websocket_url": "ws://localhost:8080/ws",
                "transport": "zmq",
                "gpio_pins": [17, 18, 19, 20],
                "pwm_pin": 21,
                "demo_duration": 30,
                "cycle_delay": 2.0
            }
    
    async def connect(self):
        """Connect to EDPM server"""
        try:
            # Create EDPM client
            edpm_config = Config()
            edmp_config.endpoint = self.config["edpm_endpoint"]
            
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
    
    async def gpio_basic_control(self):
        """Demonstrate basic GPIO pin control"""
        logger.info("=== GPIO Basic Control Demo ===")
        await self.log_message("info", "Starting GPIO basic control demo")
        
        pins = self.config["gpio_pins"]
        
        for pin in pins:
            try:
                # Set pin HIGH
                logger.info(f"Setting GPIO pin {pin} HIGH")
                await self.client.gpio_write(pin, 1)
                await asyncio.sleep(0.5)
                
                # Read pin value
                value = await self.client.gpio_read(pin)
                logger.info(f"GPIO pin {pin} value: {value}")
                
                await asyncio.sleep(1)
                
                # Set pin LOW
                logger.info(f"Setting GPIO pin {pin} LOW")
                await self.client.gpio_write(pin, 0)
                
                # Read pin value again
                value = await self.client.gpio_read(pin)
                logger.info(f"GPIO pin {pin} value: {value}")
                
                await asyncio.sleep(self.config["cycle_delay"])
                
            except Exception as e:
                logger.error(f"Error controlling GPIO pin {pin}: {e}")
                await self.log_message("error", f"GPIO pin {pin} control failed: {e}")
    
    async def gpio_pwm_demo(self):
        """Demonstrate PWM signal generation"""
        logger.info("=== GPIO PWM Demo ===")
        await self.log_message("info", "Starting GPIO PWM demo")
        
        pwm_pin = self.config["pwm_pin"]
        
        # PWM configurations to test
        pwm_configs = [
            {"frequency": 1000, "duty_cycle": 25},   # 25% duty cycle
            {"frequency": 1000, "duty_cycle": 50},   # 50% duty cycle
            {"frequency": 1000, "duty_cycle": 75},   # 75% duty cycle
            {"frequency": 2000, "duty_cycle": 50},   # Different frequency
        ]
        
        for config in pwm_configs:
            try:
                freq = config["frequency"]
                duty = config["duty_cycle"]
                
                logger.info(f"Setting PWM on pin {pwm_pin}: {freq}Hz, {duty}% duty cycle")
                await self.client.gpio_pwm(pwm_pin, freq, duty)
                await self.log_message("info", f"PWM set: {freq}Hz, {duty}% on pin {pwm_pin}")
                
                # Let PWM run for a few seconds
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error setting PWM on pin {pwm_pin}: {e}")
                await self.log_message("error", f"PWM setup failed: {e}")
        
        # Stop PWM
        try:
            await self.client.gpio_pwm(pwm_pin, 0, 0)
            logger.info(f"PWM stopped on pin {pwm_pin}")
        except Exception as e:
            logger.error(f"Error stopping PWM: {e}")
    
    async def gpio_pattern_demo(self):
        """Demonstrate GPIO pattern control"""
        logger.info("=== GPIO Pattern Demo ===")
        await self.log_message("info", "Starting GPIO pattern demo")
        
        pins = self.config["gpio_pins"]
        patterns = [
            # Knight Rider pattern
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            # Binary counting pattern
            [0, 0, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 1, 0, 0],
            [0, 1, 0, 1],
            [0, 1, 1, 0],
            [0, 1, 1, 1],
            [1, 0, 0, 0],
        ]
        
        for i, pattern in enumerate(patterns):
            try:
                logger.info(f"Pattern {i+1}: {pattern}")
                
                # Set all pins according to pattern
                for pin, value in zip(pins, pattern):
                    await self.client.gpio_write(pin, value)
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in pattern {i+1}: {e}")
        
        # Turn off all pins
        for pin in pins:
            try:
                await self.client.gpio_write(pin, 0)
            except Exception as e:
                logger.error(f"Error turning off pin {pin}: {e}")
    
    async def monitor_status(self):
        """Monitor and report system status"""
        try:
            # Get server status
            status = await self.client.send_command("status", {})
            logger.info(f"Server status: {status}")
            
            # Get GPIO-specific status
            gpio_status = await self.client.send_command("gpio", {"action": "gpio_status"})
            logger.info(f"GPIO status: {gpio_status}")
            
            await self.log_message("info", "Status monitoring completed")
            
        except Exception as e:
            logger.error(f"Error monitoring status: {e}")
    
    async def run_demo(self):
        """Run the complete GPIO demo"""
        self.running = True
        
        try:
            await self.log_message("info", "GPIO Control Example started")
            
            # Connect to EDPM server
            if not await self.connect():
                logger.error("Cannot connect to EDPM server, exiting...")
                return
            
            # Monitor initial status
            await self.monitor_status()
            
            # Run demonstrations
            demo_start = time.time()
            duration = self.config["demo_duration"]
            
            logger.info(f"Running GPIO demos for {duration} seconds...")
            
            while self.running and (time.time() - demo_start) < duration:
                # Basic GPIO control
                await self.gpio_basic_control()
                
                if not self.running:
                    break
                
                # PWM demonstration
                await self.gpio_pwm_demo()
                
                if not self.running:
                    break
                
                # Pattern demonstration
                await self.gpio_pattern_demo()
                
                # Check if we should continue
                if (time.time() - demo_start) >= duration:
                    break
                
                logger.info("Waiting before next cycle...")
                await asyncio.sleep(5)
            
            await self.log_message("info", "GPIO Control Example completed")
            logger.info("Demo completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
            await self.log_message("info", "GPIO demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo error: {e}")
            await self.log_message("error", f"GPIO demo error: {e}")
        finally:
            self.running = False
            await self.disconnect()
    
    def stop(self):
        """Stop the demo"""
        self.running = False


async def main():
    """Main entry point"""
    print("EDPM Lite GPIO Control Example")
    print("=" * 40)
    print("This example demonstrates GPIO control using EDPM Lite")
    print("Press Ctrl+C to stop the demo")
    print()
    
    # Create and run the example
    example = GPIOControlExample()
    
    # Setup signal handling
    import signal
    def signal_handler(sig, frame):
        logger.info("Received stop signal...")
        example.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the demo
    await example.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
