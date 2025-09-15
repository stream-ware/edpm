"""
EDPM Client Module
Universal client for EDPM communication supporting ZeroMQ and WebSocket transports.
"""

import json
import time
import os
import sqlite3
import logging
from typing import Optional, Dict, Any, Callable, Union
from .message import Message, MessageType
from .config import Config

# Optional dependencies
try:
    import zmq
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False
    zmq = None

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False
    websocket = None

logger = logging.getLogger(__name__)


class EDPMClient:
    """
    EDPM Universal Client
    
    Supports both ZeroMQ and WebSocket communication with automatic transport detection
    and fallback capabilities. Provides simple interface for sending commands, logs,
    and events to EDPM server.
    """
    
    def __init__(self, endpoint: str = None, config: Config = None, use_zmq: bool = True):
        """
        Initialize EDPM Client
        
        Args:
            endpoint: Server endpoint (IPC path for ZMQ or WebSocket URL)
            config: Configuration object
            use_zmq: Prefer ZeroMQ over WebSocket if available
        """
        self.config = config or Config.from_env()
        self.endpoint = endpoint or self.config.zmq_endpoint
        self.use_zmq = use_zmq and HAS_ZMQ
        
        # Initialize transport
        self.zmq_context = None
        self.zmq_socket = None
        self.ws_connection = None
        self.connected = False
        
        # Local storage for offline capability
        self.db_path = self.config.db_path
        self._init_storage()
        
        logger.info(f"EDPM Client initialized with endpoint: {self.endpoint}")
    
    def _init_storage(self):
        """Initialize local SQLite storage for message buffering"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    type TEXT,
                    source TEXT,
                    data TEXT,
                    sent BOOLEAN DEFAULT FALSE
                )
            ''')
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to initialize storage: {e}")
    
    def connect(self) -> bool:
        """
        Connect to EDPM server using preferred transport
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.use_zmq and HAS_ZMQ:
            return self._connect_zmq()
        elif HAS_WS:
            return self._connect_websocket()
        else:
            logger.error("No supported transport available (install pyzmq or websocket-client)")
            return False
    
    def _connect_zmq(self) -> bool:
        """Connect using ZeroMQ transport"""
        try:
            self.zmq_context = zmq.Context()
            self.zmq_socket = self.zmq_context.socket(zmq.REQ)
            self.zmq_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.zmq_socket.setsockopt(zmq.SNDTIMEO, 5000)
            self.zmq_socket.connect(self.endpoint)
            
            # Test connection
            test_msg = Message.create_log("info", "Connection test", source="client")
            response = self._send_zmq(test_msg)
            
            self.connected = response is not None
            logger.info(f"ZMQ connection {'successful' if self.connected else 'failed'}")
            return self.connected
            
        except Exception as e:
            logger.error(f"ZMQ connection failed: {e}")
            return False
    
    def _connect_websocket(self) -> bool:
        """Connect using WebSocket transport"""
        try:
            ws_url = f"ws://localhost:{self.config.ws_port}/ws"
            self.ws_connection = websocket.create_connection(ws_url, timeout=5)
            self.connected = True
            logger.info("WebSocket connection successful")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server and cleanup resources"""
        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()
        if self.ws_connection:
            self.ws_connection.close()
        
        self.connected = False
        logger.info("EDPM Client disconnected")
    
    def send(self, message: Message) -> Optional[Message]:
        """
        Send message to server
        
        Args:
            message: Message to send
            
        Returns:
            Response message or None if failed
        """
        if not self.connected:
            # Store message locally for later
            self._store_message(message)
            return None
        
        try:
            if self.use_zmq and self.zmq_socket:
                return self._send_zmq(message)
            elif self.ws_connection:
                return self._send_websocket(message)
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self._store_message(message)
        
        return None
    
    def _send_zmq(self, message: Message) -> Optional[Message]:
        """Send message via ZeroMQ"""
        try:
            self.zmq_socket.send_string(message.to_json())
            response_str = self.zmq_socket.recv_string()
            return Message.from_json(response_str)
        except zmq.Again:
            logger.warning("ZMQ send timeout")
            return None
        except Exception as e:
            logger.error(f"ZMQ send error: {e}")
            return None
    
    def _send_websocket(self, message: Message) -> Optional[Message]:
        """Send message via WebSocket"""
        try:
            self.ws_connection.send(message.to_json())
            response_str = self.ws_connection.recv()
            return Message.from_json(response_str)
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return None
    
    def _store_message(self, message: Message):
        """Store message in local database for offline capability"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                'INSERT INTO messages (timestamp, type, source, data) VALUES (?, ?, ?, ?)',
                (message.timestamp, message.type, message.source, message.to_json())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    def sync_offline_messages(self) -> int:
        """
        Sync stored offline messages to server
        
        Returns:
            Number of messages successfully sent
        """
        if not self.connected:
            return 0
        
        sent_count = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('SELECT id, data FROM messages WHERE sent = FALSE')
            
            for row in cursor.fetchall():
                msg_id, msg_data = row
                try:
                    message = Message.from_json(msg_data)
                    if self.send(message):
                        # Mark as sent
                        conn.execute('UPDATE messages SET sent = TRUE WHERE id = ?', (msg_id,))
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync message {msg_id}: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to sync offline messages: {e}")
        
        logger.info(f"Synced {sent_count} offline messages")
        return sent_count
    
    # Convenience methods for common operations
    
    def log(self, level: str, message: str, **metadata) -> Optional[Message]:
        """Send log message"""
        msg = Message.create_log(level, message, source="client", **metadata)
        return self.send(msg)
    
    def command(self, action: str, **params) -> Optional[Message]:
        """Send command message"""
        msg = Message.create_command(action, source="client", **params)
        return self.send(msg)
    
    def event(self, event_type: str, **data) -> Optional[Message]:
        """Send event message"""
        msg = Message.create_event(event_type, source="client", **data)
        return self.send(msg)
    
    # GPIO convenience methods
    
    def gpio_set(self, pin: int, value: int) -> Optional[Message]:
        """Set GPIO pin value"""
        return self.command("gpio_set", pin=pin, value=value)
    
    def gpio_get(self, pin: int) -> Optional[Message]:
        """Get GPIO pin value"""
        return self.command("gpio_get", pin=pin)
    
    def gpio_toggle(self, pin: int) -> Optional[Message]:
        """Toggle GPIO pin"""
        return self.command("gpio_toggle", pin=pin)
    
    # I2C convenience methods
    
    def i2c_read(self, address: int, register: int = None) -> Optional[Message]:
        """Read from I2C device"""
        params = {"address": address}
        if register is not None:
            params["register"] = register
        return self.command("i2c_read", **params)
    
    def i2c_write(self, address: int, data: Union[int, bytes], register: int = None) -> Optional[Message]:
        """Write to I2C device"""
        params = {"address": address, "data": data}
        if register is not None:
            params["register"] = register
        return self.command("i2c_write", **params)
    
    def i2c_scan(self) -> Optional[Message]:
        """Scan I2C bus for devices"""
        return self.command("i2c_scan")
    
    # Audio convenience methods
    
    def play_tone(self, frequency: float, duration: float = 1.0) -> Optional[Message]:
        """Play audio tone"""
        return self.command("play_tone", frequency=frequency, duration=duration)
    
    def record_audio(self, duration: float = 5.0) -> Optional[Message]:
        """Record audio"""
        return self.command("record_audio", duration=duration)
    
    # RS485/Modbus convenience methods
    
    def modbus_read(self, device_id: int, register: int, count: int = 1) -> Optional[Message]:
        """Read Modbus registers"""
        return self.command("modbus_read", device_id=device_id, register=register, count=count)
    
    def modbus_write(self, device_id: int, register: int, value: int) -> Optional[Message]:
        """Write Modbus register"""
        return self.command("modbus_write", device_id=device_id, register=register, value=value)
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
