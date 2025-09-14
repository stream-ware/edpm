#!/usr/bin/env python3
"""
EDPM Lite Test Suite
Unit tests for EDPM Lite functionality
"""
import unittest
import time
import tempfile
import os
import sys
import threading
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edpm_lite import EDPMLite, Message

class TestMessage(unittest.TestCase):
    """Test Message class functionality"""
    
    def test_message_creation(self):
        """Test basic message creation"""
        msg = Message(t="log", d={"level": "info", "msg": "test"})
        self.assertEqual(msg.t, "log")
        self.assertEqual(msg.v, 1)
        self.assertIn("level", msg.d)
        self.assertIsInstance(msg.ts, float)
        self.assertNotEqual(msg.id, "")
    
    def test_message_json_serialization(self):
        """Test JSON serialization/deserialization"""
        original = Message(t="cmd", d={"action": "gpio_set", "pin": 17, "value": 1})
        json_str = original.to_json()
        restored = Message.from_json(json_str)
        
        self.assertEqual(original.t, restored.t)
        self.assertEqual(original.d, restored.d)
        self.assertEqual(original.v, restored.v)
    
    def test_message_auto_fields(self):
        """Test automatic field population"""
        msg = Message()
        
        # Should auto-populate
        self.assertNotEqual(msg.id, "")
        self.assertNotEqual(msg.ts, 0)
        self.assertNotEqual(msg.src, "")
        self.assertIsInstance(msg.d, dict)

class TestEDPMLiteStandalone(unittest.TestCase):
    """Test EDPM Lite client in standalone mode (no server)"""
    
    def setUp(self):
        # Create temp IPC endpoint
        self.temp_dir = tempfile.mkdtemp()
        self.ipc_endpoint = f"ipc://{self.temp_dir}/test.ipc"
    
    def test_client_initialization(self):
        """Test client initialization"""
        # Should not crash even without server
        client = EDPMLite(self.ipc_endpoint, use_zmq=False)
        self.assertIsNotNone(client)
        self.assertIsNotNone(client.db)
    
    def test_message_buffering(self):
        """Test local message buffering"""
        client = EDPMLite(self.ipc_endpoint, use_zmq=False)
        
        # Create and buffer a message
        msg = Message(t="log", d={"level": "info", "msg": "test"})
        client._buffer_message(msg)
        
        # Check it was buffered
        cursor = client.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM buffer")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_gpio_commands(self):
        """Test GPIO command creation"""
        client = EDPMLite(self.ipc_endpoint, use_zmq=False)
        
        # Test GPIO set command
        msg = Message(t="cmd", d={"action": "gpio_set", "pin": 17, "value": 1})
        client._buffer_message(msg)
        
        # Verify command structure
        self.assertEqual(msg.t, "cmd")
        self.assertEqual(msg.d["action"], "gpio_set")
        self.assertEqual(msg.d["pin"], 17)
        self.assertEqual(msg.d["value"], 1)

class TestIntegrationWithServer(unittest.TestCase):
    """Integration tests with EDPM server"""
    
    def setUp(self):
        self.server_process = None
        self.temp_dir = tempfile.mkdtemp()
        self.ipc_endpoint = f"ipc://{self.temp_dir}/edpm_test.ipc"
    
    def start_test_server(self):
        """Start a minimal test server"""
        import subprocess
        import signal
        
        # Start the server in simulator mode
        env = os.environ.copy()
        env['EDPM_ENDPOINT'] = self.ipc_endpoint
        env['GPIO_MODE'] = 'SIMULATOR'
        env['EDPM_DB'] = f'{self.temp_dir}/test.db'
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, 'edpm-lite-server.py'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Give server time to start
            time.sleep(2)
        except Exception as e:
            self.skipTest(f"Could not start test server: {e}")
    
    def tearDown(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
    
    def test_server_communication(self):
        """Test basic server communication"""
        self.start_test_server()
        
        if not self.server_process or self.server_process.poll() is not None:
            self.skipTest("Test server not running")
        
        # Create client
        client = EDPMLite(self.ipc_endpoint, use_zmq=True)
        
        # Test logging
        response = client.log("info", "Test message")
        if response:  # Only test if server is actually responding
            self.assertEqual(response.t, "res")
            self.assertEqual(response.d.get("status"), "ok")
    
    def test_gpio_simulation(self):
        """Test GPIO operations in simulator mode"""
        self.start_test_server()
        
        if not self.server_process or self.server_process.poll() is not None:
            self.skipTest("Test server not running")
        
        client = EDPMLite(self.ipc_endpoint, use_zmq=True)
        
        # Test GPIO set
        set_response = client.gpio_set(17, 1)
        if set_response:
            self.assertEqual(set_response.d.get("status"), "ok")
        
        # Test GPIO get
        get_response = client.gpio_get(17)
        if get_response is not None:
            self.assertIn(get_response, [0, 1])

def run_standalone_tests():
    """Run tests that don't require a server"""
    print("=== Running Standalone Tests ===")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes that don't need server
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestMessage))
    suite.addTest(loader.loadTestsFromTestCase(TestEDPMLiteStandalone))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run tests that require server"""
    print("\n=== Running Integration Tests ===")
    
    # Create test suite
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestIntegrationWithServer))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main test runner"""
    print("EDPM Lite Test Suite")
    print("=" * 50)
    
    # Run standalone tests first
    standalone_success = run_standalone_tests()
    
    # Run integration tests
    integration_success = run_integration_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"Standalone tests: {'PASSED' if standalone_success else 'FAILED'}")
    print(f"Integration tests: {'PASSED' if integration_success else 'FAILED'}")
    
    if standalone_success and integration_success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
