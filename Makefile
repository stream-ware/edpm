# EDPM Extended Protocol Testing Makefile

# Default target
all: build test-all

# Build Docker containers
build:
	@echo "🔨 Building EDPM Extended containers..."
	docker-compose -f docker-compose-extended.yml build
	@echo "✅ Build complete"

# Start extended environment
start:
	@echo "🚀 Starting EDPM Extended environment..."
	docker-compose -f docker-compose-extended.yml up -d
	@echo "✅ Environment started"
	@echo "📊 Dashboard: http://localhost:8082"

# Stop environment
stop:
	@echo "🛑 Stopping EDPM Extended environment..."
	docker-compose -f docker-compose-extended.yml down
	@echo "✅ Environment stopped"

# Test I2C protocols
test-i2c:
	@echo "🔌 Testing I2C protocols..."
	python tests/test_i2c.py
	@echo "✅ I2C tests complete"

# Test I2S audio
test-i2s:
	@echo "🔊 Testing I2S audio protocols..."
	python tests/test_i2s.py
	@echo "✅ I2S tests complete"

# Test RS485/Modbus
test-rs485:
	@echo "⚡ Testing RS485/Modbus protocols..."
	python tests/test_rs485.py
	@echo "✅ RS485 tests complete"

# Test all protocols
test-all: test-i2c test-i2s test-rs485
	@echo "🎉 All protocol tests complete!"

# Clean up
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	docker-compose -f docker-compose-extended.yml down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

# Show logs
logs:
	docker-compose -f docker-compose-extended.yml logs -f

# Create test environment
setup-tests:
	@echo "🔧 Setting up test environment..."
	mkdir -p tests
	mkdir -p protocols
	mkdir -p dashboards
	@echo "✅ Test environment ready"

# Run quick validation
validate:
	@echo "🔍 Validating EDPM Extended setup..."
	@python -c "import edpm_lite; print('✅ EDPM Lite OK')"
	@python -c "import zmq; print('✅ ZeroMQ OK')" 2>/dev/null || echo "⚠️ ZeroMQ not available"
	@echo "✅ Validation complete"

# Help
help:
	@echo "EDPM Extended Protocol Testing"
	@echo "=============================="
	@echo "make build      - Build Docker containers"
	@echo "make start      - Start extended environment"
	@echo "make stop       - Stop environment"
	@echo "make test-i2c   - Test I2C protocols"
	@echo "make test-i2s   - Test I2S audio"
	@echo "make test-rs485 - Test RS485/Modbus"
	@echo "make test-all   - Test all protocols"
	@echo "make clean      - Clean up containers"
	@echo "make logs       - Show container logs"
	@echo "make validate   - Validate setup"
	@echo "make help       - Show this help"

.PHONY: all build start stop test-i2c test-i2s test-rs485 test-all clean logs setup-tests validate help
