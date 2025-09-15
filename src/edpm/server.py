#!/usr/bin/env python3
"""
EDPM Integrated Server
Main server combining all EDPM modules for complete industrial IoT functionality.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional

from .core.config import Config
from .core.server import EDPMServer
from .core.message import Message
from .web.dashboard import DashboardServer
from .protocols.gpio import GPIOHandler
from .protocols.i2c import I2CHandler
from .protocols.i2s import I2SHandler
from .protocols.rs485 import RS485Handler

logger = logging.getLogger(__name__)


class EDPMIntegratedServer:
    """
    EDPM Integrated Server
    
    Combines the core EDPM server with web dashboard and all protocol handlers
    for a complete industrial IoT edge processing solution.
    """
    
    def __init__(self, config: Config = None):
        """Initialize integrated EDPM server"""
        self.config = config or Config.from_env()
        self.running = False
        
        # Core server components
        self.edpm_server = None
        self.dashboard_server = None
        
        # Protocol handlers
        self.gpio_handler = None
        self.i2c_handler = None
        self.i2s_handler = None
        self.rs485_handler = None
        
        logger.info("EDPM Integrated Server initialized")
    
    async def start(self):
        """Start all server components"""
        try:
            logger.info("Starting EDPM Integrated Server...")
            
            # Initialize protocol handlers
            await self._init_protocol_handlers()
            
            # Create core EDPM server with protocol handlers
            self.edpm_server = EDPMServer(self.config)
            self.edpm_server.protocol_handlers = {
                'gpio': self.gpio_handler,
                'i2c': self.i2c_handler,
                'i2s': self.i2s_handler,
                'rs485': self.rs485_handler
            }
            
            # Start core server
            server_task = asyncio.create_task(self.edpm_server.start())
            
            # Start web dashboard if enabled
            dashboard_task = None
            if self.config.web_enabled:
                self.dashboard_server = DashboardServer(self.config)
                # Connect dashboard to EDPM server for real-time data
                self.dashboard_server.edpm_client = self.edpm_server
                dashboard_task = asyncio.create_task(
                    self.dashboard_server.start(host="0.0.0.0", port=self.config.web_port)
                )
                logger.info(f"Web dashboard started on http://localhost:{self.config.web_port}")
            
            self.running = True
            logger.info("EDPM Integrated Server started successfully")
            
            # Wait for both servers
            tasks = [server_task]
            if dashboard_task:
                tasks.append(dashboard_task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Failed to start EDPM Integrated Server: {e}")
            await self.stop()
            raise
    
    async def _init_protocol_handlers(self):
        """Initialize all protocol handlers"""
        try:
            logger.info("Initializing protocol handlers...")
            
            # GPIO Handler
            self.gpio_handler = GPIOHandler(self.config)
            logger.info("GPIO handler initialized")
            
            # I2C Handler
            self.i2c_handler = I2CHandler(self.config)
            logger.info("I2C handler initialized")
            
            # I2S Handler
            self.i2s_handler = I2SHandler(self.config)
            logger.info("I2S handler initialized")
            
            # RS485 Handler
            self.rs485_handler = RS485Handler(self.config)
            logger.info("RS485 handler initialized")
            
            logger.info("All protocol handlers initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize protocol handlers: {e}")
            raise
    
    async def stop(self):
        """Stop all server components"""
        if not self.running:
            return
        
        logger.info("Stopping EDPM Integrated Server...")
        self.running = False
        
        try:
            # Stop dashboard server
            if self.dashboard_server:
                await self.dashboard_server.stop()
                logger.info("Dashboard server stopped")
            
            # Stop core EDPM server
            if self.edpm_server:
                await self.edpm_server.stop()
                logger.info("EDPM core server stopped")
            
            # Cleanup protocol handlers
            await self._cleanup_protocol_handlers()
            
            logger.info("EDPM Integrated Server stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping EDPM Integrated Server: {e}")
    
    async def _cleanup_protocol_handlers(self):
        """Cleanup all protocol handlers"""
        try:
            if self.gpio_handler:
                await self.gpio_handler.cleanup()
                logger.debug("GPIO handler cleaned up")
            
            if self.i2c_handler:
                await self.i2c_handler.cleanup()
                logger.debug("I2C handler cleaned up")
            
            if self.i2s_handler:
                await self.i2s_handler.cleanup()
                logger.debug("I2S handler cleaned up")
            
            if self.rs485_handler:
                await self.rs485_handler.cleanup()
                logger.debug("RS485 handler cleaned up")
            
            logger.info("All protocol handlers cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up protocol handlers: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive server status"""
        status = {
            'server_running': self.running,
            'config': {
                'endpoint': self.config.endpoint,
                'web_port': self.config.web_port,
                'web_enabled': self.config.web_enabled,
                'debug': self.config.debug
            },
            'components': {},
            'protocols': {}
        }
        
        try:
            # Core server status
            if self.edpm_server:
                status['components']['edpm_server'] = await self.edpm_server.get_status()
            
            # Dashboard server status
            if self.dashboard_server:
                status['components']['dashboard_server'] = await self.dashboard_server.get_status()
            
            # Protocol handler statuses
            if self.gpio_handler:
                status['protocols']['gpio'] = await self.gpio_handler.get_status()
            
            if self.i2c_handler:
                status['protocols']['i2c'] = await self.i2c_handler.get_status()
            
            if self.i2s_handler:
                status['protocols']['i2s'] = await self.i2s_handler.get_status()
            
            if self.rs485_handler:
                status['protocols']['rs485'] = await self.rs485_handler.get_status()
        
        except Exception as e:
            logger.error(f"Error getting server status: {e}")
            status['error'] = str(e)
        
        return status
    
    async def handle_message(self, message: Message) -> Message:
        """Handle incoming message and route to appropriate handler"""
        try:
            if self.edpm_server:
                return await self.edpm_server.handle_message(message)
            else:
                raise Exception("EDPM server not initialized")
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return Message.error(f"Server error: {e}")


async def main():
    """Main entry point for integrated server"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting EDPM Integrated Server")
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Create and start integrated server
        server = EDPMIntegratedServer(config)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(server.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start server
        await server.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("EDPM Integrated Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
