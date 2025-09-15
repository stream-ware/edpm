#!/usr/bin/env python3
"""
I2S Audio Processing Example for EDPM Lite
Demonstrates comprehensive I2S audio communication with real-time processing and analysis.
"""

import asyncio
import json
import time
import logging
import math
import wave
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from edpm import EDPMClient, Config, Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AudioData:
    """Audio data structure"""
    timestamp: float
    sample_rate: int
    channels: int
    bit_depth: int
    data: List[float]
    duration: float
    rms_level: float
    peak_level: float


class I2SAudioProcessor:
    """I2S Audio Processing Application"""
    
    def __init__(self, config_path: str = "config.json", audio_config_path: str = "audio_configs.json"):
        """Initialize the I2S audio processor"""
        self.config_path = Path(config_path)
        self.audio_config_path = Path(audio_config_path)
        self.config = self.load_config()
        self.audio_configs = self.load_audio_configs()
        self.client = None
        self.running = False
        self.recorded_audio = []
        self.current_audio_stream = None
    
    def load_config(self) -> dict:
        """Load main configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "edpm_endpoint": "ipc:///tmp/edpm.ipc",
                "websocket_url": "ws://localhost:8080/ws",
                "transport": "zmq",
                "audio_settings": {
                    "sample_rate": 44100,
                    "channels": 2,
                    "bit_depth": 16,
                    "buffer_size": 1024
                },
                "tone_generator": {
                    "default_frequency": 440,
                    "default_amplitude": 0.5,
                    "default_duration": 5.0
                },
                "recording": {
                    "max_duration": 30.0,
                    "auto_save": true,
                    "save_directory": "./recordings"
                },
                "analysis": {
                    "fft_size": 2048,
                    "window_type": "hamming",
                    "overlap": 0.5
                },
                "effects": {
                    "low_pass_cutoff": 8000,
                    "high_pass_cutoff": 100,
                    "echo_delay": 0.3,
                    "echo_decay": 0.6
                }
            }
    
    def load_audio_configs(self) -> dict:
        """Load audio device configurations from file"""
        if self.audio_config_path.exists():
            with open(self.audio_config_path) as f:
                return json.load(f)
        else:
            # Default audio configurations
            return {
                "devices": {
                    "microphone": {
                        "name": "I2S Microphone",
                        "type": "input",
                        "sample_rates": [8000, 16000, 22050, 44100, 48000],
                        "channels": [1, 2],
                        "bit_depths": [16, 24]
                    },
                    "speaker": {
                        "name": "I2S Speaker/DAC",
                        "type": "output",
                        "sample_rates": [44100, 48000, 96000],
                        "channels": [2],
                        "bit_depths": [16, 24, 32]
                    }
                },
                "test_signals": {
                    "calibration_tones": [100, 440, 1000, 4000, 8000],
                    "sweep_range": {"start": 20, "end": 20000, "duration": 10},
                    "noise_types": ["white", "pink", "brown"]
                }
            }
    
    async def connect(self):
        """Connect to EDPM server"""
        try:
            # Create EDPM client
            edpm_config = Config()
            edpm_config.endpoint = self.config["edpm_endpoint"]
            
            self.client = EDPMClient(edpm_config, transport=self.config["transport"])
            await self.client.connect()
            
            logger.info(f"Connected to EDPM server via {self.config['transport']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to EDPM server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from EDPM server"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from EDPM server")
    
    async def log_message(self, level: str, message: str):
        """Send log message to EDPM server"""
        try:
            if self.client:
                log_msg = Message.log(level, message)
                await self.client.send_message(log_msg)
            logger.info(f"{level.upper()}: {message}")
        except Exception as e:
            logger.error(f"Failed to send log message: {e}")
    
    def generate_tone(self, frequency: float, duration: float, amplitude: float = 0.5, 
                     sample_rate: int = None) -> List[float]:
        """Generate a sine wave tone"""
        if sample_rate is None:
            sample_rate = self.config["audio_settings"]["sample_rate"]
        
        num_samples = int(sample_rate * duration)
        samples = []
        
        for i in range(num_samples):
            t = i / sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            samples.append(sample)
        
        return samples
    
    def generate_sweep(self, start_freq: float, end_freq: float, duration: float, 
                      amplitude: float = 0.5, sample_rate: int = None) -> List[float]:
        """Generate a frequency sweep (chirp) signal"""
        if sample_rate is None:
            sample_rate = self.config["audio_settings"]["sample_rate"]
        
        num_samples = int(sample_rate * duration)
        samples = []
        
        for i in range(num_samples):
            t = i / sample_rate
            # Linear frequency sweep
            instantaneous_freq = start_freq + (end_freq - start_freq) * (t / duration)
            sample = amplitude * math.sin(2 * math.pi * instantaneous_freq * t)
            samples.append(sample)
        
        return samples
    
    def apply_low_pass_filter(self, audio_data: List[float], cutoff: float, 
                             sample_rate: int = None) -> List[float]:
        """Apply a simple low-pass filter"""
        if sample_rate is None:
            sample_rate = self.config["audio_settings"]["sample_rate"]
        
        # Simple RC low-pass filter approximation
        rc = 1.0 / (2 * math.pi * cutoff)
        dt = 1.0 / sample_rate
        alpha = dt / (rc + dt)
        
        filtered = [audio_data[0]]  # Initialize with first sample
        
        for i in range(1, len(audio_data)):
            filtered_sample = alpha * audio_data[i] + (1 - alpha) * filtered[i - 1]
            filtered.append(filtered_sample)
        
        return filtered
    
    def apply_echo_effect(self, audio_data: List[float], delay: float, decay: float,
                         sample_rate: int = None) -> List[float]:
        """Apply echo effect to audio data"""
        if sample_rate is None:
            sample_rate = self.config["audio_settings"]["sample_rate"]
        
        delay_samples = int(delay * sample_rate)
        result = audio_data.copy()
        
        # Add delayed signal with decay
        for i in range(delay_samples, len(audio_data)):
            result[i] += decay * audio_data[i - delay_samples]
        
        return result
    
    def calculate_rms(self, audio_data: List[float]) -> float:
        """Calculate RMS level of audio data"""
        if not audio_data:
            return 0.0
        
        sum_squares = sum(sample ** 2 for sample in audio_data)
        return math.sqrt(sum_squares / len(audio_data))
    
    def calculate_peak(self, audio_data: List[float]) -> float:
        """Calculate peak level of audio data"""
        if not audio_data:
            return 0.0
        
        return max(abs(sample) for sample in audio_data)
    
    def perform_fft_analysis(self, audio_data: List[float], sample_rate: int = None) -> Dict[str, Any]:
        """Perform FFT analysis on audio data (simplified version)"""
        if sample_rate is None:
            sample_rate = self.config["audio_settings"]["sample_rate"]
        
        # Simplified FFT simulation (would use numpy.fft in real implementation)
        fft_size = min(len(audio_data), self.config["analysis"]["fft_size"])
        
        # Generate mock frequency spectrum
        frequencies = []
        magnitudes = []
        
        for i in range(fft_size // 2):
            freq = (i * sample_rate) / fft_size
            frequencies.append(freq)
            
            # Simplified magnitude calculation
            mag = abs(sum(audio_data[j] * math.cos(2 * math.pi * i * j / fft_size) 
                         for j in range(min(fft_size, len(audio_data)))))
            magnitudes.append(mag / fft_size)
        
        return {
            "frequencies": frequencies,
            "magnitudes": magnitudes,
            "peak_frequency": frequencies[magnitudes.index(max(magnitudes))] if magnitudes else 0,
            "fundamental_frequency": self._find_fundamental(frequencies, magnitudes)
        }
    
    def _find_fundamental(self, frequencies: List[float], magnitudes: List[float]) -> float:
        """Find the fundamental frequency from FFT data"""
        if not frequencies or not magnitudes:
            return 0.0
        
        # Simple peak picking for fundamental frequency
        max_magnitude = max(magnitudes)
        threshold = max_magnitude * 0.1
        
        for i, (freq, mag) in enumerate(zip(frequencies, magnitudes)):
            if mag > threshold and freq > 50:  # Ignore very low frequencies
                return freq
        
        return 0.0
    
    async def generate_test_tone(self, frequency: float, duration: float) -> AudioData:
        """Generate test tone and send to I2S output"""
        logger.info(f"Generating {frequency}Hz tone for {duration} seconds")
        await self.log_message("info", f"Generating test tone: {frequency}Hz, {duration}s")
        
        try:
            # Generate tone data
            audio_samples = self.generate_tone(frequency, duration)
            
            # Send to EDPM I2S handler
            result = await self.client.send_command("i2s", {
                "action": "generate_tone",
                "frequency": frequency,
                "duration": duration,
                "amplitude": self.config["tone_generator"]["default_amplitude"],
                "sample_rate": self.config["audio_settings"]["sample_rate"]
            })
            
            if result:
                logger.info(f"Tone generation result: {result}")
            
            # Create audio data object
            audio_data = AudioData(
                timestamp=time.time(),
                sample_rate=self.config["audio_settings"]["sample_rate"],
                channels=1,
                bit_depth=16,
                data=audio_samples,
                duration=duration,
                rms_level=self.calculate_rms(audio_samples),
                peak_level=self.calculate_peak(audio_samples)
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating tone: {e}")
            await self.log_message("error", f"Tone generation failed: {e}")
            raise
    
    async def record_audio(self, duration: float) -> AudioData:
        """Record audio from I2S input"""
        logger.info(f"Recording audio for {duration} seconds")
        await self.log_message("info", f"Starting audio recording: {duration}s")
        
        try:
            # Start recording via EDPM I2S handler
            result = await self.client.send_command("i2s", {
                "action": "record_audio",
                "duration": duration,
                "sample_rate": self.config["audio_settings"]["sample_rate"],
                "channels": self.config["audio_settings"]["channels"],
                "bit_depth": self.config["audio_settings"]["bit_depth"]
            })
            
            if result and "audio_data" in result:
                audio_samples = result["audio_data"]
                logger.info(f"Recorded {len(audio_samples)} samples")
            else:
                # Generate simulated recording data
                logger.warning("Using simulated recording data")
                audio_samples = self.generate_tone(440, duration, amplitude=0.1)
                # Add some noise simulation
                import random
                for i in range(len(audio_samples)):
                    audio_samples[i] += random.uniform(-0.05, 0.05)
            
            # Create audio data object
            audio_data = AudioData(
                timestamp=time.time(),
                sample_rate=self.config["audio_settings"]["sample_rate"],
                channels=self.config["audio_settings"]["channels"],
                bit_depth=self.config["audio_settings"]["bit_depth"],
                data=audio_samples,
                duration=duration,
                rms_level=self.calculate_rms(audio_samples),
                peak_level=self.calculate_peak(audio_samples)
            )
            
            # Store recording
            self.recorded_audio.append(audio_data)
            
            # Auto-save if enabled
            if self.config["recording"]["auto_save"]:
                await self.save_audio_data(audio_data)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            await self.log_message("error", f"Audio recording failed: {e}")
            raise
    
    async def save_audio_data(self, audio_data: AudioData, filename: str = None):
        """Save audio data to file"""
        try:
            if filename is None:
                timestamp = int(audio_data.timestamp)
                filename = f"recording_{timestamp}.wav"
            
            save_dir = Path(self.config["recording"]["save_directory"])
            save_dir.mkdir(exist_ok=True)
            filepath = save_dir / filename
            
            # Simulate saving audio file
            logger.info(f"Saving audio to {filepath}")
            
            # In a real implementation, you would use wave or other audio libraries
            # with wave.open(str(filepath), 'wb') as wav_file:
            #     wav_file.setnchannels(audio_data.channels)
            #     wav_file.setsampwidth(audio_data.bit_depth // 8)
            #     wav_file.setframerate(audio_data.sample_rate)
            #     wav_file.writeframes(audio_samples_bytes)
            
            await self.log_message("info", f"Audio saved: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            await self.log_message("error", f"Audio save failed: {e}")
    
    async def audio_analysis_demo(self):
        """Demonstrate audio analysis capabilities"""
        logger.info("=== Audio Analysis Demo ===")
        await self.log_message("info", "Starting audio analysis demo")
        
        # Generate test signals for analysis
        test_frequencies = self.audio_configs["test_signals"]["calibration_tones"]
        
        for freq in test_frequencies:
            try:
                logger.info(f"Analyzing {freq}Hz tone")
                
                # Generate tone
                audio_data = await self.generate_test_tone(freq, 2.0)
                
                # Perform FFT analysis
                fft_result = self.perform_fft_analysis(audio_data.data)
                
                logger.info(f"Peak frequency detected: {fft_result['peak_frequency']:.1f}Hz")
                logger.info(f"Fundamental frequency: {fft_result['fundamental_frequency']:.1f}Hz")
                logger.info(f"RMS level: {audio_data.rms_level:.3f}")
                logger.info(f"Peak level: {audio_data.peak_level:.3f}")
                
                # Send analysis results to dashboard
                await self.client.send_command("log", {
                    "level": "data",
                    "analysis_type": "frequency_analysis",
                    "test_frequency": freq,
                    "detected_frequency": fft_result['peak_frequency'],
                    "rms_level": audio_data.rms_level,
                    "peak_level": audio_data.peak_level,
                    "timestamp": audio_data.timestamp
                })
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing {freq}Hz tone: {e}")
    
    async def audio_effects_demo(self):
        """Demonstrate audio effects processing"""
        logger.info("=== Audio Effects Demo ===")
        await self.log_message("info", "Starting audio effects demo")
        
        try:
            # Generate base tone
            base_frequency = 440  # A4
            base_tone = self.generate_tone(base_frequency, 3.0)
            
            logger.info("Applying low-pass filter effect")
            filtered_audio = self.apply_low_pass_filter(
                base_tone, 
                self.config["effects"]["low_pass_cutoff"]
            )
            
            logger.info("Applying echo effect")
            echo_audio = self.apply_echo_effect(
                base_tone,
                self.config["effects"]["echo_delay"],
                self.config["effects"]["echo_decay"]
            )
            
            # Analyze processed audio
            original_rms = self.calculate_rms(base_tone)
            filtered_rms = self.calculate_rms(filtered_audio)
            echo_rms = self.calculate_rms(echo_audio)
            
            logger.info(f"Original RMS: {original_rms:.3f}")
            logger.info(f"Filtered RMS: {filtered_rms:.3f}")
            logger.info(f"Echo RMS: {echo_rms:.3f}")
            
            # Send effects results to server
            await self.client.send_command("log", {
                "level": "data",
                "processing_type": "audio_effects",
                "original_rms": original_rms,
                "filtered_rms": filtered_rms,
                "echo_rms": echo_rms,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"Error in audio effects demo: {e}")
    
    async def frequency_sweep_demo(self):
        """Demonstrate frequency sweep generation and analysis"""
        logger.info("=== Frequency Sweep Demo ===")
        await self.log_message("info", "Starting frequency sweep demo")
        
        try:
            sweep_config = self.audio_configs["test_signals"]["sweep_range"]
            
            logger.info(f"Generating sweep: {sweep_config['start']}Hz to {sweep_config['end']}Hz")
            
            # Generate frequency sweep
            sweep_audio = self.generate_sweep(
                sweep_config["start"],
                sweep_config["end"],
                sweep_config["duration"]
            )
            
            # Send sweep to I2S output
            result = await self.client.send_command("i2s", {
                "action": "play_audio",
                "audio_data": sweep_audio[:1000],  # Send subset for demo
                "sample_rate": self.config["audio_settings"]["sample_rate"]
            })
            
            # Analyze sweep
            sweep_rms = self.calculate_rms(sweep_audio)
            sweep_peak = self.calculate_peak(sweep_audio)
            
            logger.info(f"Sweep RMS: {sweep_rms:.3f}")
            logger.info(f"Sweep Peak: {sweep_peak:.3f}")
            
            await self.log_message("info", f"Frequency sweep completed: {sweep_rms:.3f} RMS")
            
        except Exception as e:
            logger.error(f"Error in frequency sweep demo: {e}")
    
    async def recording_demo(self):
        """Demonstrate audio recording and playback"""
        logger.info("=== Audio Recording Demo ===")
        await self.log_message("info", "Starting audio recording demo")
        
        try:
            # Record audio
            recording = await self.record_audio(5.0)
            
            logger.info(f"Recording completed: {len(recording.data)} samples")
            logger.info(f"Recording RMS: {recording.rms_level:.3f}")
            logger.info(f"Recording Peak: {recording.peak_level:.3f}")
            
            # Analyze recording
            fft_result = self.perform_fft_analysis(recording.data)
            
            logger.info(f"Recording analysis:")
            logger.info(f"  Peak frequency: {fft_result['peak_frequency']:.1f}Hz")
            logger.info(f"  Fundamental: {fft_result['fundamental_frequency']:.1f}Hz")
            
            # Playback recording
            await self.client.send_command("i2s", {
                "action": "play_audio",
                "audio_data": recording.data[:1000],  # Play subset
                "sample_rate": recording.sample_rate
            })
            
            logger.info("Recording playback completed")
            
        except Exception as e:
            logger.error(f"Error in recording demo: {e}")
    
    async def get_audio_status(self) -> Dict[str, Any]:
        """Get current audio processing status"""
        try:
            # Get I2S status from server
            i2s_status = await self.client.send_command("i2s", {"action": "i2s_status"})
            
            return {
                "processor_running": self.running,
                "recorded_sessions": len(self.recorded_audio),
                "audio_config": self.config["audio_settings"],
                "i2s_status": i2s_status,
                "last_recording": {
                    "timestamp": self.recorded_audio[-1].timestamp,
                    "duration": self.recorded_audio[-1].duration,
                    "rms_level": self.recorded_audio[-1].rms_level
                } if self.recorded_audio else None
            }
            
        except Exception as e:
            logger.error(f"Error getting audio status: {e}")
            return {"error": str(e)}
    
    async def run_audio_processing(self):
        """Run the complete I2S audio processing demonstration"""
        self.running = True
        
        try:
            await self.log_message("info", "I2S Audio Processor started")
            
            # Connect to EDPM server
            if not await self.connect():
                logger.error("Cannot connect to EDPM server, exiting...")
                return
            
            # Get initial I2S status
            status = await self.get_audio_status()
            logger.info(f"Initial audio status: {status}")
            
            # Run demonstrations
            while self.running:
                logger.info("Starting audio processing cycle...")
                
                # Audio analysis demo
                await self.audio_analysis_demo()
                
                if not self.running:
                    break
                
                # Audio effects demo
                await self.audio_effects_demo()
                
                if not self.running:
                    break
                
                # Frequency sweep demo
                await self.frequency_sweep_demo()
                
                if not self.running:
                    break
                
                # Recording demo
                await self.recording_demo()
                
                if not self.running:
                    break
                
                logger.info("Audio processing cycle completed, waiting...")
                await asyncio.sleep(10)
            
            await self.log_message("info", "I2S Audio Processor completed")
            logger.info("Audio processing completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("Audio processing interrupted by user")
            await self.log_message("info", "I2S audio processing interrupted by user")
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.log_message("error", f"I2S audio processing error: {e}")
        finally:
            self.running = False
            await self.disconnect()
    
    def stop(self):
        """Stop the audio processing"""
        self.running = False


async def main():
    """Main entry point"""
    print("EDPM Lite I2S Audio Processing Example")
    print("=" * 50)
    print("This example demonstrates I2S audio processing using EDPM Lite")
    print("Press Ctrl+C to stop the audio processing")
    print()
    
    # Create and run the audio processor
    processor = I2SAudioProcessor()
    
    # Setup signal handling
    import signal
    def signal_handler(sig, frame):
        logger.info("Received stop signal...")
        processor.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the audio processing
    await processor.run_audio_processing()


if __name__ == "__main__":
    asyncio.run(main())
