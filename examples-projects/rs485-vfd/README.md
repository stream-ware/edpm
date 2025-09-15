# RS485/Modbus VFD Control Example Project

This example demonstrates RS485/Modbus communication for Variable Frequency Drive (VFD) motor control using the EDPM Lite framework with Docker deployment.

## Features

- Modbus RTU communication over RS485
- VFD motor speed control and monitoring
- Power meter data collection
- Temperature controller integration
- Real-time motor parameter monitoring
- Industrial dashboard with control panels
- Docker containerization for easy deployment

## Industrial Applications

- **Motor Control**: Variable frequency drives for pumps, fans, conveyors
- **Power Monitoring**: Real-time power consumption and efficiency analysis
- **Process Control**: Temperature controllers, pressure regulators
- **Energy Management**: Power factor monitoring, demand control
- **Predictive Maintenance**: Vibration analysis, thermal monitoring

## Quick Start

### Using Docker (Recommended)

```bash
# Start the complete EDPM RS485/Modbus VFD control stack
docker-compose up -d

# View logs
docker-compose logs -f vfd-controller

# Stop the stack
docker-compose down
```

### Manual Setup

1. Install EDPM Lite package with RS485 support:
```bash
pip install edpm-lite[rs485]
```

2. Run the RS485 VFD control example:
```bash
python rs485_vfd_example.py
```

3. Access the web dashboard:
```bash
# Open browser to http://localhost:8080
```

## Configuration

Edit `config.json` to customize:
- RS485 interface settings (port, baud rate, parity)
- Modbus device addresses and parameters
- VFD control parameters and safety limits
- Power monitoring and logging settings

## Project Structure

```
rs485-vfd/
├── rs485_vfd_example.py    # Main VFD control script
├── modbus_devices.json     # Device configuration database
├── config.json            # Main configuration file
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container setup
├── requirements.txt       # Python dependencies
├── control_panels/        # Web-based control interfaces
└── README.md              # This file
```

## RS485/Modbus Operations

The example demonstrates:

1. **Device Discovery**: Automatic Modbus device scanning
2. **VFD Control**: Start/stop motors, speed control, direction control
3. **Parameter Monitoring**: Real-time motor parameters (current, voltage, frequency)
4. **Power Analysis**: Power consumption, efficiency calculations
5. **Safety Systems**: Emergency stops, fault detection and recovery
6. **Data Logging**: Historical data collection for analysis

## Web Dashboard Features

Access the web dashboard at `http://localhost:8080` to:
- Control multiple VFD motors with intuitive panels
- Monitor real-time motor parameters and power consumption
- View historical trends and efficiency reports
- Configure safety parameters and alarm thresholds
- Export data for maintenance and analysis

## Docker Services

The docker-compose setup includes:
- **edpm-server**: Core EDPM server with RS485 protocol handler
- **edpm-dashboard**: Industrial web dashboard with VFD control panels
- **vfd-controller**: RS485/Modbus VFD control application
- **modbus-simulator**: Hardware-in-the-loop simulator for development
- **influxdb**: Time-series database for industrial data storage
- **grafana**: Industrial process visualization and analytics

## Hardware Requirements

- RS485/USB converter (e.g., USB-to-RS485 adapter)
- VFD with Modbus RTU support (e.g., Schneider, ABB, Siemens)
- Industrial motors and control equipment
- Power meters with Modbus communication

## RS485 Wiring

Standard RS485 connections:
- **A (D+)**: Positive differential signal
- **B (D-)**: Negative differential signal  
- **GND**: Signal ground (optional but recommended)
- **Termination**: 120Ω resistors at network ends

## Modbus Device Support

Supported device types:
- **VFDs**: Variable Frequency Drives from major manufacturers
- **Power Meters**: Energy monitoring and power quality analysis
- **Temperature Controllers**: PID temperature control systems
- **I/O Modules**: Digital and analog input/output expansion
- **HMI Panels**: Human-machine interface devices

## Simulator Mode

The example supports Modbus simulator mode for development without hardware:
```bash
export RS485_SIMULATOR=true
docker-compose up
```

## Safety Features

Industrial safety implementations:
- **Emergency Stop**: Immediate motor shutdown capability
- **Safety Interlocks**: Configurable safety logic
- **Fault Detection**: Automatic error detection and reporting
- **Parameter Limits**: Configurable operational boundaries
- **Redundancy**: Backup communication and control paths

## VFD Parameters

Common VFD control parameters:
- **Speed Reference**: Target motor speed (0-100%)
- **Run/Stop**: Motor start and stop commands
- **Direction**: Forward/reverse rotation control
- **Acceleration/Deceleration**: Ramp rates for smooth operation
- **Current Limit**: Maximum motor current protection

## Power Monitoring

Power analysis features:
- **Real Power**: Active power consumption (kW)
- **Reactive Power**: Reactive power measurement (kVAR)
- **Power Factor**: Efficiency indicator
- **Energy Consumption**: Total energy usage (kWh)
- **Demand Analysis**: Peak demand monitoring

## Industrial Standards

Compliance with industrial standards:
- **Modbus RTU**: RS485-based Modbus protocol
- **IEC 61131**: Industrial automation programming
- **NEMA Standards**: Motor and drive specifications
- **IEC 61800**: Variable speed drive standards

## Troubleshooting

1. **Communication Errors**: Check RS485 wiring and termination
2. **Device Not Responding**: Verify Modbus address and baud rate
3. **Motor Not Starting**: Check safety interlocks and enable signals
4. **Power Measurement Issues**: Verify current transformer connections
5. **Docker Issues**: Ensure proper serial device mapping

For more help, check the main EDPM documentation and industrial automation guides.
