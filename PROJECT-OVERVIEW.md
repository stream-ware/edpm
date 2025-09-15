# EDPM Lite - Complete Project Overview

## 🚀 **Project Vision**

EDPM Lite is a comprehensive **Embedded Device Process Manager** with an advanced **Web UI Dashboard** for real-time monitoring and control of industrial protocols. Designed for Raspberry Pi and embedded systems, it provides a unified interface for GPIO, I2C, I2S, and RS485/Modbus communications.

---

## 🌟 **Key Features & Capabilities**

### **Core Framework**
- ✅ **Lightweight Architecture** - < 10MB RAM footprint on RPi3
- ✅ **Universal Protocol** - Simple JSON over ZeroMQ/WebSocket
- ✅ **Multi-language Ready** - 5-minute implementation in any language
- ✅ **Docker Native** - Complete containerized environment
- ✅ **Production Ready** - SQLite storage, graceful shutdown, error handling

### **🌐 Web UI Dashboard**
- ✅ **Modern Responsive Design** - Works on desktop, tablet, mobile
- ✅ **Real-time Monitoring** - WebSocket-based live data streaming
- ✅ **Interactive Controls** - Buttons, sliders, toggles for all protocols
- ✅ **Professional Charts** - Chart.js integration with live data
- ✅ **Dark Theme UI** - Professional appearance with modern styling
- ✅ **Multi-protocol Support** - Unified interface for all communications

### **🔌 Extended Protocol Support**

#### **GPIO Control**
- Real-time pin monitoring and control
- PWM signal generation and control
- Interactive toggle buttons and status LEDs
- Live charts showing pin history and patterns
- Multi-pin pattern generation

#### **🌡️ I2C Sensor Integration**
- **BME280** - Temperature, humidity, pressure monitoring
- **ADS1115** - 4-channel ADC with live readings
- **Bus Scanning** - Automatic device detection
- **Live Sensor Charts** - Historical data visualization
- **Configurable Parameters** - Sensor-specific settings

#### **🔊 I2S Audio Processing**
- **Test Tone Generation** - Multiple frequencies (440Hz, 880Hz, 1760Hz)
- **Audio Recording** - Real-time capture and playback
- **Live Waveform Display** - Real-time audio visualization
- **FFT Analysis** - Frequency domain analysis
- **Level Metering** - Real-time audio level monitoring

#### **⚡ RS485/Modbus Communication**
- **VFD Control** - Variable Frequency Drive management
- **Power Monitoring** - Industrial power meter integration
- **Device Communication** - Generic Modbus device support
- **Speed Control** - Interactive slider-based control
- **Status Monitoring** - Real-time device status

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        EDPM Lite Core                           │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Web UI Dashboard │ 🔌 WebSocket Server │ 📊 Real-time Data  │
├─────────────────────────────────────────────────────────────────┤
│          Simple Message Protocol (SMP)                          │
│         JSON ← ZeroMQ IPC / WebSocket / HTTP                   │
├─────────────────────────────────────────────────────────────────┤
│ Process Manager │ Logger │ Event Router │ Protocol Handlers    │
├─────────────────────────────────────────────────────────────────┤
│  GPIO │ I2C │ I2S │ RS485 │ Protocol Simulators │ Live Charts  │
├─────────────────────────────────────────────────────────────────┤
│         SQLite (RAM) │ Config (JSON) │ Static Assets           │
└─────────────────────────────────────────────────────────────────┘
```

### **Architecture Layers:**
1. **Web UI Layer** - Modern dashboard with real-time monitoring
2. **Communication Layer** - WebSocket + ZeroMQ + HTTP
3. **Protocol Layer** - GPIO, I2C, I2S, RS485 handlers
4. **Hardware Layer** - Physical hardware + Docker simulators
5. **Storage Layer** - SQLite + JSON configuration

---

## 🚀 **Quick Start Guide**

### **Local Development**
```bash
# Clone repository
git clone <repository-url>
cd edpm

# Install dependencies
pip3 install -r requirements.txt

# Start EDPM server with Web Dashboard
python3 edpm-lite-server.py

# Open dashboard in browser
open http://localhost:8080
```

### **Docker Environment**
```bash
# Start complete environment with simulators
make extended-up

# Access Web Dashboard
open http://localhost:8080

# View logs
make extended-logs

# Stop environment
make extended-down
```

---

## 📊 **Dashboard Features**

### **Real-time Monitoring Panels**

| Panel | Features | Capabilities |
|-------|----------|-------------|
| 🔌 **GPIO** | Toggle controls, status LEDs, PWM sliders | Real-time pin control and monitoring |
| 🌡️ **I2C** | Sensor readings, bus scanning, live charts | Environmental monitoring and ADC |
| 🔊 **I2S** | Audio generation, recording, waveforms | Sound testing and analysis |
| ⚡ **RS485** | VFD control, power monitoring, device comm | Industrial automation control |
| 📊 **System** | CPU/RAM usage, message rates, uptime | System performance monitoring |
| 📝 **Logs** | Live colored logs, filtering, search | Real-time system diagnostics |

### **Interactive Controls**
- **Buttons** - Instant command execution
- **Sliders** - Continuous value control (PWM, VFD speed)
- **Toggles** - Binary state control (GPIO pins)
- **Charts** - Live data visualization with Chart.js
- **Status Indicators** - Connection and system status

---

## 🔄 **WebSocket Communication**

Real-time bidirectional communication between dashboard and server:

```javascript
// WebSocket connection
const ws = new WebSocket(`ws://${window.location.host}/ws`);

// Receive real-time data
ws.onmessage = function(event) {
    const msg = JSON.parse(event.data);
    updateDashboard(msg);
};

// Send commands
function sendCommand(action, params) {
    const msg = { v: 1, t: 'cmd', d: { action, ...params } };
    ws.send(JSON.stringify(msg));
}
```

---

## 🧪 **Testing & Simulation**

### **Protocol Simulators**
- **GPIO Simulator** - Virtual pin states and PWM
- **I2C Simulator** - BME280, ADS1115 sensor simulation
- **I2S Simulator** - Audio generation and processing
- **RS485 Simulator** - VFD and power meter simulation

### **Automated Testing**
```bash
# Run all tests
make test

# Run specific protocol tests
python3 -m pytest tests/test_i2c.py
python3 -m pytest tests/test_i2s.py
python3 -m pytest tests/test_rs485.py
```

### **Manual Testing via Dashboard**
1. **GPIO Testing** - Toggle pins, observe LED changes
2. **I2C Testing** - Read sensors, scan bus, monitor trends
3. **Audio Testing** - Generate tones, record, analyze FFT
4. **RS485 Testing** - Control VFD speed, monitor power

---

## ⚙️ **Configuration**

### **Environment Variables**
```bash
# Core settings
EDPM_ENDPOINT=ipc:///tmp/edpm.ipc
EDPM_PORT=8080
EDPM_DB=/dev/shm/edpm.db
EDPM_DEBUG=true

# Protocol simulators
GPIO_MODE=SIMULATOR
I2C_SIMULATOR=true
I2S_SIMULATOR=true
RS485_SIMULATOR=true
SIMULATE_SENSORS=true
```

### **JSON Configuration**
```json
{
  "server": {
    "port": 8080,
    "debug": true
  },
  "protocols": {
    "gpio": { "mode": "SIMULATOR" },
    "i2c": { "bus": 1, "simulate": true },
    "i2s": { "sample_rate": 44100, "simulate": true },
    "rs485": { "port": "/dev/ttyUSB0", "simulate": true }
  }
}
```

---

## 📁 **Project Structure**

```
edpm/
├── 📁 web/
│   └── dashboard.html          # Web UI Dashboard
├── 📁 protocols/
│   ├── i2c_handler.py         # I2C protocol implementation
│   ├── i2s_handler.py         # I2S audio implementation
│   └── rs485_handler.py       # RS485/Modbus implementation
├── 📁 tests/
│   ├── test_i2c.py           # I2C protocol tests
│   ├── test_i2s.py           # I2S audio tests
│   └── test_rs485.py         # RS485/Modbus tests
├── 📁 examples/
│   ├── basic_gpio_example.py  # GPIO usage examples
│   └── logging_example.py     # Logging examples
├── 📁 config/
│   └── default.json          # Default configuration
├── edpm_lite.py              # Core client library
├── edpm-lite-server.py       # Main server with Web UI
├── protocol_simulator.py     # Protocol simulators
├── docker-compose.yml        # Basic Docker setup
├── docker-compose-extended.yml # Extended Docker environment
├── Dockerfile               # Server container
├── Dockerfile.simulator     # Simulator container
├── requirements.txt         # Python dependencies
├── Makefile                # Build and deployment
└── 📁 Documentation/
    ├── README.md            # Main project documentation
    ├── edpm-lite-framework.md # Framework documentation
    ├── edpm-protocols-extended.md # Protocol documentation
    └── PROJECT-OVERVIEW.md  # This overview document
```

---

## 🔧 **Development & Deployment**

### **Development Workflow**
1. **Local Development** - Python environment with simulators
2. **Docker Testing** - Containerized environment testing
3. **Hardware Testing** - Real Raspberry Pi deployment
4. **CI/CD Pipeline** - Automated testing and deployment

### **Production Deployment**
```bash
# Production Docker deployment
docker-compose -f docker-compose.yml up -d

# Raspberry Pi deployment
sudo systemctl enable edpm-lite
sudo systemctl start edpm-lite

# Web Dashboard access
curl http://raspberry-pi-ip:8080
```

---

## 📈 **Performance & Scalability**

### **System Requirements**
- **Minimum** - Raspberry Pi 3B+ with 1GB RAM
- **Recommended** - Raspberry Pi 4 with 2GB+ RAM
- **Storage** - 1GB free space for logs and data
- **Network** - Ethernet or WiFi for Web Dashboard access

### **Performance Metrics**
- **Memory Usage** - < 10MB RAM for core system
- **CPU Usage** - < 5% on RPi4 during normal operation
- **WebSocket Latency** - < 10ms for real-time updates
- **Protocol Response** - < 1ms for GPIO/I2C operations

---

## 🌍 **Use Cases & Applications**

### **Industrial Automation**
- Factory equipment monitoring
- Process control systems
- Environmental monitoring
- Quality control systems

### **IoT & Smart Systems**
- Smart building automation
- Agricultural monitoring
- Weather stations
- Security systems

### **Education & Research**
- Embedded systems learning
- Protocol development
- Hardware prototyping
- Research data collection

### **Prototyping & Development**
- Hardware testing
- Protocol validation
- System integration
- Performance analysis

---

## 🤝 **Contributing**

### **Development Setup**
```bash
# Fork and clone repository
git clone https://github.com/your-username/edpm.git
cd edpm

# Create development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
make test

# Start development server
python3 edpm-lite-server.py
```

### **Contribution Guidelines**
1. **Code Style** - Follow PEP 8 for Python code
2. **Testing** - Add tests for new features
3. **Documentation** - Update relevant documentation
4. **Pull Requests** - Use clear descriptions and test results

---

## 📞 **Support & Documentation**

### **Documentation Files**
- **README.md** - Quick start and basic usage
- **edpm-lite-framework.md** - Framework architecture and API
- **edpm-protocols-extended.md** - Extended protocol documentation
- **PROJECT-OVERVIEW.md** - Complete project overview (this file)

### **Getting Help**
- **Issues** - Report bugs and feature requests
- **Discussions** - Community support and questions
- **Wiki** - Extended documentation and tutorials
- **Examples** - Sample code and implementations

---

## 🎯 **Project Status & Roadmap**

### **Current Status (v1.0)**
- ✅ Core EDPM Lite framework completed
- ✅ Web UI Dashboard fully functional
- ✅ Extended protocols implemented (GPIO, I2C, I2S, RS485)
- ✅ Docker environment with simulators
- ✅ Comprehensive documentation
- ✅ Real-time WebSocket communication
- ✅ Professional charting and visualization

### **Future Roadmap**
- 🔄 **SPI Protocol** - Serial Peripheral Interface support
- 🔄 **CAN Bus** - Controller Area Network integration
- 🔄 **Mobile App** - Native mobile application
- 🔄 **Cloud Integration** - Remote monitoring capabilities
- 🔄 **Plugin System** - Extensible protocol architecture
- 🔄 **Multi-device** - Distributed system support

---

**EDPM Lite - Embedded Device Process Manager with Web UI Dashboard**
*Real-time monitoring and control for industrial protocols*

---
