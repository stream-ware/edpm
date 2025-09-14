"""
I2S Audio Protocol Handler with simulator support
Supports: Audio input/output, analysis, tone generation
"""
import asyncio
import numpy as np
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging
import math
import random

logger = logging.getLogger('I2S')

@dataclass
class AudioConfig:
    """I2S Audio configuration"""
    sample_rate: int = 44100
    channels: int = 2  # Stereo
    bit_depth: int = 16
    buffer_size: int = 1024

class I2SHandler:
    """I2S Audio Protocol Handler with simulation support"""
    
    def __init__(self, config: AudioConfig = None, simulator: bool = False):
        self.config = config or AudioConfig()
        self.simulator = simulator
        self.is_recording = False
        self.is_playing = False
        self.audio_buffer = []
        self.callbacks = []
        
        # Audio processing
        self.sample_rate = self.config.sample_rate
        self.channels = self.config.channels
        self.bit_depth = self.config.bit_depth
        
        if not simulator:
            try:
                import pyaudio
                self.pyaudio = pyaudio
                self.pa = pyaudio.PyAudio()
                logger.info(f"I2S initialized: {self.sample_rate}Hz, {self.channels}ch, {self.bit_depth}bit")
            except ImportError:
                logger.warning("PyAudio not found, using simulator")
                self.simulator = True
        
        if self.simulator:
            self._init_simulator()
    
    def _init_simulator(self):
        """Initialize I2S audio simulator"""
        logger.info("I2S Audio Simulator initialized")
        self.pyaudio = None
        self.pa = None
        
        # Generate some test waveforms
        self.test_frequencies = [440, 880, 1760, 2000]  # A4, A5, A6, B6
        self.current_tone = 0
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """List available audio devices"""
        if self.simulator:
            return [
                {"index": 0, "name": "Simulated Input", "channels": 2, "type": "input"},
                {"index": 1, "name": "Simulated Output", "channels": 2, "type": "output"}
            ]
        
        devices = []
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            devices.append({
                "index": i,
                "name": info['name'],
                "channels": info['maxInputChannels'] if info['maxInputChannels'] > 0 else info['maxOutputChannels'],
                "type": "input" if info['maxInputChannels'] > 0 else "output"
            })
        return devices
    
    def generate_tone(self, frequency: float, duration: float, amplitude: float = 0.5) -> np.ndarray:
        """Generate a sine wave tone"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # Generate stereo sine wave
        if self.channels == 2:
            left = amplitude * np.sin(2 * np.pi * frequency * t)
            right = amplitude * np.sin(2 * np.pi * frequency * t)
            audio_data = np.column_stack((left, right))
        else:
            audio_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Convert to appropriate bit depth
        if self.bit_depth == 16:
            audio_data = (audio_data * 32767).astype(np.int16)
        elif self.bit_depth == 32:
            audio_data = (audio_data * 2147483647).astype(np.int32)
        
        return audio_data
    
    def analyze_audio(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Analyze audio data for frequency content and levels"""
        if audio_data is None or len(audio_data) == 0:
            return {"error": "No audio data"}
        
        try:
            # Convert to mono if stereo
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                mono_data = np.mean(audio_data, axis=1)
            else:
                mono_data = audio_data.flatten()
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(mono_data.astype(float) ** 2))
            db_level = 20 * np.log10(rms / 32767.0) if rms > 0 else -120
            
            # FFT for frequency analysis
            fft = np.fft.fft(mono_data)
            freqs = np.fft.fftfreq(len(fft), 1/self.sample_rate)
            magnitude = np.abs(fft[:len(fft)//2])
            
            # Find dominant frequency
            dominant_freq_idx = np.argmax(magnitude[1:]) + 1  # Skip DC component
            dominant_frequency = abs(freqs[dominant_freq_idx])
            
            # Peak detection
            peak_indices = []
            threshold = np.max(magnitude) * 0.1  # 10% of max
            for i in range(1, len(magnitude)-1):
                if magnitude[i] > magnitude[i-1] and magnitude[i] > magnitude[i+1] and magnitude[i] > threshold:
                    peak_indices.append(i)
            
            peaks = [(abs(freqs[i]), magnitude[i]) for i in peak_indices[:5]]  # Top 5 peaks
            
            return {
                "rms_level": rms,
                "db_level": round(db_level, 2),
                "dominant_frequency": round(dominant_frequency, 2),
                "peaks": peaks,
                "sample_rate": self.sample_rate,
                "duration": len(mono_data) / self.sample_rate
            }
            
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return {"error": str(e)}
    
    async def start_recording(self, callback: Optional[Callable] = None, duration: Optional[float] = None):
        """Start audio recording"""
        if self.is_recording:
            logger.warning("Already recording")
            return
        
        self.is_recording = True
        self.audio_buffer = []
        logger.info("Started I2S recording")
        
        if callback:
            self.callbacks.append(callback)
        
        if self.simulator:
            await self._simulate_recording(duration)
        else:
            await self._real_recording(duration)
    
    async def _simulate_recording(self, duration: Optional[float] = None):
        """Simulate audio recording"""
        start_time = time.time()
        
        while self.is_recording:
            # Generate some simulated audio data (mix of tones and noise)
            chunk_duration = 0.1  # 100ms chunks
            samples = int(self.sample_rate * chunk_duration)
            
            # Mix multiple frequencies with noise
            t = np.linspace(0, chunk_duration, samples, False)
            audio_chunk = np.zeros(samples)
            
            # Add some test tones with random amplitudes
            for freq in [440, 880, 1320]:  # Musical chord
                amplitude = random.uniform(0.1, 0.3)
                audio_chunk += amplitude * np.sin(2 * np.pi * freq * t)
            
            # Add some noise
            noise = random.uniform(0.05, 0.15) * np.random.normal(0, 0.1, samples)
            audio_chunk += noise
            
            # Convert to stereo int16
            if self.channels == 2:
                stereo_chunk = np.column_stack((audio_chunk, audio_chunk))
            else:
                stereo_chunk = audio_chunk
            
            audio_data = (stereo_chunk * 32767).astype(np.int16)
            self.audio_buffer.extend(audio_data)
            
            # Call callbacks with chunk
            for callback in self.callbacks:
                try:
                    await callback(audio_data)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            await asyncio.sleep(chunk_duration)
            
            # Check duration limit
            if duration and (time.time() - start_time) >= duration:
                break
    
    async def _real_recording(self, duration: Optional[float] = None):
        """Real audio recording using PyAudio"""
        def audio_callback(in_data, frame_count, time_info, status):
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self.audio_buffer.extend(audio_data)
            return (in_data, self.pyaudio.paContinue)
        
        stream = self.pa.open(
            format=self.pa.get_format_from_width(self.bit_depth // 8),
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.config.buffer_size,
            stream_callback=audio_callback
        )
        
        stream.start_stream()
        
        start_time = time.time()
        while self.is_recording:
            await asyncio.sleep(0.1)
            if duration and (time.time() - start_time) >= duration:
                break
        
        stream.stop_stream()
        stream.close()
    
    def stop_recording(self) -> np.ndarray:
        """Stop recording and return recorded audio"""
        self.is_recording = False
        self.callbacks.clear()
        
        if self.audio_buffer:
            audio_array = np.array(self.audio_buffer, dtype=np.int16)
            logger.info(f"Stopped recording: {len(audio_array)} samples")
            return audio_array
        else:
            logger.warning("No audio data recorded")
            return np.array([])
    
    async def play_audio(self, audio_data: np.ndarray):
        """Play audio data"""
        if self.is_playing:
            logger.warning("Already playing audio")
            return
        
        self.is_playing = True
        logger.info("Started I2S playback")
        
        if self.simulator:
            await self._simulate_playback(audio_data)
        else:
            await self._real_playback(audio_data)
        
        self.is_playing = False
        logger.info("Finished I2S playback")
    
    async def _simulate_playback(self, audio_data: np.ndarray):
        """Simulate audio playback"""
        if len(audio_data) == 0:
            return
        
        # Calculate playback duration
        duration = len(audio_data) / (self.sample_rate * self.channels)
        logger.info(f"Simulating playback of {duration:.2f}s audio")
        
        # Analyze what we're "playing"
        analysis = self.analyze_audio(audio_data)
        logger.info(f"Playing audio: {analysis.get('dominant_frequency', 0):.1f}Hz, {analysis.get('db_level', -120):.1f}dB")
        
        await asyncio.sleep(duration)
    
    async def _real_playback(self, audio_data: np.ndarray):
        """Real audio playback using PyAudio"""
        stream = self.pa.open(
            format=self.pa.get_format_from_width(self.bit_depth // 8),
            channels=self.channels,
            rate=self.sample_rate,
            output=True
        )
        
        # Play in chunks to avoid blocking
        chunk_size = self.config.buffer_size * self.channels
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            stream.write(chunk.tobytes())
            await asyncio.sleep(0.01)  # Small delay to allow other tasks
        
        stream.stop_stream()
        stream.close()
    
    async def play_tone(self, frequency: float, duration: float = 1.0, amplitude: float = 0.5):
        """Play a test tone"""
        logger.info(f"Playing tone: {frequency}Hz for {duration}s")
        tone_data = self.generate_tone(frequency, duration, amplitude)
        await self.play_audio(tone_data)
    
    async def continuous_monitoring(self, callback, interval: float = 0.5):
        """Start continuous audio monitoring"""
        while True:
            try:
                # Record a short sample for analysis
                await self.start_recording(duration=0.1)
                await asyncio.sleep(0.1)
                recorded = self.stop_recording()
                
                if len(recorded) > 0:
                    analysis = self.analyze_audio(recorded)
                    await callback(analysis)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"I2S monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def __del__(self):
        """Cleanup audio resources"""
        if hasattr(self, 'pa') and self.pa:
            self.pa.terminate()
