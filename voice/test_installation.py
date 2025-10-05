#!/usr/bin/env python3
"""
Test script to verify Voice Agent installation and configuration.
"""

import os
import sys
import importlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test if all required packages can be imported."""
    print("🔍 Testing package imports...")
    
    required_packages = [
        'requests',
        'sounddevice', 
        'numpy',
        'google.generativeai',
        'playsound',
        'dotenv'
    ]
    
    failed_imports = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"  ✅ {package}")
        except ImportError as e:
            print(f"  ❌ {package}: {e}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    else:
        print("✅ All packages imported successfully")
        return True

def test_environment_variables():
    """Test if required environment variables are set."""
    print("\n🔧 Testing environment variables...")
    
    required_vars = [
        'ELEVENLABS_API_KEY',
        'GEMINI_API_KEY',
        'ELEVENLABS_VOICE_ID'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the key for security
            masked_value = value[:8] + '...' if len(value) > 8 else '***'
            print(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Create a .env file with your API keys")
        return False
    else:
        print("✅ All environment variables are set")
        return True

def test_audio_system():
    """Test audio system functionality."""
    print("\n🔊 Testing audio system...")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"  ✅ Audio devices found: {len(devices)}")
        
        # Check for input devices
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if input_devices:
            print(f"  ✅ Microphone devices: {len(input_devices)}")
        else:
            print("  ⚠️ No microphone devices found")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Audio system error: {e}")
        return False

def test_voice_agent_import():
    """Test if voice agent can be imported."""
    print("\n🤖 Testing voice agent import...")
    
    try:
        from voice_agent import VoiceAgent, create_voice_agent_from_env
        print("  ✅ VoiceAgent classes imported successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Voice agent import failed: {e}")
        return False

def test_api_connections():
    """Test API connections if keys are available."""
    print("\n🌐 Testing API connections...")
    
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not elevenlabs_key or not gemini_key:
        print("  ⚠️ Skipping API tests (keys not available)")
        return True
    
    # Test Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Simple test
        response = model.generate_content("Hello, this is a test.")
        if response.text:
            print("  ✅ Gemini API connection successful")
        else:
            print("  ⚠️ Gemini API response empty")
    except Exception as e:
        print(f"  ❌ Gemini API test failed: {e}")
    
    # Test ElevenLabs
    try:
        import requests
        headers = {'xi-api-key': elevenlabs_key}
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("  ✅ ElevenLabs API connection successful")
        else:
            print(f"  ⚠️ ElevenLabs API test failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ ElevenLabs API test failed: {e}")
    
    return True

def main():
    """Run all tests."""
    print("🧪 Voice Agent Installation Test")
    print("=" * 40)
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment Variables", test_environment_variables),
        ("Audio System", test_audio_system),
        ("Voice Agent Import", test_voice_agent_import),
        ("API Connections", test_api_connections)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 20)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your installation is ready.")
        print("💡 Run: python voice_agent.py")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        print("💡 Run: python setup.py for installation help")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
