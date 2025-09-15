FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1-dev \
    ffmpeg \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY i2s_audio_example.py .
COPY config.json .
COPY audio_configs.json .

# Create directories for recordings and logs
RUN mkdir -p /app/recordings /app/logs /app/audio_samples

# Environment variables for EDPM configuration
ENV EDPM_ENDPOINT="ipc:///tmp/edpm.ipc"
ENV EDPM_DEBUG="false"
ENV I2S_SIMULATOR="true"
ENV PULSE_SERVER="unix:/tmp/pulse-socket"
ENV PYTHONPATH="/app"

# Run the I2S audio processing example
CMD ["python", "i2s_audio_example.py"]
