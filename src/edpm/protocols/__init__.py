"""
EDPM Protocols Module
Protocol handlers for GPIO, I2C, I2S, and RS485/Modbus communications.
"""

from .gpio import GPIOHandler
from .i2c import I2CHandler  
from .i2s import I2SHandler
from .rs485 import RS485Handler

__all__ = ["GPIOHandler", "I2CHandler", "I2SHandler", "RS485Handler"]
