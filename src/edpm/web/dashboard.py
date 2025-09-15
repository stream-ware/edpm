"""
EDPM Web Dashboard Server
WebSocket and HTTP server for real-time Web UI Dashboard.
"""

import asyncio
import json
import os
import time
import logging
from typing import Dict, Any, Set, Optional
from pathlib import Path

from ..core.message import Message, MessageType
from ..core.config import Config

# Optional dependencies
try:
    from aiohttp import web, WSMsgType
    import aiofiles
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    web = None

logger = logging.getLogger(__name__)


class DashboardServer:
    """
    EDPM Web Dashboard Server
    
    Provides HTTP server for static assets and WebSocket server for real-time
    communication with the Web UI Dashboard.
    """
    
    def __init__(self, config: Config = None, edpm_server=None):
        """Initialize Dashboard Server"""
        if not HAS_WEB:
            raise ImportError("aiohttp required for Web Dashboard. Install with: pip install aiohttp")
        
        self.config = config or Config.from_env()
        self.edpm_server = edpm_server
        self.app = web.Application()
        self.websocket_clients: Set[web.WebSocketResponse] = set()
        self.running = False
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Dashboard Server initialized on port {self.config.ws_port}")
    
    def _setup_routes(self):
        """Setup HTTP and WebSocket routes"""
        # Static file serving
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/dashboard', self.handle_dashboard)
        self.app.router.add_get('/ws', self.handle_websocket)
        
        # API endpoints
        self.app.router.add_get('/api/stats', self.handle_api_stats)
        self.app.router.add_get('/api/status', self.handle_api_status)
        
        # Static assets
        self.app.router.add_static('/static/', path='static/', name='static')
    
    async def start(self):
        """Start the dashboard server"""
        if not HAS_WEB:
            logger.error("Cannot start dashboard server: aiohttp not available")
            return
        
        self.running = True
        
        # Create and start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', self.config.ws_port)
        await site.start()
        
        logger.info(f"Dashboard server started on http://localhost:{self.config.ws_port}")
        
        # Start periodic tasks
        asyncio.create_task(self._periodic_broadcast())
        
        return runner
    
    async def stop(self):
        """Stop the dashboard server"""
        self.running = False
        
        # Close all WebSocket connections
        for ws in list(self.websocket_clients):
            await ws.close()
        
        logger.info("Dashboard server stopped")
    
    async def handle_index(self, request):
        """Handle root path - redirect to dashboard"""
        return web.HTTPFound('/dashboard')
    
    async def handle_dashboard(self, request):
        """Serve the dashboard HTML file"""
        try:
            # Try to find dashboard file
            dashboard_paths = [
                Path(self.config.dashboard_path),
                Path("web/dashboard.html"),
                Path("../web/dashboard.html"),
                Path("../../web/dashboard.html")
            ]
            
            dashboard_file = None
            for path in dashboard_paths:
                if path.exists():
                    dashboard_file = path
                    break
            
            if dashboard_file:
                async with aiofiles.open(dashboard_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                return web.Response(text=content, content_type='text/html')
            else:
                # Return basic fallback HTML
                return web.Response(
                    text=self._get_fallback_html(),
                    content_type='text/html'
                )
                
        except Exception as e:
            logger.error(f"Error serving dashboard: {e}")
            return web.Response(
                text=f"<h1>Dashboard Error</h1><p>{e}</p>",
                content_type='text/html',
                status=500
            )
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_clients.add(ws)
        client_id = f"{request.remote}:{id(ws)}"
        logger.info(f"WebSocket client connected: {client_id}")
        
        try:
            # Send initial connection message
            await self._send_to_client(ws, {
                'type': 'connection',
                'status': 'connected',
                'timestamp': time.time()
            })
            
            # Handle incoming messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from WebSocket client: {e}")
                        await self._send_error(ws, f"Invalid JSON: {e}")
                        
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_clients.discard(ws)
            logger.info(f"WebSocket client disconnected: {client_id}")
        
        return ws
    
    async def _handle_websocket_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            msg_type = data.get('t', 'unknown')
            
            if msg_type == 'cmd':
                # Command message - forward to EDPM server
                await self._handle_command(ws, data)
            elif msg_type == 'ping':
                # Ping message - respond with pong
                await self._send_to_client(ws, {'type': 'pong', 'timestamp': time.time()})
            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")
                await self._send_error(ws, f"Unknown message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(ws, str(e))
    
    async def _handle_command(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle command from WebSocket client"""
        if not self.edpm_server:
            await self._send_error(ws, "EDPM server not available")
            return
        
        try:
            # Create EDPM message from WebSocket data
            message = Message(
                version=data.get('v', 1),
                type=MessageType.COMMAND.value,
                source='dashboard',
                data=data.get('d', {})
            )
            
            # Process message through EDPM server
            response = await self.edpm_server.process_message(message)
            
            # Send response back to client
            response_data = {
                'type': 'response',
                'original': data,
                'response': {
                    'status': response.data.get('status', 'unknown'),
                    'result': response.data.get('result'),
                    'error': response.data.get('error')
                },
                'timestamp': time.time()
            }
            
            await self._send_to_client(ws, response_data)
            
        except Exception as e:
            logger.error(f"Command handling error: {e}")
            await self._send_error(ws, f"Command failed: {e}")
    
    async def _send_to_client(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Send data to WebSocket client"""
        try:
            await ws.send_str(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending to WebSocket client: {e}")
    
    async def _send_error(self, ws: web.WebSocketResponse, error: str):
        """Send error message to WebSocket client"""
        await self._send_to_client(ws, {
            'type': 'error',
            'error': error,
            'timestamp': time.time()
        })
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast event to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message = {
            'type': 'event',
            'data': event_data,
            'timestamp': time.time()
        }
        
        # Send to all clients
        disconnected_clients = set()
        for ws in self.websocket_clients:
            try:
                await self._send_to_client(ws, message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(ws)
        
        # Remove disconnected clients
        for ws in disconnected_clients:
            self.websocket_clients.discard(ws)
    
    async def broadcast_system_stats(self):
        """Broadcast system statistics to all clients"""
        if not self.edpm_server:
            return
        
        stats = self.edpm_server.get_stats()
        await self.broadcast_event({
            'event': 'system_stats',
            'stats': stats
        })
    
    async def _periodic_broadcast(self):
        """Periodic broadcast of system information"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Every 10 seconds
                
                if self.websocket_clients:
                    # Broadcast system stats
                    await self.broadcast_system_stats()
                    
                    # Broadcast simulated data for demo
                    await self._broadcast_demo_data()
                    
            except Exception as e:
                logger.error(f"Periodic broadcast error: {e}")
    
    async def _broadcast_demo_data(self):
        """Broadcast simulated data for demonstration"""
        import random
        
        # Simulate GPIO data
        await self.broadcast_event({
            'event': 'gpio_change',
            'pin': 17,
            'value': random.choice([0, 1]),
            'timestamp': time.time()
        })
        
        # Simulate I2C sensor data
        await self.broadcast_event({
            'event': 'sensor_reading',
            'sensor': 'BME280',
            'temperature': 20 + random.uniform(-5, 15),
            'humidity': 50 + random.uniform(-10, 20),
            'pressure': 1013 + random.uniform(-20, 20),
            'timestamp': time.time()
        })
        
        # Simulate audio level
        await self.broadcast_event({
            'event': 'audio_level',
            'level': random.uniform(0, 100),
            'frequency': 440,
            'timestamp': time.time()
        })
    
    async def handle_api_stats(self, request):
        """API endpoint for server statistics"""
        if not self.edpm_server:
            return web.json_response({'error': 'EDPM server not available'}, status=503)
        
        try:
            stats = self.edpm_server.get_stats()
            return web.json_response(stats)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def handle_api_status(self, request):
        """API endpoint for server status"""
        status = {
            'dashboard_running': self.running,
            'websocket_clients': len(self.websocket_clients),
            'edpm_server_available': self.edpm_server is not None,
            'timestamp': time.time()
        }
        return web.json_response(status)
    
    def _get_fallback_html(self) -> str:
        """Return fallback HTML when dashboard file is not found"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EDPM Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #1e1e1e; color: white; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 20px; background: #2d2d30; border-radius: 8px; margin: 20px 0; }
        .error { background: #d73a49; }
        .success { background: #28a745; }
        button { padding: 10px 20px; background: #0366d6; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 10px; }
        #logs { background: #2d2d30; padding: 20px; border-radius: 8px; height: 300px; overflow-y: auto; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 EDPM Dashboard</h1>
        <div class="status" id="status">
            <h2>Connection Status</h2>
            <p>WebSocket: <span id="ws-status">Connecting...</span></p>
            <p>Server: <span id="server-status">Unknown</span></p>
        </div>
        
        <div class="status">
            <h2>Quick Actions</h2>
            <button onclick="sendCommand('ping')">Ping Server</button>
            <button onclick="sendCommand('get_stats')">Get Stats</button>
            <button onclick="sendCommand('gpio_toggle', {pin: 17})">Toggle GPIO 17</button>
            <button onclick="sendCommand('i2c_scan')">Scan I2C Bus</button>
        </div>
        
        <div class="status">
            <h2>Live Logs</h2>
            <div id="logs"></div>
        </div>
    </div>

    <script>
        let ws = null;
        
        function connect() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                updateStatus('ws-status', 'Connected', 'success');
                addLog('WebSocket connected');
            };
            
            ws.onclose = function() {
                updateStatus('ws-status', 'Disconnected', 'error');
                addLog('WebSocket disconnected');
                setTimeout(connect, 5000); // Retry
            };
            
            ws.onerror = function(error) {
                updateStatus('ws-status', 'Error', 'error');
                addLog('WebSocket error: ' + error);
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
        }
        
        function updateStatus(elementId, text, className) {
            const element = document.getElementById(elementId);
            element.textContent = text;
            element.className = className;
        }
        
        function addLog(message) {
            const logs = document.getElementById('logs');
            const timestamp = new Date().toLocaleTimeString();
            logs.innerHTML += `<div>[${timestamp}] ${message}</div>`;
            logs.scrollTop = logs.scrollHeight;
        }
        
        function handleMessage(data) {
            addLog(`Received: ${JSON.stringify(data)}`);
            
            if (data.type === 'response') {
                addLog(`Command response: ${JSON.stringify(data.response)}`);
            } else if (data.type === 'event') {
                addLog(`Event: ${data.data.event || 'unknown'}`);
            }
        }
        
        function sendCommand(action, params = {}) {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                addLog('WebSocket not connected');
                return;
            }
            
            const message = {
                v: 1,
                t: 'cmd',
                d: {
                    action: action,
                    ...params
                }
            };
            
            ws.send(JSON.stringify(message));
            addLog(`Sent command: ${action}`);
        }
        
        // Start connection
        connect();
    </script>
</body>
</html>
        """
