# I2S Audio Processing Example Project

This example demonstrates I2S audio communication and processing using the EDPM Lite framework with Docker deployment.

## Features

- I2S audio input/output configuration
- Real-time audio signal processing
- Audio tone generation and playback
- Audio recording and analysis
- FFT spectrum analysis and visualization
- Real-time audio monitoring via web dashboard
- Docker containerization for easy deployment

## Audio Capabilities

- **Tone Generation**: Generate sine waves, square waves, and custom waveforms
- **Audio Recording**: Capture audio from I2S microphones or line inputs
- **Audio Playback**: Play audio through I2S DACs or speakers
- **Signal Analysis**: Real-time FFT analysis, frequency domain visualization
- **Audio Effects**: Basic filtering, amplitude modulation, echo effects
- **Format Support**: Various sample rates, bit depths, and channel configurations

## Quick Start

### Using Docker (Recommended)

```bash
# Start the complete EDPM I2S audio processing stack
docker-compose up -d

# View logs
docker-compose logs -f audio-processor

# Stop the stack
docker-compose down
```

### Manual Setup

1. Install EDPM Lite package with audio support:
```bash
pip install edpm-lite[i2s]
```

2. Run the I2S audio processing example:
```bash
python i2s_audio_example.py
```

3. Access the web dashboard:
```bash
# Open browser to http://localhost:8080
```

## Configuration

Edit `config.json` to customize:
- I2S interface configuration (sample rate, bit depth, channels)
- Audio processing parameters
- Recording and playback settings
- Signal analysis options

## Project Structure

```
i2s-audio/
├── i2s_audio_example.py    # Main audio processing script
├── audio_configs.json      # Audio device and format configurations
├── config.json            # Main configuration file
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container setup
├── requirements.txt       # Python dependencies
├── audio_samples/         # Sample audio files
└── README.md              # This file
```

## I2S Operations

The example demonstrates:

1. **Audio Interface Setup**: Configure I2S hardware parameters
2. **Tone Generation**: Create test signals and calibration tones
3. **Audio Recording**: Capture audio data with configurable parameters
4. **Real-time Processing**: Live audio effects and filtering
5. **Spectrum Analysis**: FFT analysis with frequency domain visualization
6. **Audio Streaming**: Real-time audio data streaming to web dashboard

## Web Dashboard Features

Access the web dashboard at `http://localhost:8080` to:
- Monitor real-time audio levels and frequency spectrum
- Control audio playback and recording parameters
- Visualize audio waveforms and spectrograms
- Adjust audio effects and processing settings
- Export recorded audio and analysis data

## Docker Services

The docker-compose setup includes:
- **edpm-server**: Core EDPM server with I2S protocol handler
- **edpm-dashboard**: Web-based audio monitoring and control
- **audio-processor**: I2S audio processing application
- **pulseaudio**: Audio server for container audio routing
- **icecast**: Audio streaming server for remote monitoring

## Hardware Requirements

- Raspberry Pi or compatible I2S-capable device
- I2S microphone (e.g., SPH0645, INMP441)
- I2S DAC/amplifier (e.g., MAX98357A, PCM5102A)
- Speakers or headphones for audio output

## I2S Wiring

Standard I2S connections for Raspberry Pi:
- **BCLK (Bit Clock)**: GPIO 18 (Pin 12)
- **LRCLK (LR Clock)**: GPIO 19 (Pin 35) 
- **DIN (Data In)**: GPIO 20 (Pin 38)
- **DOUT (Data Out)**: GPIO 21 (Pin 40)

## Audio Formats

Supported audio configurations:
- **Sample Rates**: 8kHz, 16kHz, 22.05kHz, 44.1kHz, 48kHz, 96kHz
- **Bit Depths**: 16-bit, 24-bit, 32-bit
- **Channels**: Mono, Stereo, Multi-channel
- **Formats**: PCM, I2S, TDM

## Simulator Mode

The example supports audio simulator mode for development without hardware:
```bash
export I2S_SIMULATOR=true
docker-compose up
```

## Signal Processing

Available audio processing features:
- **Low-pass/High-pass Filters**: Configurable cutoff frequencies
- **Equalizer**: Multi-band frequency adjustment
- **Compressor**: Dynamic range control
- **Echo/Reverb**: Time-based effects
- **Amplitude Modulation**: Ring modulation effects

## Audio Analysis

Real-time analysis capabilities:
- **Time Domain**: Waveform visualization, RMS levels, peak detection
- **Frequency Domain**: FFT spectrum analysis, spectrogram display
- **Psychoacoustic**: A-weighted levels, bark scale analysis
- **Statistics**: Signal-to-noise ratio, total harmonic distortion

## Use Cases

This example is suitable for:
- Audio quality testing and measurement
- Industrial noise monitoring
- Voice communication systems
- Audio effects development
- Sound level monitoring
- Audio device calibration

## Troubleshooting

1. **Audio Device Not Found**: Check I2S interface configuration
2. **Crackling/Distorted Audio**: Adjust buffer sizes and sample rates
3. **No Audio Input**: Verify microphone connections and power
4. **Docker Audio Issues**: Ensure PulseAudio container is running
5. **Permission Issues**: Check audio device access permissions

For more help, check the main EDPM documentation and I2S hardware guides.
