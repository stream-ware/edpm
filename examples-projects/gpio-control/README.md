# GPIO Control Example Project

This example demonstrates basic GPIO control using the EDPM Lite framework with Docker deployment.

## Features

- GPIO pin control (read/write)
- PWM signal generation
- Real-time logging and monitoring
- Web dashboard integration
- Docker containerization for easy deployment

## Quick Start

### Using Docker (Recommended)

```bash
# Start the complete EDPM GPIO example stack
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the stack
docker-compose down
```

### Manual Setup

1. Install EDPM Lite package:
```bash
pip install edpm-lite
```

2. Run the GPIO control example:
```bash
python gpio_example.py
```

3. Access the web dashboard:
```bash
# Open browser to http://localhost:8080
```

## Configuration

Edit `config.json` to customize:
- GPIO pins to control
- Server endpoints
- Logging levels
- Web dashboard settings

## Project Structure

```
gpio-control/
├── gpio_example.py         # Main GPIO control script
├── config.json            # Configuration file
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container setup
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## GPIO Operations

The example demonstrates:

1. **Basic Pin Control**: Set pins HIGH/LOW
2. **Pin Reading**: Read current pin states
3. **PWM Generation**: Generate PWM signals with configurable frequency and duty cycle
4. **Status Monitoring**: Real-time pin status via web dashboard
5. **Logging**: Comprehensive operation logging

## Web Dashboard

Access the web dashboard at `http://localhost:8080` to:
- Monitor GPIO pin states in real-time
- Control pins through the web interface
- View system logs and status
- Generate PWM signals interactively

## Docker Services

The docker-compose setup includes:
- **edpm-server**: Core EDPM server with GPIO protocol handler
- **edpm-dashboard**: Web-based monitoring and control interface
- **gpio-example**: The GPIO control example application

## Hardware Requirements

- Raspberry Pi or compatible GPIO-capable device
- LEDs, buttons, or other GPIO components (optional)

## Simulator Mode

The example supports simulator mode for development without hardware:
```bash
export GPIO_SIMULATOR=true
docker-compose up
```

## Troubleshooting

1. **Permission Issues**: Ensure proper GPIO permissions
2. **Port Conflicts**: Check if ports 8080, 8081 are available
3. **Hardware Issues**: Use simulator mode for development

For more help, check the main EDPM documentation.
