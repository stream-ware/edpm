#!/usr/bin/env python3
"""
EDPM Lite Server - Simplified universal server
Single file, minimal dependencies, easy to understand
"""

import asyncio
import json
import time
import sqlite3
import os
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

# Minimal dependencies
try:
    import zmq
    import zmq.asyncio
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False
    print("Warning: ZeroMQ not installed. Install with: pip install pyzmq")

try:
    from aiohttp import web
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    print("Warning: aiohttp not installed. Install with: pip install aiohttp")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EDPM-Lite')

# Configuration with defaults
CONFIG = {
    "zmq_endpoint": os.getenv("EDPM_ENDPOINT", "ipc:///tmp/edpm.ipc"),
    "ws_port": int(os.getenv("EDPM_PORT", "8080")),
    "db_path": os.getenv("EDPM_DB", "/dev/shm/edpm.db"),  # RAM disk on Linux
    "gpio_mode": os.getenv("GPIO_MODE", "SIMULATOR"),
    "max_buffer": int(os.getenv("EDPM_MAX_BUFFER", "10000")),
    "debug": os.getenv("EDPM_DEBUG", "false").lower() == "true"
}

@dataclass
class Message:
    """Universal message format"""
    v: int = 1
    t: str = "log"  # log, cmd, evt, res
    id: str = ""
    src: str = ""
    ts: float = 0
    d: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{time.time():.6f}"
        if not self.ts:
            self.ts = time.time()
        if not self.src:
            self.src = "server"
        if self.d is None:
            self.d = {}
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'))
    
    @classmethod
    def from_json(cls, data: str) -> 'Message':
        return cls(**json.loads(data))

class SimpleGPIOSimulator:
    """Simple GPIO simulator for testing"""
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

class EDPMLiteServer:
    """Main EDPM Lite Server"""
    
    def __init__(self):
        self.config = CONFIG
        self.running = True
        self.clients = set()
        self.event_handlers = {}
        self.stats = {
            'messages_processed': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Initialize components
        self._init_database()
        self._init_gpio()
        
        # ZeroMQ
        if HAS_ZMQ:
            self.zmq_context = zmq.asyncio.Context()
            self.zmq_socket = None
        
        logger.info(f"EDPM Lite Server initialized - Mode: {self.config['gpio_mode']}")
    
    def _init_database(self):
        """Initialize SQLite database"""
        self.db = sqlite3.connect(self.config['db_path'], check_same_thread=False)
        cursor = self.db.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                source TEXT,
                level TEXT,
                message TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                source TEXT,
                event TEXT,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpio_states (
                pin INTEGER PRIMARY KEY,
                value INTEGER,
                mode TEXT,
                last_update REAL
            )
        ''')
        
        self.db.commit()
        logger.info(f"Database initialized at {self.config['db_path']}")
    
    def _init_gpio(self):
        """Initialize GPIO (real or simulator)"""
        if self.config['gpio_mode'] == 'SIMULATOR':
            self.gpio = SimpleGPIOSimulator()
        else:
            try:
                import RPi.GPIO as GPIO
                self.gpio = GPIO
                GPIO.setmode(GPIO.BCM)
                logger.info("Using real RPi.GPIO")
            except ImportError:
                logger.warning("RPi.GPIO not available, using simulator")
                self.gpio = SimpleGPIOSimulator()
    
    async def start(self):
        """Start all server components"""
        tasks = []
        
        if HAS_ZMQ:
            tasks.append(self.start_zmq_server())
        
        if HAS_WEB:
            tasks.append(self.start_web_server())
        
        tasks.append(self.stats_reporter())
        
        if not tasks:
            logger.error("No transport available! Install pyzmq or aiohttp")
            return
        
        await asyncio.gather(*tasks)
    
    async def start_zmq_server(self):
        """ZeroMQ REP socket server"""
        self.zmq_socket = self.zmq_context.socket(zmq.REP)
        
        # Try IPC first, fallback to TCP
        try:
            self.zmq_socket.bind(self.config['zmq_endpoint'])
            logger.info(f"ZMQ server listening on {self.config['zmq_endpoint']}")
        except:
            tcp_endpoint = "tcp://127.0.0.1:5555"
            self.zmq_socket.bind(tcp_endpoint)
            logger.info(f"ZMQ server listening on {tcp_endpoint}")
        
        while self.running:
            try:
                # Receive message
                message_data = await self.zmq_socket.recv_string()
                
                # Process message
                request = Message.from_json(message_data)
                response = await self.process_message(request)
                
                # Send response
                await self.zmq_socket.send_string(response.to_json())
                
            except Exception as e:
                logger.error(f"ZMQ error: {e}")
                self.stats['errors'] += 1
                
                # Send error response
                error_response = Message(
                    t="res",
                    d={"status": "error", "message": str(e)}
                )
                await self.zmq_socket.send_string(error_response.to_json())
    
    async def start_web_server(self):
        """Web server with WebSocket support"""
        app = web.Application()
        
        # Routes
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/ws', self.handle_websocket)
        app.router.add_get('/health', self.handle_health)
        app.router.add_get('/stats', self.handle_stats)
        app.router.add_post('/api/message', self.handle_api_message)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.config['ws_port'])
        await site.start()
        
        logger.info(f"Web server running on http://0.0.0.0:{self.config['ws_port']}")
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def process_message(self, msg: Message) -> Message:
        """Process incoming message and return response"""
        self.stats['messages_processed'] += 1
        
        if self.config['debug']:
            logger.debug(f"Processing: {msg}")
        
        # Route by message type
        if msg.t == "log":
            return await self.handle_log(msg)
        elif msg.t == "cmd":
            return await self.handle_command(msg)
        elif msg.t == "evt":
            return await self.handle_event(msg)
        else:
            return Message(t="res", d={"status": "error", "message": "Unknown message type"})
    
    async def handle_log(self, msg: Message) -> Message:
        """Handle log messages"""
        # Save to database
        cursor = self.db.cursor()
        cursor.execute(
            'INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?)',
            (
                msg.id,
                msg.ts,
                msg.src,
                msg.d.get('level', 'info'),
                msg.d.get('msg', ''),
                json.dumps(msg.d.get('metadata', {}))
            )
        )
        self.db.commit()
        
        # Broadcast to WebSocket clients
        await self.broadcast_to_clients(msg)
        
        return Message(t="res", d={"status": "ok"})
    
    async def handle_command(self, msg: Message) -> Message:
        """Handle command messages"""
        action = msg.d.get('action')
        
        if action == 'gpio_set':
            pin = msg.d.get('pin')
            value = msg.d.get('value')
            
            if pin is None or value is None:
                return Message(t="res", d={"status": "error", "message": "Missing pin or value"})
            
            # Set GPIO
            if hasattr(self.gpio, 'output'):
                self.gpio.output(pin, value)
            else:
                self.gpio.pins[pin] = {'value': value}
            
            # Update database
            cursor = self.db.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO gpio_states VALUES (?, ?, ?, ?)',
                (pin, value, 'OUT', time.time())
            )
            self.db.commit()
            
            return Message(t="res", d={"status": "ok", "pin": pin, "value": value})
        
        elif action == 'gpio_get':
            pin = msg.d.get('pin')
            
            if pin is None:
                return Message(t="res", d={"status": "error", "message": "Missing pin"})
            
            # Read GPIO
            if hasattr(self.gpio, 'input'):
                value = self.gpio.input(pin)
            else:
                value = self.gpio.pins.get(pin, {}).get('value', 0)
            
            return Message(t="res", d={"status": "ok", "pin": pin, "value": value})
        
        elif action == 'gpio_pwm':
            pin = msg.d.get('pin')
            frequency = msg.d.get('frequency', 1000)
            duty_cycle = msg.d.get('duty_cycle', 50)
            
            # Start PWM
            if hasattr(self.gpio, 'pwm_start'):
                self.gpio.pwm_start(pin, frequency, duty_cycle)
            elif hasattr(self.gpio, 'PWM'):
                pwm = self.gpio.PWM(pin, frequency)
                pwm.start(duty_cycle)
            
            return Message(t="res", d={"status": "ok", "pin": pin})
        
        else:
            return Message(t="res", d={"status": "error", "message": f"Unknown action: {action}"})
    
    async def handle_event(self, msg: Message) -> Message:
        """Handle event messages"""
        event_name = msg.d.get('event')
        
        # Save to database
        cursor = self.db.cursor()
        cursor.execute(
            'INSERT INTO events VALUES (?, ?, ?, ?, ?)',
            (msg.id, msg.ts, msg.src, event_name, json.dumps(msg.d))
        )
        self.db.commit()
        
        # Trigger event handlers
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                await handler(msg.d)
        
        # Broadcast to clients
        await self.broadcast_to_clients(msg)
        
        return Message(t="res", d={"status": "ok"})
    
    async def broadcast_to_clients(self, msg: Message):
        """Broadcast message to all WebSocket clients"""
        if not self.clients:
            return
        
        disconnected = set()
        for client in self.clients:
            try:
                await client.send_str(msg.to_json())
            except:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def handle_index(self, request):
        """Serve simple web UI"""
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>EDPM Lite Server</title>
            <style>
                body { font-family: monospace; background: #1a1a1a; color: #0f0; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                h1 { color: #0f0; text-shadow: 0 0 10px #0f0; }
                .stats { background: #000; padding: 20px; border: 1px solid #0f0; border-radius: 5px; }
                .log { background: #000; padding: 10px; margin: 10px 0; border-left: 3px solid #0f0; }
                button { background: #0f0; color: #000; border: none; padding: 10px 20px; cursor: pointer; }
                button:hover { background: #0a0; }
                input { background: #000; color: #0f0; border: 1px solid #0f0; padding: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>EDPM Lite Server</h1>
                <div class="stats">
                    <p>Status: <span id="status">Connecting...</span></p>
                    <p>Messages: <span id="messages">0</span></p>
                    <p>Uptime: <span id="uptime">0s</span></p>
                </div>
                
                <h2>GPIO Control</h2>
                <div>
                    Pin: <input type="number" id="pin" value="17" min="0" max="27">
                    Value: <input type="number" id="value" value="1" min="0" max="1">
                    <button onclick="setGPIO()">Set GPIO</button>
                    <button onclick="getGPIO()">Get GPIO</button>
                </div>
                
                <h2>Logs</h2>
                <div id="logs"></div>
            </div>
            
            <script>
                const ws = new WebSocket('ws://' + window.location.host + '/ws');
                let messageCount = 0;
                const startTime = Date.now();
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = 'Connected';
                    document.getElementById('status').style.color = '#0f0';
                };
                
                ws.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    messageCount++;
                    document.getElementById('messages').textContent = messageCount;
                    
                    if (msg.t === 'log') {
                        addLog(msg.d.level, msg.d.msg);
                    }
                };
                
                ws.onerror = () => {
                    document.getElementById('status').textContent = 'Error';
                    document.getElementById('status').style.color = '#f00';
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = 'Disconnected';
                    document.getElementById('status').style.color = '#fa0';
                };
                
                function setGPIO() {
                    const pin = document.getElementById('pin').value;
                    const value = document.getElementById('value').value;
                    
                    const msg = {
                        v: 1,
                        t: 'cmd',
                        id: Date.now().toString(),
                        src: 'web',
                        ts: Date.now() / 1000,
                        d: {
                            action: 'gpio_set',
                            pin: parseInt(pin),
                            value: parseInt(value)
                        }
                    };
                    
                    ws.send(JSON.stringify(msg));
                    addLog('info', `Set GPIO ${pin} to ${value}`);
                }
                
                function getGPIO() {
                    const pin = document.getElementById('pin').value;
                    
                    const msg = {
                        v: 1,
                        t: 'cmd',
                        id: Date.now().toString(),
                        src: 'web',
                        ts: Date.now() / 1000,
                        d: {
                            action: 'gpio_get',
                            pin: parseInt(pin)
                        }
                    };
                    
                    ws.send(JSON.stringify(msg));
                }
                
                function addLog(level, message) {
                    const logs = document.getElementById('logs');
                    const log = document.createElement('div');
                    log.className = 'log';
                    log.innerHTML = `<span style="color: ${level === 'error' ? '#f00' : '#0f0'}">[${level}]</span> ${message}`;
                    logs.insertBefore(log, logs.firstChild);
                    
                    if (logs.children.length > 10) {
                        logs.removeChild(logs.lastChild);
                    }
                }
                
                // Update uptime
                setInterval(() => {
                    const uptime = Math.floor((Date.now() - startTime) / 1000);
                    document.getElementById('uptime').textContent = uptime + 's';
                }, 1000);
            </script>
        </body>
        </html>
        '''
        return web.Response(text=html, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Process message
                    request_msg = Message.from_json(msg.data)
                    response = await self.process_message(request_msg)
                    await ws.send_str(response.to_json())
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.clients.remove(ws)
        
        return ws
    
    async def handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'ok',
            'uptime': time.time() - self.stats['start_time'],
            'messages': self.stats['messages_processed']
        })
    
    async def handle_stats(self, request):
        """Statistics endpoint"""
        return web.json_response(self.stats)
    
    async def handle_api_message(self, request):
        """REST API endpoint for messages"""
        data = await request.json()
        msg = Message(**data)
        response = await self.process_message(msg)
        return web.json_response(asdict(response))
    
    async def stats_reporter(self):
        """Periodically log statistics"""
        while self.running:
            await asyncio.sleep(60)  # Every minute
            
            uptime = time.time() - self.stats['start_time']
            rate = self.stats['messages_processed'] / uptime if uptime > 0 else 0
            
            logger.info(
                f"Stats: Messages={self.stats['messages_processed']}, "
                f"Rate={rate:.1f}/s, Errors={self.stats['errors']}, "
                f"Clients={len(self.clients)}"
            )
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down EDPM Lite Server...")
        self.running = False
        
        # Close connections
        if HAS_ZMQ and self.zmq_socket:
            self.zmq_socket.close()
        
        # Cleanup GPIO
        if hasattr(self.gpio, 'cleanup'):
            self.gpio.cleanup()
        
        # Close database
        self.db.close()
        
        logger.info("Shutdown complete")

def main():
    """Main entry point"""
    # Show banner
    print("""
    ╔═══════════════════════════════════════╗
    ║       EDPM Lite Server v1.0.0         ║
    ║   Simple • Universal • Lightweight    ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7+ required")
        sys.exit(1)
    
    # Create and start server
    server = EDPMLiteServer()
    
    # Setup signal handlers
    import signal
    
    def signal_handler(sig, frame):
        asyncio.create_task(server.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run server
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
