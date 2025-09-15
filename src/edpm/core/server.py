"""
EDPM Server Module
Main EDPM server with ZeroMQ and WebSocket support for protocol handling.
"""

import asyncio
import json
import time
import sqlite3
import os
import logging
from typing import Dict, Any, Optional, Set
from .message import Message, MessageType
from .config import Config

# Optional dependencies
try:
    import zmq
    import zmq.asyncio
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False
    zmq = None

try:
    from aiohttp import web
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    web = None

logger = logging.getLogger(__name__)


class EDPMServer:
    """
    EDPM Lite Server
    
    Main server component that handles ZeroMQ REP socket for client communication
    and manages protocol handlers for GPIO, I2C, I2S, and RS485/Modbus.
    """
    
    def __init__(self, config: Config = None):
        """Initialize EDPM Server"""
        self.config = config or Config.from_env()
        self.running = True
        self.clients = set()
        self.protocol_handlers = {}
        self.stats = {
            'messages_processed': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Initialize components
        self._init_database()
        self._init_zmq()
        
        logger.info(f"EDPM Server initialized - ZMQ: {self.config.zmq_endpoint}")
    
    def _init_database(self):
        """Initialize SQLite database for message storage"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.config.db_path), exist_ok=True)
            
            self.db = sqlite3.connect(self.config.db_path, check_same_thread=False)
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    type TEXT,
                    source TEXT,
                    data TEXT,
                    processed BOOLEAN DEFAULT TRUE
                )
            ''')
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    event_type TEXT,
                    source TEXT,
                    data TEXT
                )
            ''')
            self.db.commit()
            logger.info(f"Database initialized: {self.config.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _init_zmq(self):
        """Initialize ZeroMQ context and socket"""
        if not HAS_ZMQ:
            logger.warning("ZeroMQ not available, server will run in WebSocket-only mode")
            self.zmq_context = None
            self.zmq_socket = None
            return
        
        try:
            self.zmq_context = zmq.asyncio.Context()
            self.zmq_socket = self.zmq_context.socket(zmq.REP)
            self.zmq_socket.bind(self.config.zmq_endpoint)
            logger.info(f"ZeroMQ server bound to {self.config.zmq_endpoint}")
            
        except Exception as e:
            logger.error(f"ZeroMQ initialization failed: {e}")
            self.zmq_context = None
            self.zmq_socket = None
    
    def add_protocol_handler(self, name: str, handler):
        """Add protocol handler"""
        self.protocol_handlers[name] = handler
        logger.info(f"Added protocol handler: {name}")
    
    def remove_protocol_handler(self, name: str):
        """Remove protocol handler"""
        if name in self.protocol_handlers:
            del self.protocol_handlers[name]
            logger.info(f"Removed protocol handler: {name}")
    
    async def start(self):
        """Start the EDPM server"""
        logger.info("Starting EDPM Server...")
        
        tasks = []
        
        # Start ZeroMQ server if available
        if self.zmq_socket:
            tasks.append(asyncio.create_task(self._zmq_server_loop()))
        
        # Start periodic tasks
        tasks.append(asyncio.create_task(self._stats_update_loop()))
        tasks.append(asyncio.create_task(self._cleanup_loop()))
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the EDPM server"""
        logger.info("Stopping EDPM Server...")
        self.running = False
        
        # Close ZeroMQ resources
        if self.zmq_socket:
            self.zmq_socket.close()
        if self.zmq_context:
            self.zmq_context.term()
        
        # Close database
        if hasattr(self, 'db'):
            self.db.close()
        
        # Cleanup protocol handlers
        for name, handler in self.protocol_handlers.items():
            if hasattr(handler, 'cleanup'):
                try:
                    await handler.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")
        
        logger.info("EDPM Server stopped")
    
    async def _zmq_server_loop(self):
        """Main ZeroMQ server loop"""
        logger.info("ZeroMQ server loop started")
        
        while self.running:
            try:
                # Receive message with timeout
                try:
                    message_str = await asyncio.wait_for(
                        self.zmq_socket.recv_string(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process message
                response = await self._process_message_string(message_str)
                
                # Send response
                await self.zmq_socket.send_string(response.to_json())
                
            except Exception as e:
                logger.error(f"ZeroMQ server error: {e}")
                # Send error response
                error_response = Message.create_response(
                    "error", 
                    source="server",
                    error=str(e)
                )
                try:
                    await self.zmq_socket.send_string(error_response.to_json())
                except:
                    pass
    
    async def _process_message_string(self, message_str: str) -> Message:
        """Process incoming message string"""
        try:
            message = Message.from_json(message_str)
            return await self.process_message(message)
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return Message.create_response(
                "error",
                source="server", 
                error=f"Message processing failed: {e}"
            )
    
    async def process_message(self, message: Message) -> Message:
        """
        Process incoming message and return response
        
        Args:
            message: Incoming message to process
            
        Returns:
            Response message
        """
        self.stats['messages_processed'] += 1
        
        try:
            # Store message in database
            self._store_message(message)
            
            # Route message based on type
            if message.is_log():
                return await self._handle_log_message(message)
            elif message.is_command():
                return await self._handle_command_message(message)
            elif message.is_event():
                return await self._handle_event_message(message)
            else:
                return Message.create_response(
                    "error",
                    source="server",
                    error=f"Unknown message type: {message.type}"
                )
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing message: {e}")
            return Message.create_response(
                "error",
                source="server",
                error=str(e)
            )
    
    async def _handle_log_message(self, message: Message) -> Message:
        """Handle log message"""
        level = message.data.get('level', 'info')
        msg = message.data.get('msg', '')
        
        # Log to Python logger
        getattr(logger, level.lower(), logger.info)(f"[{message.source}] {msg}")
        
        return Message.create_response("ok", source="server")
    
    async def _handle_command_message(self, message: Message) -> Message:
        """Handle command message"""
        action = message.data.get('action')
        if not action:
            return Message.create_response(
                "error",
                source="server",
                error="Missing action in command"
            )
        
        # Route to appropriate protocol handler
        try:
            if action.startswith('gpio_'):
                return await self._handle_gpio_command(action, message.data)
            elif action.startswith('i2c_'):
                return await self._handle_i2c_command(action, message.data)
            elif action.startswith('i2s_') or action in ['play_tone', 'record_audio']:
                return await self._handle_i2s_command(action, message.data)
            elif action.startswith('modbus_') or action.startswith('rs485_'):
                return await self._handle_rs485_command(action, message.data)
            else:
                return await self._handle_generic_command(action, message.data)
                
        except Exception as e:
            return Message.create_response(
                "error",
                source="server",
                error=f"Command execution failed: {e}"
            )
    
    async def _handle_event_message(self, message: Message) -> Message:
        """Handle event message"""
        event_type = message.data.get('event')
        
        # Store event in database
        self._store_event(message)
        
        # Broadcast to clients if needed
        await self._broadcast_event(message)
        
        return Message.create_response("ok", source="server")
    
    async def _handle_gpio_command(self, action: str, data: Dict[str, Any]) -> Message:
        """Handle GPIO command"""
        handler = self.protocol_handlers.get('gpio')
        if not handler:
            return Message.create_response(
                "error",
                source="server", 
                error="GPIO handler not available"
            )
        
        try:
            result = await handler.handle_command(action, data)
            return Message.create_response("ok", source="server", result=result)
        except Exception as e:
            return Message.create_response(
                "error",
                source="server",
                error=f"GPIO command failed: {e}"
            )
    
    async def _handle_i2c_command(self, action: str, data: Dict[str, Any]) -> Message:
        """Handle I2C command"""
        handler = self.protocol_handlers.get('i2c')
        if not handler:
            return Message.create_response(
                "error",
                source="server",
                error="I2C handler not available"
            )
        
        try:
            result = await handler.handle_command(action, data)
            return Message.create_response("ok", source="server", result=result)
        except Exception as e:
            return Message.create_response(
                "error",
                source="server", 
                error=f"I2C command failed: {e}"
            )
    
    async def _handle_i2s_command(self, action: str, data: Dict[str, Any]) -> Message:
        """Handle I2S command"""
        handler = self.protocol_handlers.get('i2s')
        if not handler:
            return Message.create_response(
                "error",
                source="server",
                error="I2S handler not available"
            )
        
        try:
            result = await handler.handle_command(action, data)
            return Message.create_response("ok", source="server", result=result)
        except Exception as e:
            return Message.create_response(
                "error",
                source="server",
                error=f"I2S command failed: {e}"
            )
    
    async def _handle_rs485_command(self, action: str, data: Dict[str, Any]) -> Message:
        """Handle RS485 command"""
        handler = self.protocol_handlers.get('rs485')
        if not handler:
            return Message.create_response(
                "error",
                source="server",
                error="RS485 handler not available"
            )
        
        try:
            result = await handler.handle_command(action, data)
            return Message.create_response("ok", source="server", result=result)
        except Exception as e:
            return Message.create_response(
                "error",
                source="server", 
                error=f"RS485 command failed: {e}"
            )
    
    async def _handle_generic_command(self, action: str, data: Dict[str, Any]) -> Message:
        """Handle generic command"""
        if action == "get_stats":
            return Message.create_response("ok", source="server", stats=self.get_stats())
        elif action == "ping":
            return Message.create_response("ok", source="server", message="pong")
        else:
            return Message.create_response(
                "error",
                source="server",
                error=f"Unknown command: {action}"
            )
    
    def _store_message(self, message: Message):
        """Store message in database"""
        try:
            self.db.execute(
                'INSERT INTO messages (timestamp, type, source, data) VALUES (?, ?, ?, ?)',
                (message.timestamp, message.type, message.source, message.to_json())
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    def _store_event(self, message: Message):
        """Store event in database"""
        try:
            event_type = message.data.get('event', 'unknown')
            self.db.execute(
                'INSERT INTO events (timestamp, event_type, source, data) VALUES (?, ?, ?, ?)',
                (message.timestamp, event_type, message.source, message.to_json())
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
    
    async def _broadcast_event(self, message: Message):
        """Broadcast event to connected clients"""
        # This will be implemented by web server component
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            'messages_processed': self.stats['messages_processed'],
            'errors': self.stats['errors'],
            'uptime': uptime,
            'clients_connected': len(self.clients),
            'protocol_handlers': list(self.protocol_handlers.keys()),
            'config': {
                'zmq_endpoint': self.config.zmq_endpoint,
                'ws_port': self.config.ws_port,
                'debug': self.config.debug,
                'gpio_mode': self.config.gpio_mode
            }
        }
    
    async def _stats_update_loop(self):
        """Periodic stats update loop"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Update every minute
                stats = self.get_stats()
                logger.debug(f"Server stats: {stats}")
            except Exception as e:
                logger.error(f"Stats update error: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup loop"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                await self._cleanup_old_messages()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _cleanup_old_messages(self):
        """Cleanup old messages from database"""
        try:
            # Keep only last 10000 messages
            cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
            
            self.db.execute(
                'DELETE FROM messages WHERE timestamp < ? AND id NOT IN (SELECT id FROM messages ORDER BY timestamp DESC LIMIT ?)',
                (cutoff_time, self.config.max_buffer)
            )
            self.db.execute(
                'DELETE FROM events WHERE timestamp < ? AND id NOT IN (SELECT id FROM events ORDER BY timestamp DESC LIMIT ?)',
                (cutoff_time, self.config.max_buffer)
            )
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")


# Simple GPIO Simulator for testing
class SimpleGPIOSimulator:
    """Simple GPIO simulator for development and testing"""
    
    def __init__(self):
        self.pins = {}
        self.mode = "BCM"
        logger.info("GPIO Simulator initialized")
    
    def setup(self, pin: int, direction: str):
        self.pins[pin] = {
            'direction': direction,
            'value': 0,
            'pwm': None
        }
        return True
    
    def output(self, pin: int, value: int):
        if pin in self.pins:
            self.pins[pin]['value'] = value
            return True
        return False
    
    def input(self, pin: int) -> int:
        if pin in self.pins:
            return self.pins[pin].get('value', 0)
        return 0
    
    def pwm_start(self, pin: int, frequency: float, duty_cycle: float):
        if pin not in self.pins:
            self.setup(pin, 'OUT')
        self.pins[pin]['pwm'] = {
            'frequency': frequency,
            'duty_cycle': duty_cycle,
            'active': True
        }
        return True
    
    def pwm_stop(self, pin: int):
        if pin in self.pins and self.pins[pin].get('pwm'):
            self.pins[pin]['pwm']['active'] = False
            return True
        return False
    
    def cleanup(self):
        self.pins.clear()
