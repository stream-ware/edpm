#!/usr/bin/env python3
"""
Test I2S audio protocol functionality
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from protocols.i2s_handler import I2SHandler, AudioConfig
import edpm_lite

def test_i2s_basic():
    """Test basic I2S functionality"""
    print("🔊 Testing I2S Audio Protocol Handler")
    print("=" * 50)
    
    # Initialize I2S handler in simulator mode
    config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
    i2s = I2SHandler(config=config, simulator=True)
    
    # Test device listing
    print("🎤 Listing audio devices...")
    devices = i2s.list_devices()
    for device in devices:
        print(f"  Device {device['index']}: {device['name']} ({device['channels']}ch, {device['type']})")
    
    if not devices:
        print("❌ No audio devices found")
        return False
    
    # Test tone generation
    print("\n🎵 Testing tone generation...")
    for freq in [440, 880, 1760]:
        print(f"  Generating {freq}Hz tone...")
        tone_data = i2s.generate_tone(freq, duration=0.5, amplitude=0.3)
        analysis = i2s.analyze_audio(tone_data)
        print(f"    Generated tone analysis: {analysis.get('dominant_frequency', 0):.1f}Hz, "
              f"{analysis.get('db_level', -120):.1f}dB")
    
    print("✅ I2S basic tests completed")
    return True

async def test_i2s_playback():
    """Test I2S audio playback"""
    print("\n🔊 Testing I2S audio playback...")
    
    config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
    i2s = I2SHandler(config=config, simulator=True)
    
    # Play test tones
    test_frequencies = [440, 660, 880]  # A4, E5, A5 chord
    
    for freq in test_frequencies:
        print(f"  Playing {freq}Hz tone for 0.5 seconds...")
        await i2s.play_tone(freq, duration=0.5, amplitude=0.3)
        await asyncio.sleep(0.2)  # Small gap between tones
    
    print("✅ I2S playback test completed")
    return True

async def test_i2s_recording():
    """Test I2S audio recording"""
    print("\n🎙️ Testing I2S audio recording...")
    
    config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
    i2s = I2SHandler(config=config, simulator=True)
    
    # Start recording for 2 seconds
    print("  Starting 2-second recording...")
    await i2s.start_recording(duration=2.0)
    
    # Stop and analyze
    recorded_data = i2s.stop_recording()
    
    if len(recorded_data) > 0:
        analysis = i2s.analyze_audio(recorded_data)
        print(f"  Recording analysis: {analysis.get('duration', 0):.2f}s, "
              f"{analysis.get('dominant_frequency', 0):.1f}Hz, "
              f"{analysis.get('db_level', -120):.1f}dB")
        
        # Test playback of recorded audio
        print("  Playing back recorded audio...")
        await i2s.play_audio(recorded_data)
        
        print("✅ I2S recording test completed")
        return True
    else:
        print("❌ No audio data recorded")
        return False

async def test_i2s_continuous():
    """Test continuous I2S monitoring"""
    print("\n🔄 Testing I2S continuous monitoring...")
    
    config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
    i2s = I2SHandler(config=config, simulator=True)
    
    readings = []
    
    async def audio_callback(data):
        readings.append(data)
        print(f"  📊 Audio Analysis: Level={data.get('db_level', -120):.1f}dB, "
              f"Freq={data.get('dominant_frequency', 0):.1f}Hz")
    
    # Start monitoring for 5 seconds
    task = asyncio.create_task(i2s.continuous_monitoring(audio_callback, interval=1.0))
    await asyncio.sleep(5)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    print(f"✅ Collected {len(readings)} audio readings")
    return len(readings) > 0

def test_i2s_with_edpm():
    """Test I2S integration with EDPM"""
    print("\n🔗 Testing I2S with EDPM integration...")
    
    # Initialize EDPM client
    edpm = edpm_lite.EDPMLite(use_zmq=False)  # Offline mode
    config = AudioConfig(sample_rate=44100, channels=2, bit_depth=16)
    i2s = I2SHandler(config=config, simulator=True)
    
    # Generate test audio and analyze
    tone_data = i2s.generate_tone(440, duration=1.0, amplitude=0.5)
    analysis = i2s.analyze_audio(tone_data)
    
    # Log the analysis to EDPM
    edpm.log("info", "Audio analysis", **analysis)
    
    # Emit event
    edpm.emit_event("audio_level", {
        "protocol": "I2S",
        "device": "Audio Interface",
        **analysis
    })
    
    print(f"📝 Logged audio analysis to EDPM: {analysis}")
    print("✅ I2S-EDPM integration test completed")
    return True

async def main():
    """Main test runner"""
    print("🚀 EDPM I2S Audio Protocol Tests")
    print("=" * 50)
    
    tests = [
        ("Basic I2S Operations", test_i2s_basic),
        ("Audio Playback", test_i2s_playback),
        ("Audio Recording", test_i2s_recording),
        ("Continuous Monitoring", test_i2s_continuous),
        ("EDPM Integration", test_i2s_with_edpm),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
            print(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append(False)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Success Rate: {(sum(results)/len(results)*100):.1f}%")
    
    if all(results):
        print("🎉 All I2S tests passed!")
        return 0
    else:
        print("⚠️ Some I2S tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
