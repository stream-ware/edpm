# RS485/Modbus VFD Control Example Dockerfile
FROM python:3.10-slim

LABEL maintainer="EDPM Lite Team"
LABEL description="RS485/Modbus VFD Control Example for Industrial IoT"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Install system dependencies for RS485/Modbus communication
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    pkg-config \
    libudev-dev \
    libusb-1.0-0-dev \
    udev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY rs485_vfd_example.py .
COPY config.json .
COPY modbus_devices.json .

# Create directories for logs and data
RUN mkdir -p /var/log /app/data /app/config

# Set environment variables
ENV PYTHONPATH=/app
ENV EDPM_ENDPOINT=ipc:///tmp/edpm.ipc
ENV EDPM_PORT=5555
ENV EDPM_DEBUG=false
ENV RS485_SIMULATOR=false
ENV WEB_ENABLED=true
ENV LOG_LEVEL=INFO

# Configure RS485 device access (will be mounted from host)
ENV RS485_PORT=/dev/ttyUSB0
ENV RS485_BAUDRATE=9600

# Expose ports for web dashboard and monitoring
EXPOSE 8080 9090

# Create non-root user for security
RUN groupadd -r vfdcontrol && useradd -r -g vfdcontrol vfdcontrol
RUN chown -R vfdcontrol:vfdcontrol /app /var/log
USER vfdcontrol

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set the entrypoint
ENTRYPOINT ["python3", "rs485_vfd_example.py"]
