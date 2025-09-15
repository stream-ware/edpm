"""
EDPM Message Module
Defines message structure and types for EDPM communication protocol.
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum


class MessageType(Enum):
    """Message types for EDPM protocol"""
    LOG = "log"
    COMMAND = "cmd" 
    EVENT = "evt"
    RESPONSE = "res"


@dataclass
class Message:
    """
    EDPM Protocol Message
    
    Simple, universal message format for all EDPM communications.
    Compatible with JSON serialization over ZeroMQ, WebSocket, or HTTP.
    """
    version: int = 1
    type: str = MessageType.LOG.value
    id: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[float] = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values after object creation"""
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        # Use short field names for efficient transmission
        msg_dict = {
            "v": self.version,
            "t": self.type,
            "ts": self.timestamp,
            "d": self.data
        }
        
        if self.id:
            msg_dict["id"] = self.id
        if self.source:
            msg_dict["src"] = self.source
            
        return json.dumps(msg_dict)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string"""
        try:
            data = json.loads(json_str)
            return cls(
                version=data.get("v", 1),
                type=data.get("t", MessageType.LOG.value),
                id=data.get("id"),
                source=data.get("src"),
                timestamp=data.get("ts", time.time()),
                data=data.get("d", {})
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid message format: {e}")
    
    @classmethod
    def create_log(cls, level: str, message: str, source: str = None, **metadata) -> 'Message':
        """Create a log message"""
        data = {"level": level, "msg": message}
        data.update(metadata)
        
        return cls(
            type=MessageType.LOG.value,
            source=source,
            data=data
        )
    
    @classmethod  
    def create_command(cls, action: str, source: str = None, **params) -> 'Message':
        """Create a command message"""
        data = {"action": action}
        data.update(params)
        
        return cls(
            type=MessageType.COMMAND.value,
            source=source,
            data=data
        )
    
    @classmethod
    def create_event(cls, event: str, source: str = None, **data) -> 'Message':
        """Create an event message"""
        event_data = {"event": event}
        event_data.update(data)
        
        return cls(
            type=MessageType.EVENT.value,
            source=source, 
            data=event_data
        )
    
    @classmethod
    def create_response(cls, status: str, source: str = None, **data) -> 'Message':
        """Create a response message"""
        response_data = {"status": status}
        response_data.update(data)
        
        return cls(
            type=MessageType.RESPONSE.value,
            source=source,
            data=response_data
        )
    
    def is_log(self) -> bool:
        """Check if message is a log message"""
        return self.type == MessageType.LOG.value
    
    def is_command(self) -> bool:
        """Check if message is a command message"""
        return self.type == MessageType.COMMAND.value
        
    def is_event(self) -> bool:
        """Check if message is an event message"""
        return self.type == MessageType.EVENT.value
        
    def is_response(self) -> bool:
        """Check if message is a response message"""
        return self.type == MessageType.RESPONSE.value
    
    def get_action(self) -> Optional[str]:
        """Get command action if this is a command message"""
        if self.is_command():
            return self.data.get("action")
        return None
    
    def get_event_type(self) -> Optional[str]:
        """Get event type if this is an event message"""
        if self.is_event():
            return self.data.get("event")
        return None
    
    def get_log_level(self) -> Optional[str]:
        """Get log level if this is a log message"""
        if self.is_log():
            return self.data.get("level")
        return None
    
    def __str__(self) -> str:
        """String representation of message"""
        return f"Message({self.type}, src={self.source}, data={self.data})"
