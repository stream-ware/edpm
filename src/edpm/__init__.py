"""
EDPM - Embedded Device Process Manager
A lightweight, modular framework for embedded device management with Web UI Dashboard.
"""

__version__ = "1.0.0"
__author__ = "EDPM Team"
__email__ = "info@edpm.dev"

from .core.client import EDPMClient
from .core.message import Message, MessageType
from .core.server import EDPMServer
from .web.dashboard import DashboardServer
from .protocols.gpio import GPIOHandler
from .protocols.i2c import I2CHandler
from .protocols.i2s import I2SHandler
from .protocols.rs485 import RS485Handler

__all__ = [
    "EDPMClient",
    "EDPMServer", 
    "DashboardServer",
    "Message",
    "MessageType",
    "GPIOHandler",
    "I2CHandler", 
    "I2SHandler",
    "RS485Handler",
]
