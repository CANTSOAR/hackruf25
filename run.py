#pip#!/usr/bin/env python3
"""
Startup script for AI Agent Scheduler
This script handles environment setup and starts the Flask application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import flask_cors
        print("✅ Flask dependencies found")
        return True
    except ImportError:
        print("❌ Flask dependencies not found")
        return False

def install_dependencies():
    """Install required packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "agents/notes",
        "templates",
        "static/css",
        "static/js"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_env_file():
    """Check if .env file exists"""
    if not Path(".env").exists():
        print("⚠️  .env file not found")
        print("Creating template .env file...")
        
        env_template = """# AI Agent Scheduler Environment Variables
# Copy this file and fill in your actual values

# Required
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here

# Optional - for Canvas integration
CANVAS_API_URL=https://your-canvas-instance.instructure.com/api/v1
CANVAS_API_TOKEN=your_canvas_token_here

# Optional - for Google Calendar
GOOGLE_CREDENTIALS_FILE=credentials.json

# Optional - for production
DEBUG=False
PORT=5000
"""
        
        with open(".env", "w") as f:
            f.write(env_template)
        
        print("✅ Created .env template file")
        print("📝 Please edit .env file with your actual API keys")
        return False
    else:
        print("✅ .env file found")
        return True

def main():
    """Main startup function"""
    print("🚀 Starting AI Agent Scheduler...")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Check dependencies
    if not check_dependencies():
        print("Installing dependencies...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Please run: pip install -r requirements.txt")
            sys.exit(1)
    
    # Check environment file
    env_configured = check_env_file()
    
    if not env_configured:
        print("\n⚠️  Please configure your .env file before running the application")
        print("1. Edit the .env file with your actual API keys")
        print("2. Run this script again")
        sys.exit(1)
    
    # Start the application
    print("\n🎉 Starting Flask application...")
    print("📱 Open your browser and navigate to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the application")
    print("=" * 50)
    
    try:
        from app import app
        app.run(
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('DEBUG', 'False').lower() == 'true'
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
