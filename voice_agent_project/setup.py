#!/usr/bin/env python3
"""
Setup script for Voice Conversation Agent
Handles installation and configuration.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True


def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Set up environment variables."""
    print("🔧 Setting up environment variables...")
    
    env_file = Path(".env")
    env_example = Path("env_example.txt")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        # Copy example to .env
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from example")
        print("📝 Please edit .env file and add your API keys:")
        print("   - ELEVENLABS_API_KEY")
        print("   - GEMINI_API_KEY") 
        print("   - ELEVENLABS_VOICE_ID")
        return True
    else:
        print("❌ env_example.txt not found")
        return False


def check_audio_system():
    """Check if audio system is working."""
    print("🔊 Checking audio system...")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"✅ Audio devices found: {len(devices)}")
        
        # Check for input devices
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if input_devices:
            print(f"✅ Microphone devices found: {len(input_devices)}")
        else:
            print("⚠️ No microphone devices found")
            
        return True
    except ImportError:
        print("❌ sounddevice not installed")
        return False
    except Exception as e:
        print(f"⚠️ Audio system check failed: {e}")
        return False


def test_api_connections():
    """Test API connections if keys are available."""
    print("🌐 Testing API connections...")
    
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    
    if not all([elevenlabs_key, gemini_key, voice_id]):
        print("⚠️ API keys not set in environment variables")
        print("💡 Set them in .env file or run: source .env")
        return True
    
    try:
        # Test Gemini connection
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello")
        
        if response.text:
            print("✅ Gemini API connection successful")
        else:
            print("⚠️ Gemini API response empty")
            
    except Exception as e:
        print(f"⚠️ Gemini API test failed: {e}")
    
    try:
        # Test ElevenLabs connection
        import requests
        headers = {'xi-api-key': elevenlabs_key}
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ ElevenLabs API connection successful")
        else:
            print(f"⚠️ ElevenLabs API test failed: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ ElevenLabs API test failed: {e}")
    
    return True


def main():
    """Main setup function."""
    print("🎤 Voice Conversation Agent Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Check audio system
    check_audio_system()
    
    # Test API connections
    test_api_connections()
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your API keys")
    print("2. Run: python voice_agent.py")
    print("3. Or run web interface: python web_integration_example.py flask")
    print("\n💡 For help, check the README or run: python voice_agent.py --help")


if __name__ == "__main__":
    main()
