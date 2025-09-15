#!/usr/bin/env python3
"""
EDPM CLI Entry Points
Command-line interfaces for EDPM server, client, and dashboard components.
"""

import sys
import asyncio
import argparse
import logging
import signal
from pathlib import Path
from typing import Optional

from .core.config import Config
from .core.server import EDPMServer
from .core.client import EDPMClient
from .web.dashboard import DashboardServer


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def create_base_parser() -> argparse.ArgumentParser:
    """Create base argument parser with common options"""
    parser = argparse.ArgumentParser(description="EDPM Lite - Edge Data Processing and Monitoring")
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Configuration file path"
    )
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log file path (default: console only)"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="EDPM Lite 1.0.0"
    )
    return parser


def server_main():
    """Main entry point for EDPM server"""
    parser = create_base_parser()
    parser.prog = "edpm-server"
    parser.description = "EDPM Lite Server - Industrial IoT Edge Data Processing Server"
    
    # Server-specific arguments
    parser.add_argument(
        "--endpoint",
        type=str,
        help="ZeroMQ endpoint (default: from config or ipc:///tmp/edpm.ipc)"
    )
    parser.add_argument(
        "--web-port",
        type=int,
        help="Web dashboard port (default: from config or 8080)"
    )
    parser.add_argument(
        "--disable-web",
        action="store_true",
        help="Disable web dashboard server"
    )
    parser.add_argument(
        "--simulator",
        action="store_true",
        help="Enable simulator mode for all protocols"
    )
    parser.add_argument(
        "--gpio-simulator",
        action="store_true",
        help="Enable GPIO simulator mode"
    )
    parser.add_argument(
        "--i2c-simulator",
        action="store_true",
        help="Enable I2C simulator mode"
    )
    parser.add_argument(
        "--i2s-simulator",
        action="store_true",
        help="Enable I2S simulator mode"
    )
    parser.add_argument(
        "--rs485-simulator",
        action="store_true",
        help="Enable RS485 simulator mode"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    logger.info("Starting EDPM Server")
    
    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config.from_env()
        
        # Override config with command line arguments
        if args.endpoint:
            config.endpoint = args.endpoint
        if args.web_port:
            config.web_port = args.web_port
        if args.disable_web:
            config.web_enabled = False
        
        # Set simulator flags
        if args.simulator:
            config.gpio_simulator = True
            config.i2c_simulator = True
            config.i2s_simulator = True
            config.rs485_simulator = True
        else:
            if args.gpio_simulator:
                config.gpio_simulator = True
            if args.i2c_simulator:
                config.i2c_simulator = True
            if args.i2s_simulator:
                config.i2s_simulator = True
            if args.rs485_simulator:
                config.rs485_simulator = True
        
        # Create and start server
        server = EDPMServer(config)
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            loop.create_task(server.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run server
        logger.info(f"EDPM Server starting on {config.endpoint}")
        if config.web_enabled:
            logger.info(f"Web dashboard available at http://localhost:{config.web_port}")
        
        loop.run_until_complete(server.start())
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("EDPM Server stopped")


def client_main():
    """Main entry point for EDPM client"""
    parser = create_base_parser()
    parser.prog = "edpm-client"
    parser.description = "EDPM Lite Client - Industrial IoT Edge Data Processing Client"
    
    # Client-specific arguments
    parser.add_argument(
        "--endpoint",
        type=str,
        help="EDPM server endpoint (default: from config or ipc:///tmp/edpm.ipc)"
    )
    parser.add_argument(
        "--transport",
        choices=["zmq", "websocket"],
        default="zmq",
        help="Transport protocol (default: zmq)"
    )
    parser.add_argument(
        "--websocket-url",
        type=str,
        help="WebSocket server URL (default: ws://localhost:8080/ws)"
    )
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # GPIO commands
    gpio_parser = subparsers.add_parser("gpio", help="GPIO commands")
    gpio_subparsers = gpio_parser.add_subparsers(dest="gpio_action", help="GPIO actions")
    
    gpio_read_parser = gpio_subparsers.add_parser("read", help="Read GPIO pin")
    gpio_read_parser.add_argument("pin", type=int, help="GPIO pin number")
    
    gpio_write_parser = gpio_subparsers.add_parser("write", help="Write GPIO pin")
    gpio_write_parser.add_argument("pin", type=int, help="GPIO pin number")
    gpio_write_parser.add_argument("value", type=int, choices=[0, 1], help="Pin value (0 or 1)")
    
    gpio_pwm_parser = gpio_subparsers.add_parser("pwm", help="Set PWM on GPIO pin")
    gpio_pwm_parser.add_argument("pin", type=int, help="GPIO pin number")
    gpio_pwm_parser.add_argument("frequency", type=float, help="PWM frequency in Hz")
    gpio_pwm_parser.add_argument("duty_cycle", type=float, help="PWM duty cycle (0-100)")
    
    # I2C commands
    i2c_parser = subparsers.add_parser("i2c", help="I2C commands")
    i2c_subparsers = i2c_parser.add_subparsers(dest="i2c_action", help="I2C actions")
    
    i2c_scan_parser = i2c_subparsers.add_parser("scan", help="Scan I2C devices")
    
    i2c_read_parser = i2c_subparsers.add_parser("read", help="Read from I2C device")
    i2c_read_parser.add_argument("address", type=lambda x: int(x, 0), help="I2C device address (hex or decimal)")
    i2c_read_parser.add_argument("register", type=lambda x: int(x, 0), help="Register address")
    i2c_read_parser.add_argument("--count", type=int, default=1, help="Number of bytes to read")
    
    i2c_write_parser = i2c_subparsers.add_parser("write", help="Write to I2C device")
    i2c_write_parser.add_argument("address", type=lambda x: int(x, 0), help="I2C device address (hex or decimal)")
    i2c_write_parser.add_argument("register", type=lambda x: int(x, 0), help="Register address")
    i2c_write_parser.add_argument("data", nargs="+", type=lambda x: int(x, 0), help="Data bytes to write")
    
    # I2S commands
    i2s_parser = subparsers.add_parser("i2s", help="I2S audio commands")
    i2s_subparsers = i2s_parser.add_subparsers(dest="i2s_action", help="I2S actions")
    
    i2s_tone_parser = i2s_subparsers.add_parser("tone", help="Generate audio tone")
    i2s_tone_parser.add_argument("frequency", type=float, help="Tone frequency in Hz")
    i2s_tone_parser.add_argument("duration", type=float, help="Duration in seconds")
    
    i2s_record_parser = i2s_subparsers.add_parser("record", help="Record audio")
    i2s_record_parser.add_argument("duration", type=float, help="Recording duration in seconds")
    i2s_record_parser.add_argument("--output", type=str, help="Output file path")
    
    # RS485 commands
    rs485_parser = subparsers.add_parser("rs485", help="RS485/Modbus commands")
    rs485_subparsers = rs485_parser.add_subparsers(dest="rs485_action", help="RS485 actions")
    
    rs485_scan_parser = rs485_subparsers.add_parser("scan", help="Scan Modbus devices")
    rs485_scan_parser.add_argument("--start", type=int, default=1, help="Start device ID")
    rs485_scan_parser.add_argument("--end", type=int, default=10, help="End device ID")
    
    rs485_read_parser = rs485_subparsers.add_parser("read", help="Read Modbus registers")
    rs485_read_parser.add_argument("device_id", type=int, help="Modbus device ID")
    rs485_read_parser.add_argument("address", type=int, help="Register start address")
    rs485_read_parser.add_argument("--count", type=int, default=1, help="Number of registers")
    
    rs485_vfd_parser = rs485_subparsers.add_parser("vfd", help="VFD control commands")
    rs485_vfd_subparsers = rs485_vfd_parser.add_subparsers(dest="vfd_action", help="VFD actions")
    
    rs485_vfd_start = rs485_vfd_subparsers.add_parser("start", help="Start VFD motor")
    rs485_vfd_start.add_argument("device_id", type=int, help="VFD device ID")
    
    rs485_vfd_stop = rs485_vfd_subparsers.add_parser("stop", help="Stop VFD motor")
    rs485_vfd_stop.add_argument("device_id", type=int, help="VFD device ID")
    
    rs485_vfd_speed = rs485_vfd_subparsers.add_parser("speed", help="Set VFD speed")
    rs485_vfd_speed.add_argument("device_id", type=int, help="VFD device ID")
    rs485_vfd_speed.add_argument("speed", type=int, help="Speed percentage (0-100)")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get server status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    
    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config.from_env()
        
        # Override config with command line arguments
        if args.endpoint:
            config.endpoint = args.endpoint
        if args.websocket_url:
            config.websocket_url = args.websocket_url
        
        # Execute command
        asyncio.run(execute_client_command(args, config, logger))
        
    except Exception as e:
        logger.error(f"Client error: {e}")
        sys.exit(1)


async def execute_client_command(args, config: Config, logger):
    """Execute client command"""
    # Create client
    transport = "websocket" if args.transport == "websocket" else "zmq"
    client = EDPMClient(config, transport=transport)
    
    try:
        await client.connect()
        
        # Execute command based on arguments
        if args.command == "status":
            result = await client.send_command("status", {})
            print(f"Server Status: {result}")
        
        elif args.command == "gpio":
            if args.gpio_action == "read":
                result = await client.gpio_read(args.pin)
                print(f"GPIO Pin {args.pin}: {result}")
            elif args.gpio_action == "write":
                result = await client.gpio_write(args.pin, args.value)
                print(f"GPIO Pin {args.pin} set to {args.value}: {result}")
            elif args.gpio_action == "pwm":
                result = await client.gpio_pwm(args.pin, args.frequency, args.duty_cycle)
                print(f"GPIO Pin {args.pin} PWM set: {result}")
        
        elif args.command == "i2c":
            if args.i2c_action == "scan":
                result = await client.i2c_scan()
                print(f"I2C Devices Found: {result}")
            elif args.i2c_action == "read":
                result = await client.i2c_read(args.address, args.register, args.count)
                print(f"I2C Read from 0x{args.address:02X}[0x{args.register:02X}]: {result}")
            elif args.i2c_action == "write":
                result = await client.i2c_write(args.address, args.register, args.data)
                print(f"I2C Write to 0x{args.address:02X}[0x{args.register:02X}]: {result}")
        
        elif args.command == "i2s":
            if args.i2s_action == "tone":
                result = await client.send_command("i2s", {
                    "action": "generate_tone",
                    "frequency": args.frequency,
                    "duration": args.duration
                })
                print(f"I2S Tone Generated: {result}")
            elif args.i2s_action == "record":
                result = await client.send_command("i2s", {
                    "action": "record_audio",
                    "duration": args.duration,
                    "output_path": args.output
                })
                print(f"I2S Recording: {result}")
        
        elif args.command == "rs485":
            if args.rs485_action == "scan":
                result = await client.send_command("rs485", {
                    "action": "scan_devices",
                    "start_id": args.start,
                    "end_id": args.end
                })
                print(f"RS485 Device Scan: {result}")
            elif args.rs485_action == "read":
                result = await client.send_command("rs485", {
                    "action": "modbus_read",
                    "device_id": args.device_id,
                    "start_address": args.address,
                    "count": args.count
                })
                print(f"RS485 Modbus Read: {result}")
            elif args.rs485_action == "vfd":
                if args.vfd_action == "start":
                    result = await client.send_command("rs485", {
                        "action": "start_vfd",
                        "device_id": args.device_id
                    })
                    print(f"VFD Start: {result}")
                elif args.vfd_action == "stop":
                    result = await client.send_command("rs485", {
                        "action": "stop_vfd",
                        "device_id": args.device_id
                    })
                    print(f"VFD Stop: {result}")
                elif args.vfd_action == "speed":
                    result = await client.send_command("rs485", {
                        "action": "set_vfd_speed",
                        "device_id": args.device_id,
                        "speed": args.speed
                    })
                    print(f"VFD Speed Set: {result}")
        
    finally:
        await client.disconnect()


def dashboard_main():
    """Main entry point for EDPM dashboard server"""
    parser = create_base_parser()
    parser.prog = "edpm-dashboard"
    parser.description = "EDPM Lite Dashboard - Web-based monitoring and control interface"
    
    # Dashboard-specific arguments
    parser.add_argument(
        "--port",
        type=int,
        help="Dashboard server port (default: from config or 8080)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Dashboard server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--edpm-endpoint",
        type=str,
        help="EDPM server endpoint (default: from config or ipc:///tmp/edpm.ipc)"
    )
    parser.add_argument(
        "--static-dir",
        type=str,
        help="Static files directory (default: web/static)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)
    logger.info("Starting EDPM Dashboard Server")
    
    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config.from_env()
        
        # Override config with command line arguments
        if args.port:
            config.web_port = args.port
        if args.edpm_endpoint:
            config.endpoint = args.edpm_endpoint
        
        # Create dashboard server
        dashboard = DashboardServer(config)
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down dashboard...")
            loop.create_task(dashboard.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run dashboard
        logger.info(f"EDPM Dashboard starting on http://{args.host}:{config.web_port}")
        
        loop.run_until_complete(dashboard.start(host=args.host, port=config.web_port))
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        sys.exit(1)
    finally:
        logger.info("EDPM Dashboard stopped")


if __name__ == "__main__":
    # This allows running the CLI module directly for testing
    print("EDPM CLI Module - Use edpm-server, edpm-client, or edpm-dashboard commands")
    sys.exit(1)
