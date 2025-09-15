"""
EDPM Configuration Module
Centralized configuration management for EDPM framework.
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Config:
    """
    EDPM Configuration Class
    
    Manages all configuration settings for EDPM framework with environment
    variable support and JSON config file loading.
    """
    
    # Core settings
    zmq_endpoint: str = "ipc:///tmp/edpm.ipc"
    ws_port: int = 8080
    db_path: str = "/dev/shm/edpm.db"
    max_buffer: int = 10000
    debug: bool = False
    
    # GPIO settings
    gpio_mode: str = "SIMULATOR"  # SIMULATOR, BCM, BOARD
    
    # Protocol simulator settings
    simulate_sensors: bool = True
    i2c_simulator: bool = True
    i2s_simulator: bool = True
    rs485_simulator: bool = True
    
    # Web UI settings
    web_enabled: bool = True
    static_path: str = "web"
    dashboard_path: str = "web/dashboard.html"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            zmq_endpoint=os.getenv("EDPM_ENDPOINT", cls.zmq_endpoint),
            ws_port=int(os.getenv("EDPM_PORT", str(cls.ws_port))),
            db_path=os.getenv("EDPM_DB", cls.db_path),
            max_buffer=int(os.getenv("EDPM_MAX_BUFFER", str(cls.max_buffer))),
            debug=os.getenv("EDPM_DEBUG", "false").lower() == "true",
            
            gpio_mode=os.getenv("GPIO_MODE", cls.gpio_mode),
            
            simulate_sensors=os.getenv("SIMULATE_SENSORS", "true").lower() == "true",
            i2c_simulator=os.getenv("I2C_SIMULATOR", "true").lower() == "true", 
            i2s_simulator=os.getenv("I2S_SIMULATOR", "true").lower() == "true",
            rs485_simulator=os.getenv("RS485_SIMULATOR", "true").lower() == "true",
            
            web_enabled=os.getenv("WEB_ENABLED", "true").lower() == "true",
            static_path=os.getenv("STATIC_PATH", cls.static_path),
            dashboard_path=os.getenv("DASHBOARD_PATH", cls.dashboard_path),
            
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Create config from environment first, then override with file values
            config = cls.from_env()
            
            # Update with file values
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            return config
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading config file {config_path}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "core": {
                "zmq_endpoint": self.zmq_endpoint,
                "ws_port": self.ws_port,
                "db_path": self.db_path,
                "max_buffer": self.max_buffer,
                "debug": self.debug,
            },
            "gpio": {
                "mode": self.gpio_mode,
            },
            "simulators": {
                "sensors": self.simulate_sensors,
                "i2c": self.i2c_simulator,
                "i2s": self.i2s_simulator,
                "rs485": self.rs485_simulator,
            },
            "web": {
                "enabled": self.web_enabled,
                "static_path": self.static_path,
                "dashboard_path": self.dashboard_path,
            },
            "logging": {
                "level": self.log_level,
                "format": self.log_format,
            }
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file"""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def get_zmq_address(self) -> str:
        """Get ZeroMQ address for binding/connecting"""
        return self.zmq_endpoint
    
    def get_web_address(self) -> str:
        """Get web server address"""
        return f"http://localhost:{self.ws_port}"
    
    def get_websocket_address(self) -> str:
        """Get WebSocket address"""
        return f"ws://localhost:{self.ws_port}/ws"
    
    def is_simulator_mode(self) -> bool:
        """Check if running in simulator mode"""
        return self.gpio_mode == "SIMULATOR"
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        if self.ws_port < 1 or self.ws_port > 65535:
            errors.append(f"Invalid port: {self.ws_port}")
        
        if self.max_buffer < 100:
            errors.append(f"Buffer too small: {self.max_buffer}")
        
        if self.gpio_mode not in ["SIMULATOR", "BCM", "BOARD"]:
            errors.append(f"Invalid GPIO mode: {self.gpio_mode}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        return True
