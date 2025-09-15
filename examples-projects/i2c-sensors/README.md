# I2C Sensor Monitoring Example Project

This example demonstrates I2C sensor communication and monitoring using the EDPM Lite framework with Docker deployment.

## Features

- I2C device scanning and detection
- Multiple sensor support (temperature, humidity, pressure, accelerometer)
- Real-time sensor data collection
- Data visualization on web dashboard
- Historical data logging and analysis
- Docker containerization for easy deployment

## Supported Sensors

- **BME280**: Temperature, humidity, and pressure sensor
- **MPU6050**: 6-axis accelerometer and gyroscope
- **DS3231**: Real-time clock module
- **Generic sensors**: Temperature sensors, ADC modules, etc.

## Quick Start

### Using Docker (Recommended)

```bash
# Start the complete EDPM I2C sensor monitoring stack
docker-compose up -d

# View logs
docker-compose logs -f sensor-monitor

# Stop the stack
docker-compose down
```

### Manual Setup

1. Install EDPM Lite package:
```bash
pip install edpm-lite[i2c]
```

2. Run the I2C sensor monitoring example:
```bash
python i2c_sensor_example.py
```

3. Access the web dashboard:
```bash
# Open browser to http://localhost:8080
```

## Configuration

Edit `config.json` to customize:
- I2C bus configuration
- Sensor addresses and types
- Data collection intervals
- Logging and storage settings

## Project Structure

```
i2c-sensors/
├── i2c_sensor_example.py   # Main sensor monitoring script
├── sensor_configs.json     # Sensor configuration database
├── config.json            # Main configuration file
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container setup
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## I2C Operations

The example demonstrates:

1. **Device Scanning**: Automatic I2C device discovery
2. **Sensor Reading**: Continuous data collection from multiple sensors
3. **Data Processing**: Raw data conversion and calibration
4. **Real-time Monitoring**: Live data streaming to web dashboard
5. **Data Logging**: Persistent storage for historical analysis
6. **Error Handling**: Robust error recovery and sensor validation

## Web Dashboard Features

Access the web dashboard at `http://localhost:8080` to:
- View real-time sensor readings with interactive charts
- Monitor I2C bus status and connected devices
- Configure sensor parameters and sampling rates
- Export historical data for analysis
- Set up alerts and thresholds

## Docker Services

The docker-compose setup includes:
- **edpm-server**: Core EDPM server with I2C protocol handler
- **edpm-dashboard**: Web-based monitoring and visualization
- **sensor-monitor**: I2C sensor data collection application
- **influxdb**: Time-series database for sensor data storage
- **grafana**: Advanced data visualization and dashboards

## Hardware Requirements

- Raspberry Pi or compatible I2C-capable device
- I2C sensors (BME280, MPU6050, etc.)
- Pull-up resistors for I2C lines (typically 4.7kΩ)

## I2C Wiring

Standard I2C connections:
- **SDA**: GPIO 2 (Pin 3) on Raspberry Pi
- **SCL**: GPIO 3 (Pin 5) on Raspberry Pi
- **VCC**: 3.3V or 5V (depending on sensor)
- **GND**: Ground

## Simulator Mode

The example supports simulator mode for development without hardware:
```bash
export I2C_SIMULATOR=true
docker-compose up
```

## Sensor Configuration

Add new sensors in `sensor_configs.json`:
```json
{
  "0x76": {
    "name": "BME280",
    "type": "environmental",
    "registers": {
      "temperature": 0xFA,
      "pressure": 0xF7,
      "humidity": 0xFD
    }
  }
}
```

## Data Analysis

Collected sensor data can be analyzed using:
- Built-in web dashboard charts
- Grafana dashboards for advanced visualization
- Data export to CSV/JSON formats
- Python scripts for custom analysis

## Troubleshooting

1. **I2C Permission Issues**: Ensure user is in `i2c` group
2. **Sensor Not Detected**: Check wiring and I2C address
3. **Data Reading Errors**: Verify sensor power and pull-up resistors
4. **Port Conflicts**: Ensure ports 8080, 3000, 8086 are available

For more help, check the main EDPM documentation.
