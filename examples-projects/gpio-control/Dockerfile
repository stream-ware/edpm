FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY gpio_example.py .
COPY config.json .

# Create logs directory
RUN mkdir -p /app/logs

# Environment variables for EDPM configuration
ENV EDPM_ENDPOINT="ipc:///tmp/edpm.ipc"
ENV EDPM_DEBUG="false"
ENV GPIO_SIMULATOR="true"
ENV PYTHONPATH="/app"

# Run the GPIO example
CMD ["python", "gpio_example.py"]
