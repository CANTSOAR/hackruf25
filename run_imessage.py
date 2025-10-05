#!/usr/bin/env python3
"""
iMessage-Style AI Agent Chat - Startup Script
Handles database setup and launches the iMessage-style interface
"""

import os
import sys
import subprocess
import time
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
        import streamlit
        import snowflake.connector
        print("✅ Required dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
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

def check_env_file():
    """Check if .env file exists and create template"""
    if not Path(".env").exists():
        print("⚠️  .env file not found")
        print("Creating template .env file...")
        
        env_template = """# AI Agent Chat - Environment Variables
# Snowflake Database Configuration
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=AI_AGENT_SCHEDULER
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# AI Agent Configuration
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here

# Optional - Canvas integration
CANVAS_API_URL=https://your-canvas-instance.instructure.com/api/v1
CANVAS_API_TOKEN=your_canvas_token_here

# Optional - Google Calendar
GOOGLE_CREDENTIALS_FILE=credentials.json

# Application Settings
DEBUG=False
PORT=8501
"""
        
        with open(".env", "w") as f:
            f.write(env_template)
        
        print("✅ Created .env template file")
        print("📝 Please edit .env file with your database and API keys")
        return False
    else:
        print("✅ .env file found")
        return True

def setup_database():
    """Setup MySQL database"""
    print("🗄️  Setting up database...")
    try:
        from database_setup import setup_database
        if setup_database():
            print("✅ Database setup completed")
            return True
        else:
            print("❌ Database setup failed")
            return False
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        print("💡 Make sure Snowflake is accessible and credentials are correct")
        return False

def check_snowflake_connection():
    """Check Snowflake connection"""
    try:
        from dotenv import load_dotenv
        import snowflake.connector
        from snowflake.connector import Error
        
        load_dotenv()
        
        connection = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER', 'your_username'),
            password=os.getenv('SNOWFLAKE_PASSWORD', 'your_password'),
            account=os.getenv('SNOWFLAKE_ACCOUNT', 'your_account'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'AI_AGENT_SCHEDULER'),
            schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
        )
        
        if connection:
            print("✅ Snowflake connection successful")
            connection.close()
            return True
        else:
            print("❌ Snowflake connection failed")
            return False
            
    except Error as e:
        print(f"❌ Snowflake connection error: {e}")
        print("💡 Please check your Snowflake credentials in .env file")
        return False

def launch_imessage_app():
    """Launch iMessage-style Streamlit app"""
    print("\n🚀 Launching AI Agent Chat...")
    print("=" * 60)
    print("💬 iMessage-Style Interface")
    print("🤖 AI Agent Communication")
    print("📱 iPhone-Inspired Design")
    print("=" * 60)
    print("\n📱 The application will open in your browser automatically")
    print("🌐 URL: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    print("=" * 60)
    
    try:
        # Launch Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_imessage.py",
            "--server.port", "8501",
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        sys.exit(1)

def main():
    """Main startup function"""
    print("💬 AI Agent Chat - iMessage Style Interface")
    print("=" * 50)
    print("🤖 iPhone-Inspired Design • MySQL Database • Real-time Chat")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
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
        print("1. Edit the .env file with your Snowflake credentials and API keys")
        print("2. Make sure Snowflake is accessible")
        print("3. Run this script again")
        sys.exit(1)
    
    # Check Snowflake connection
    if not check_snowflake_connection():
        print("\n❌ Cannot connect to Snowflake database")
        print("Please check your Snowflake credentials and ensure Snowflake is accessible")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("\n❌ Database setup failed")
        print("Please check your Snowflake connection and try again")
        sys.exit(1)
    
    # Launch application
    launch_imessage_app()

if __name__ == "__main__":
    main()
