"""
EDPM GPIO Protocol Handler
GPIO control and monitoring with simulator support.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
from ..core.config import Config

# Optional GPIO dependencies
try:
    import RPi.GPIO as GPIO
    HAS_RPI_GPIO = True
except ImportError:
    HAS_RPI_GPIO = False
    GPIO = None

logger = logging.getLogger(__name__)


class GPIOHandler:
    """
    GPIO Protocol Handler
    
    Handles GPIO operations with support for both real Raspberry Pi hardware
    and simulator mode for development and testing.
    """
    
    def __init__(self, config: Config = None):
        """Initialize GPIO Handler"""
        self.config = config or Config.from_env()
        self.simulator = None
        self.pins_setup = {}
        self.pwm_instances = {}
        
        # Initialize GPIO based on mode
        if self.config.gpio_mode == "SIMULATOR":
            self._init_simulator()
        elif HAS_RPI_GPIO:
            self._init_rpi_gpio()
        else:
            logger.warning("GPIO hardware not available, using simulator")
            self._init_simulator()
        
        logger.info(f"GPIO Handler initialized in {self.config.gpio_mode} mode")
    
    def _init_simulator(self):
        """Initialize GPIO simulator"""
        self.simulator = GPIOSimulator()
        self.mode = "SIMULATOR"
    
    def _init_rpi_gpio(self):
        """Initialize Raspberry Pi GPIO"""
        try:
            if self.config.gpio_mode == "BCM":
                GPIO.setmode(GPIO.BCM)
            else:
                GPIO.setmode(GPIO.BOARD)
            
            GPIO.setwarnings(False)
            self.mode = self.config.gpio_mode
            
        except Exception as e:
            logger.error(f"Failed to initialize RPi.GPIO: {e}")
            logger.warning("Falling back to simulator")
            self._init_simulator()
    
    async def handle_command(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GPIO command
        
        Args:
            action: GPIO action to perform
            data: Command parameters
            
        Returns:
            Result dictionary
        """
        try:
            if action == "gpio_set":
                return await self.set_pin(data.get("pin"), data.get("value"))
            elif action == "gpio_get":
                return await self.get_pin(data.get("pin"))
            elif action == "gpio_toggle":
                return await self.toggle_pin(data.get("pin"))
            elif action == "gpio_setup":
                return await self.setup_pin(
                    data.get("pin"), 
                    data.get("direction", "OUT"),
                    data.get("pull_up_down", "PUD_OFF")
                )
            elif action == "gpio_pwm_start":
                return await self.pwm_start(
                    data.get("pin"),
                    data.get("frequency", 1000),
                    data.get("duty_cycle", 50)
                )
            elif action == "gpio_pwm_stop":
                return await self.pwm_stop(data.get("pin"))
            elif action == "gpio_pwm_change":
                return await self.pwm_change_duty_cycle(
                    data.get("pin"),
                    data.get("duty_cycle")
                )
            elif action == "gpio_status":
                return await self.get_status()
            elif action == "gpio_cleanup":
                return await self.cleanup()
            else:
                raise ValueError(f"Unknown GPIO action: {action}")
                
        except Exception as e:
            logger.error(f"GPIO command error: {e}")
            raise
    
    async def setup_pin(self, pin: int, direction: str = "OUT", pull_up_down: str = "PUD_OFF") -> Dict[str, Any]:
        """Setup GPIO pin"""
        if pin is None:
            raise ValueError("Pin number required")
        
        try:
            if self.simulator:
                result = self.simulator.setup(pin, direction, pull_up_down)
            else:
                # Convert direction string to GPIO constant
                gpio_direction = GPIO.OUT if direction.upper() == "OUT" else GPIO.IN
                
                # Convert pull up/down string to GPIO constant  
                if pull_up_down.upper() == "PUD_UP":
                    gpio_pull = GPIO.PUD_UP
                elif pull_up_down.upper() == "PUD_DOWN":
                    gpio_pull = GPIO.PUD_DOWN
                else:
                    gpio_pull = GPIO.PUD_OFF
                
                GPIO.setup(pin, gpio_direction, pull_up_down=gpio_pull)
                result = True
            
            if result:
                self.pins_setup[pin] = {
                    'direction': direction,
                    'pull_up_down': pull_up_down,
                    'value': 0
                }
            
            return {
                'pin': pin,
                'direction': direction,
                'pull_up_down': pull_up_down,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to setup pin {pin}: {e}")
    
    async def set_pin(self, pin: int, value: Union[int, bool]) -> Dict[str, Any]:
        """Set GPIO pin value"""
        if pin is None:
            raise ValueError("Pin number required")
        if value is None:
            raise ValueError("Pin value required")
        
        # Ensure pin is setup as output
        if pin not in self.pins_setup:
            await self.setup_pin(pin, "OUT")
        
        try:
            int_value = int(bool(value))  # Convert to 0 or 1
            
            if self.simulator:
                result = self.simulator.output(pin, int_value)
            else:
                GPIO.output(pin, int_value)
                result = True
            
            if result and pin in self.pins_setup:
                self.pins_setup[pin]['value'] = int_value
            
            return {
                'pin': pin,
                'value': int_value,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to set pin {pin}: {e}")
    
    async def get_pin(self, pin: int) -> Dict[str, Any]:
        """Get GPIO pin value"""
        if pin is None:
            raise ValueError("Pin number required")
        
        try:
            if self.simulator:
                value = self.simulator.input(pin)
            else:
                value = GPIO.input(pin)
            
            # Update cached value
            if pin in self.pins_setup:
                self.pins_setup[pin]['value'] = value
            
            return {
                'pin': pin,
                'value': value
            }
            
        except Exception as e:
            raise Exception(f"Failed to read pin {pin}: {e}")
    
    async def toggle_pin(self, pin: int) -> Dict[str, Any]:
        """Toggle GPIO pin value"""
        if pin is None:
            raise ValueError("Pin number required")
        
        try:
            # Get current value
            current = await self.get_pin(pin)
            new_value = 1 - current['value']
            
            # Set new value
            result = await self.set_pin(pin, new_value)
            
            return {
                'pin': pin,
                'previous_value': current['value'],
                'new_value': new_value,
                'success': result['success']
            }
            
        except Exception as e:
            raise Exception(f"Failed to toggle pin {pin}: {e}")
    
    async def pwm_start(self, pin: int, frequency: float, duty_cycle: float) -> Dict[str, Any]:
        """Start PWM on GPIO pin"""
        if pin is None:
            raise ValueError("Pin number required")
        
        try:
            # Ensure pin is setup as output
            if pin not in self.pins_setup:
                await self.setup_pin(pin, "OUT")
            
            if self.simulator:
                result = self.simulator.pwm_start(pin, frequency, duty_cycle)
                pwm_instance = f"sim_pwm_{pin}"
            else:
                # Stop existing PWM if any
                if pin in self.pwm_instances:
                    self.pwm_instances[pin].stop()
                
                # Create and start PWM
                pwm = GPIO.PWM(pin, frequency)
                pwm.start(duty_cycle)
                self.pwm_instances[pin] = pwm
                pwm_instance = f"hw_pwm_{pin}"
                result = True
            
            return {
                'pin': pin,
                'frequency': frequency,
                'duty_cycle': duty_cycle,
                'pwm_instance': pwm_instance,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to start PWM on pin {pin}: {e}")
    
    async def pwm_stop(self, pin: int) -> Dict[str, Any]:
        """Stop PWM on GPIO pin"""
        if pin is None:
            raise ValueError("Pin number required")
        
        try:
            if self.simulator:
                result = self.simulator.pwm_stop(pin)
            else:
                if pin in self.pwm_instances:
                    self.pwm_instances[pin].stop()
                    del self.pwm_instances[pin]
                    result = True
                else:
                    result = False
            
            return {
                'pin': pin,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to stop PWM on pin {pin}: {e}")
    
    async def pwm_change_duty_cycle(self, pin: int, duty_cycle: float) -> Dict[str, Any]:
        """Change PWM duty cycle"""
        if pin is None:
            raise ValueError("Pin number required")
        if duty_cycle is None:
            raise ValueError("Duty cycle required")
        
        try:
            if self.simulator:
                result = self.simulator.pwm_change_duty_cycle(pin, duty_cycle)
            else:
                if pin in self.pwm_instances:
                    self.pwm_instances[pin].ChangeDutyCycle(duty_cycle)
                    result = True
                else:
                    result = False
            
            return {
                'pin': pin,
                'duty_cycle': duty_cycle,
                'success': result
            }
            
        except Exception as e:
            raise Exception(f"Failed to change PWM duty cycle on pin {pin}: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get GPIO handler status"""
        return {
            'mode': self.mode,
            'pins_setup': self.pins_setup.copy(),
            'pwm_instances': list(self.pwm_instances.keys()),
            'simulator_active': self.simulator is not None,
            'hardware_available': HAS_RPI_GPIO
        }
    
    async def cleanup(self) -> Dict[str, Any]:
        """Cleanup GPIO resources"""
        try:
            # Stop all PWM instances
            if not self.simulator:
                for pwm in self.pwm_instances.values():
                    pwm.stop()
                self.pwm_instances.clear()
                
                # Cleanup GPIO
                GPIO.cleanup()
            else:
                self.simulator.cleanup()
            
            self.pins_setup.clear()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"GPIO cleanup error: {e}")
            return {'success': False, 'error': str(e)}


class GPIOSimulator:
    """GPIO Simulator for development and testing"""
    
    def __init__(self):
        """Initialize GPIO simulator"""
        self.pins = {}
        logger.info("GPIO Simulator initialized")
    
    def setup(self, pin: int, direction: str, pull_up_down: str = "PUD_OFF"):
        """Setup simulated GPIO pin"""
        self.pins[pin] = {
            'direction': direction.upper(),
            'pull_up_down': pull_up_down.upper(),
            'value': 0,
            'pwm': None
        }
        return True
    
    def output(self, pin: int, value: int):
        """Set simulated GPIO pin value"""
        if pin in self.pins:
            self.pins[pin]['value'] = int(value)
            logger.debug(f"GPIO SIM: Pin {pin} set to {value}")
            return True
        return False
    
    def input(self, pin: int) -> int:
        """Get simulated GPIO pin value"""
        if pin in self.pins:
            return self.pins[pin]['value']
        return 0
    
    def pwm_start(self, pin: int, frequency: float, duty_cycle: float):
        """Start simulated PWM"""
        if pin not in self.pins:
            self.setup(pin, 'OUT')
        
        self.pins[pin]['pwm'] = {
            'frequency': frequency,
            'duty_cycle': duty_cycle,
            'active': True
        }
        logger.debug(f"GPIO SIM: PWM started on pin {pin} - {frequency}Hz @ {duty_cycle}%")
        return True
    
    def pwm_stop(self, pin: int):
        """Stop simulated PWM"""
        if pin in self.pins and self.pins[pin].get('pwm'):
            self.pins[pin]['pwm']['active'] = False
            logger.debug(f"GPIO SIM: PWM stopped on pin {pin}")
            return True
        return False
    
    def pwm_change_duty_cycle(self, pin: int, duty_cycle: float):
        """Change simulated PWM duty cycle"""
        if pin in self.pins and self.pins[pin].get('pwm'):
            self.pins[pin]['pwm']['duty_cycle'] = duty_cycle
            logger.debug(f"GPIO SIM: PWM duty cycle changed on pin {pin} to {duty_cycle}%")
            return True
        return False
    
    def cleanup(self):
        """Cleanup simulated GPIO"""
        self.pins.clear()
        logger.debug("GPIO SIM: Cleaned up")
