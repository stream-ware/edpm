"""
EDPM I2S Audio Protocol Handler
I2S audio input/output with tone generation, recording, and analysis capabilities.
"""

import asyncio
import time
import threading
import math
import random
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass
from ..core.config import Config

# Optional audio dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    pyaudio = None

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """I2S Audio configuration"""
    sample_rate: int = 44100
    channels: int = 2  # Stereo
    bit_depth: int = 16
    buffer_size: int = 1024
    input_device: Optional[int] = None
    output_device: Optional[int] = None


class I2SHandler:
    """
    I2S Audio Protocol Handler
    
    Handles I2S audio operations including tone generation, recording, playback,
    and audio analysis. Includes simulator mode for development and testing.
    """
    
    def __init__(self, config: Config = None):
        """Initialize I2S Handler"""
        self.config = config or Config.from_env()
        self.audio_config = AudioConfig()
        self.simulator = None
        
        # Audio state
        self.is_recording = False
        self.is_playing = False
        self.audio_buffer = []
        self.callbacks = []
        self.pyaudio_instance = None
        self.current_stream = None
        
        # Initialize I2S based on configuration
        if self.config.i2s_simulator:
            self._init_simulator()
        elif HAS_PYAUDIO:
            self._init_hardware()
        else:
            logger.warning("PyAudio not available, using simulator")
            self._init_simulator()
        
        logger.info(f"I2S Handler initialized - Rate: {self.audio_config.sample_rate}Hz, Channels: {self.audio_config.channels}, Simulator: {self.simulator is not None}")
    
    def _init_simulator(self):
        """Initialize I2S simulator"""
        self.simulator = I2SSimulator(self.audio_config)
    
    def _init_hardware(self):
        """Initialize I2S hardware"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            logger.info(f"PyAudio initialized: {self.audio_config.sample_rate}Hz, {self.audio_config.channels}ch, {self.audio_config.bit_depth}bit")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            logger.warning("Falling back to simulator")
            self._init_simulator()
    
    async def handle_command(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle I2S command
        
        Args:
            action: I2S action to perform
            data: Command parameters
            
        Returns:
            Result dictionary
        """
        try:
            if action == "play_tone":
                return await self.play_tone(
                    data.get("frequency", 440),
                    data.get("duration", 1.0),
                    data.get("amplitude", 0.5)
                )
            elif action == "record_audio":
                return await self.record_audio(
                    data.get("duration", 5.0),
                    data.get("filename")
                )
            elif action == "stop_recording":
                return await self.stop_recording()
            elif action == "play_audio":
                return await self.play_audio(data.get("filename"))
            elif action == "stop_playback":
                return await self.stop_playback()
            elif action == "get_audio_level":
                return await self.get_audio_level()
            elif action == "get_fft_analysis":
                return await self.get_fft_analysis()
            elif action == "i2s_status":
                return await self.get_status()
            elif action == "list_audio_devices":
                return await self.list_audio_devices()
            else:
                raise ValueError(f"Unknown I2S action: {action}")
                
        except Exception as e:
            logger.error(f"I2S command error: {e}")
            raise
    
    async def play_tone(self, frequency: float, duration: float = 1.0, amplitude: float = 0.5) -> Dict[str, Any]:
        """Generate and play audio tone"""
        try:
            if self.simulator:
                result = await self.simulator.play_tone(frequency, duration, amplitude)
            else:
                result = await self._hardware_play_tone(frequency, duration, amplitude)
            
            return {
                'frequency': frequency,
                'duration': duration,
                'amplitude': amplitude,
                'success': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to play tone: {e}")
    
    async def record_audio(self, duration: float = 5.0, filename: Optional[str] = None) -> Dict[str, Any]:
        """Record audio for specified duration"""
        if self.is_recording:
            raise Exception("Recording already in progress")
        
        try:
            if self.simulator:
                result = await self.simulator.record_audio(duration, filename)
            else:
                result = await self._hardware_record_audio(duration, filename)
            
            return {
                'duration': duration,
                'filename': filename,
                'sample_rate': self.audio_config.sample_rate,
                'channels': self.audio_config.channels,
                'success': result.get('success', False),
                'samples_recorded': result.get('samples', 0),
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to record audio: {e}")
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Stop audio recording"""
        try:
            if self.simulator:
                result = self.simulator.stop_recording()
            else:
                result = await self._hardware_stop_recording()
            
            self.is_recording = False
            
            return {
                'success': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to stop recording: {e}")
    
    async def play_audio(self, filename: str) -> Dict[str, Any]:
        """Play audio file"""
        if not filename:
            raise ValueError("Filename required")
        
        try:
            if self.simulator:
                result = await self.simulator.play_audio(filename)
            else:
                result = await self._hardware_play_audio(filename)
            
            return {
                'filename': filename,
                'success': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to play audio: {e}")
    
    async def stop_playback(self) -> Dict[str, Any]:
        """Stop audio playback"""
        try:
            if self.simulator:
                result = self.simulator.stop_playback()
            else:
                result = await self._hardware_stop_playback()
            
            self.is_playing = False
            
            return {
                'success': result,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to stop playback: {e}")
    
    async def get_audio_level(self) -> Dict[str, Any]:
        """Get current audio input level"""
        try:
            if self.simulator:
                level = self.simulator.get_audio_level()
            else:
                level = await self._hardware_get_audio_level()
            
            return {
                'level': level,
                'level_db': 20 * math.log10(max(level, 1e-10)),  # Convert to dB
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to get audio level: {e}")
    
    async def get_fft_analysis(self, samples: int = 1024) -> Dict[str, Any]:
        """Get FFT analysis of current audio"""
        try:
            if self.simulator:
                fft_data = self.simulator.get_fft_analysis(samples)
            else:
                fft_data = await self._hardware_get_fft_analysis(samples)
            
            return {
                'fft_data': fft_data,
                'sample_rate': self.audio_config.sample_rate,
                'samples': samples,
                'timestamp': time.time()
            }
            
        except Exception as e:
            raise Exception(f"Failed to get FFT analysis: {e}")
    
    async def list_audio_devices(self) -> Dict[str, Any]:
        """List available audio devices"""
        devices = []
        
        try:
            if self.simulator:
                devices = [
                    {'index': 0, 'name': 'Simulator Input', 'type': 'input'},
                    {'index': 1, 'name': 'Simulator Output', 'type': 'output'}
                ]
            elif self.pyaudio_instance:
                device_count = self.pyaudio_instance.get_device_count()
                for i in range(device_count):
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'type': 'input' if device_info['maxInputChannels'] > 0 else 'output',
                        'channels': device_info['maxInputChannels'] or device_info['maxOutputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
            
            return {
                'devices': devices,
                'count': len(devices)
            }
            
        except Exception as e:
            raise Exception(f"Failed to list audio devices: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get I2S handler status"""
        return {
            'sample_rate': self.audio_config.sample_rate,
            'channels': self.audio_config.channels,
            'bit_depth': self.audio_config.bit_depth,
            'buffer_size': self.audio_config.buffer_size,
            'simulator_active': self.simulator is not None,
            'hardware_available': HAS_PYAUDIO and self.pyaudio_instance is not None,
            'is_recording': self.is_recording,
            'is_playing': self.is_playing,
            'audio_buffer_size': len(self.audio_buffer)
        }
    
    async def _hardware_play_tone(self, frequency: float, duration: float, amplitude: float) -> bool:
        """Play tone using hardware"""
        try:
            if not HAS_NUMPY:
                logger.warning("NumPy required for tone generation")
                return False
            
            # Generate tone
            samples = int(self.audio_config.sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            tone = amplitude * np.sin(2 * np.pi * frequency * t)
            
            # Convert to audio format
            audio_data = (tone * 32767).astype(np.int16)
            
            # Play using PyAudio
            stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.audio_config.sample_rate,
                output=True
            )
            
            stream.write(audio_data.tobytes())
            stream.stop_stream()
            stream.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Hardware tone playback error: {e}")
            return False
    
    async def _hardware_record_audio(self, duration: float, filename: Optional[str]) -> Dict[str, Any]:
        """Record audio using hardware"""
        try:
            self.is_recording = True
            samples = int(self.audio_config.sample_rate * duration)
            
            stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.audio_config.channels,
                rate=self.audio_config.sample_rate,
                input=True,
                frames_per_buffer=self.audio_config.buffer_size
            )
            
            frames = []
            for _ in range(int(samples / self.audio_config.buffer_size)):
                data = stream.read(self.audio_config.buffer_size)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Save to file if filename provided
            if filename and HAS_NUMPY:
                # Convert to numpy array and save (simplified)
                audio_data = b''.join(frames)
                # In real implementation, you would save as WAV file
            
            self.audio_buffer = frames
            self.is_recording = False
            
            return {
                'success': True,
                'samples': len(frames) * self.audio_config.buffer_size
            }
            
        except Exception as e:
            self.is_recording = False
            logger.error(f"Hardware recording error: {e}")
            return {'success': False}
    
    async def _hardware_stop_recording(self) -> bool:
        """Stop hardware recording"""
        self.is_recording = False
        return True
    
    async def _hardware_play_audio(self, filename: str) -> bool:
        """Play audio file using hardware"""
        # Simplified implementation
        logger.info(f"Would play audio file: {filename}")
        return True
    
    async def _hardware_stop_playback(self) -> bool:
        """Stop hardware playback"""
        self.is_playing = False
        return True
    
    async def _hardware_get_audio_level(self) -> float:
        """Get audio level from hardware"""
        try:
            if self.is_recording:
                # Return simulated level based on recent recording
                return random.uniform(0.1, 0.8)
            else:
                # Quick sample to get current level
                stream = self.pyaudio_instance.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.audio_config.sample_rate,
                    input=True,
                    frames_per_buffer=256
                )
                
                data = stream.read(256)
                stream.close()
                
                if HAS_NUMPY:
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    level = np.sqrt(np.mean(audio_data**2)) / 32768.0
                else:
                    level = random.uniform(0.1, 0.5)
                
                return min(level, 1.0)
                
        except Exception as e:
            logger.error(f"Hardware audio level error: {e}")
            return 0.0
    
    async def _hardware_get_fft_analysis(self, samples: int) -> List[float]:
        """Get FFT analysis from hardware"""
        try:
            if HAS_NUMPY and len(self.audio_buffer) > 0:
                # Use recent recorded data for FFT
                data = self.audio_buffer[-1]  # Last buffer
                audio_data = np.frombuffer(data, dtype=np.int16)
                fft = np.fft.fft(audio_data[:samples])
                magnitudes = np.abs(fft[:samples//2])
                return magnitudes.tolist()
            else:
                # Return simulated FFT data
                return [random.uniform(0, 100) for _ in range(samples//2)]
                
        except Exception as e:
            logger.error(f"Hardware FFT error: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup I2S resources"""
        try:
            if self.current_stream:
                self.current_stream.close()
            
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
            
            if self.simulator:
                self.simulator.cleanup()
            
            logger.info("I2S Handler cleanup completed")
            
        except Exception as e:
            logger.error(f"I2S cleanup error: {e}")


class I2SSimulator:
    """I2S Audio Simulator for development and testing"""
    
    def __init__(self, audio_config: AudioConfig):
        """Initialize I2S simulator"""
        self.config = audio_config
        self.is_recording = False
        self.is_playing = False
        self.audio_level = 0.0
        self.current_frequency = 440.0
        
        logger.info("I2S Simulator initialized")
    
    async def play_tone(self, frequency: float, duration: float, amplitude: float) -> bool:
        """Simulate tone playback"""
        self.current_frequency = frequency
        self.is_playing = True
        
        logger.debug(f"I2S SIM: Playing tone {frequency}Hz for {duration}s at {amplitude} amplitude")
        
        # Simulate playback duration
        await asyncio.sleep(min(duration, 0.1))  # Don't actually wait full duration
        
        self.is_playing = False
        return True
    
    async def record_audio(self, duration: float, filename: Optional[str]) -> Dict[str, Any]:
        """Simulate audio recording"""
        self.is_recording = True
        samples = int(self.config.sample_rate * duration)
        
        logger.debug(f"I2S SIM: Recording {duration}s ({samples} samples)")
        
        # Simulate recording time
        await asyncio.sleep(min(duration, 0.1))
        
        self.is_recording = False
        
        return {
            'success': True,
            'samples': samples
        }
    
    def stop_recording(self) -> bool:
        """Stop simulated recording"""
        self.is_recording = False
        logger.debug("I2S SIM: Recording stopped")
        return True
    
    async def play_audio(self, filename: str) -> bool:
        """Simulate audio file playback"""
        self.is_playing = True
        logger.debug(f"I2S SIM: Playing audio file {filename}")
        
        # Simulate playback
        await asyncio.sleep(0.1)
        
        self.is_playing = False
        return True
    
    def stop_playback(self) -> bool:
        """Stop simulated playback"""
        self.is_playing = False
        logger.debug("I2S SIM: Playback stopped")
        return True
    
    def get_audio_level(self) -> float:
        """Get simulated audio level"""
        if self.is_recording or self.is_playing:
            # Vary the level based on frequency for realism
            base_level = 0.5
            frequency_factor = min(self.current_frequency / 1000.0, 1.0)
            noise = random.uniform(-0.1, 0.1)
            level = base_level * frequency_factor + noise
        else:
            # Background noise level
            level = random.uniform(0.01, 0.05)
        
        self.audio_level = max(0.0, min(level, 1.0))
        return self.audio_level
    
    def get_fft_analysis(self, samples: int) -> List[float]:
        """Get simulated FFT analysis"""
        # Generate realistic FFT data with peak at current frequency
        fft_data = []
        freq_resolution = self.config.sample_rate / samples
        
        for i in range(samples // 2):
            freq = i * freq_resolution
            if abs(freq - self.current_frequency) < 50:  # Peak at current frequency
                magnitude = random.uniform(80, 100)
            else:
                # Background noise decreases with frequency
                magnitude = random.uniform(1, 20) * (1.0 - freq / (self.config.sample_rate / 2))
            
            fft_data.append(max(0, magnitude))
        
        return fft_data
    
    def cleanup(self):
        """Cleanup simulator"""
        self.is_recording = False
        self.is_playing = False
        logger.debug("I2S SIM: Cleaned up")
