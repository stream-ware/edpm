"""
EDPM Lite - Minimal universal client
Works with ZeroMQ IPC or WebSocket
"""
import json
import time
import os
import sqlite3
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict

# Try ZeroMQ, fallback to WebSocket
try:
    import zmq
    HAS_ZMQ = True
except ImportError:
    HAS_ZMQ = False
    
try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False
    websocket = None

@dataclass
class Message:
    v: int = 1
    t: str = "log"
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
            self.src = f"{os.getpid()}"
        if self.d is None:
            self.d = {}
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(',', ':'))
    
    @classmethod
    def from_json(cls, data: str) -> 'Message':
        return cls(**json.loads(data))

class EDPMLite:
    """Simplified EDPM client for any language"""
    
    def __init__(self, 
                 endpoint: str = "ipc:///tmp/edpm.ipc",
                 use_zmq: bool = True):
        self.endpoint = endpoint
        self.use_zmq = use_zmq and HAS_ZMQ
        self.socket = None
        self.ws = None
        self.callbacks = {}
        
        # Initialize connection
        if self.use_zmq:
            self._init_zmq()
        else:
            self._init_ws()
        
        # Local SQLite buffer (optional)
        self.db = sqlite3.connect(':memory:')
        self._init_db()
    
    def _init_zmq(self):
        """Initialize ZeroMQ connection"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.endpoint)
    
    def _init_ws(self):
        """Initialize WebSocket connection"""
        if not HAS_WS or websocket is None:
            print("Warning: WebSocket not available")
            return
        ws_endpoint = self.endpoint.replace("ipc://", "ws://localhost:8080/")
        self.ws = websocket.WebSocket()
        try:
            self.ws.connect(ws_endpoint)
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.ws = None
    
    def _init_db(self):
        """Initialize local buffer database"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buffer (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                type TEXT,
                data TEXT
            )
        ''')
    
    def send(self, msg: Message) -> Optional[Message]:
        """Send message and get response"""
        json_msg = msg.to_json()
        
        # Buffer locally first
        self._buffer_message(msg)
        
        try:
            if self.use_zmq and self.socket:
                self.socket.send_string(json_msg)
                response = self.socket.recv_string()
                return Message.from_json(response)
            elif self.ws:
                self.ws.send(json_msg)
                response = self.ws.recv()
                return Message.from_json(response)
        except Exception as e:
            print(f"Send error: {e}")
            return None
    
    def _buffer_message(self, msg: Message):
        """Buffer message locally"""
        cursor = self.db.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO buffer VALUES (?, ?, ?, ?)',
            (msg.id, msg.ts, msg.t, json.dumps(msg.d))
        )
    
    # Simplified API methods
    def log(self, level: str, message: str, **metadata):
        """Simple logging"""
        msg = Message(
            t="log",
            d={"level": level, "msg": message, **metadata}
        )
        return self.send(msg)
    
    def cmd(self, action: str, **params):
        """Send command"""
        msg = Message(
            t="cmd",
            d={"action": action, **params}
        )
        return self.send(msg)
    
    def event(self, event_name: str, **data):
        """Emit event"""
        msg = Message(
            t="evt",
            d={"event": event_name, **data}
        )
        return self.send(msg)
    
    def on(self, event_name: str, callback: Callable):
        """Register event handler"""
        self.callbacks[event_name] = callback
    
    # GPIO specific helpers
    def gpio_set(self, pin: int, value: int):
        """Set GPIO pin"""
        return self.cmd("gpio_set", pin=pin, value=value)
    
    def gpio_get(self, pin: int):
        """Get GPIO pin value"""
        response = self.cmd("gpio_get", pin=pin)
        if response and response.d.get("status") == "ok":
            return response.d.get("value")
        return None
    
    def gpio_pwm(self, pin: int, frequency: float, duty_cycle: float):
        """Start PWM on pin"""
        return self.cmd("gpio_pwm", 
                       pin=pin, 
                       frequency=frequency,
                       duty_cycle=duty_cycle)

# Singleton instance
_client = None

def get_client(endpoint: str = None) -> EDPMLite:
    """Get or create singleton client"""
    global _client
    if _client is None:
        _client = EDPMLite(endpoint or os.getenv("EDPM_ENDPOINT", "ipc:///tmp/edpm.ipc"))
    return _client

# Simple functional API
def log(level: str, message: str, **metadata):
    """Quick log function"""
    return get_client().log(level, message, **metadata)

def cmd(action: str, **params):
    """Quick command function"""
    return get_client().cmd(action, **params)

def gpio_set(pin: int, value: int):
    """Quick GPIO set"""
    return get_client().gpio_set(pin, value)
