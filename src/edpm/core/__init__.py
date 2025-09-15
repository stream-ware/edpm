"""
EDPM Core Module
Core functionality for EDPM framework including messaging, server, and client.
"""

from .message import Message, MessageType
from .client import EDPMClient
from .server import EDPMServer
from .config import Config

__all__ = ["Message", "MessageType", "EDPMClient", "EDPMServer", "Config"]
