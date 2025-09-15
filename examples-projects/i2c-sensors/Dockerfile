FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    i2c-tools \
    libi2c-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY i2c_sensor_example.py .
COPY config.json .
COPY sensor_configs.json .

# Create directories for data and logs
RUN mkdir -p /app/logs /app/data_exports

# Environment variables for EDPM configuration
ENV EDPM_ENDPOINT="ipc:///tmp/edpm.ipc"
ENV EDPM_DEBUG="false"
ENV I2C_SIMULATOR="true"
ENV PYTHONPATH="/app"

# Run the I2C sensor monitoring example
CMD ["python", "i2c_sensor_example.py"]
