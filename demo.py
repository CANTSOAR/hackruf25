#!/usr/bin/env python3
"""
Demo script for AI Agent Scheduler
This script demonstrates the core functionality without the web interface
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def demo_orchestrator():
    """Demo the orchestrator agent"""
    print("🤖 ORCHESTRATOR AGENT DEMO")
    print("=" * 40)
    
    try:
        from agents.orchestrator import ORCHESTOR
        
        # Example queries
        queries = [
            "Help me plan my study schedule for next week",
            "I have a math assignment due in 3 days, can you help me plan it?",
            "Create a study session for my computer science course"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n📝 Query {i}: {query}")
            print("-" * 30)
            
            try:
                response = ORCHESTOR.run(query)
                print(f"🤖 Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
    except ImportError as e:
        print(f"❌ Could not import orchestrator: {e}")
        print("Make sure all dependencies are installed")

def demo_gatherer():
    """Demo the gatherer agent"""
    print("\n\n📚 GATHERER AGENT DEMO")
    print("=" * 40)
    
    try:
        from agents.gatherer import gatherer
        
        # Example assignment processing
        print("\n📝 Processing Canvas Assignment...")
        print("-" * 30)
        
        query = """
        I have a Canvas assignment due next week. The assignment URL is:
        https://canvas.example.com/courses/123/assignments/456
        
        Please help me:
        1. Read the assignment details
        2. Find relevant course materials
        3. Create a study plan
        4. Add it to my Google Calendar
        """
        
        try:
            response = gatherer.run(query)
            print(f"🤖 Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Note: This might fail without proper Canvas API credentials")
        
    except ImportError as e:
        print(f"❌ Could not import gatherer: {e}")

def demo_scheduler():
    """Demo the scheduler agent"""
    print("\n\n📅 SCHEDULER AGENT DEMO")
    print("=" * 40)
    
    try:
        from agents.scheduler import SCHEDULER
        
        # Example calendar operations
        queries = [
            "List all my calendars",
            "Show me my upcoming events",
            "Create a study session for tomorrow from 2pm to 4pm"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n📝 Query {i}: {query}")
            print("-" * 30)
            
            try:
                response = SCHEDULER.run(query)
                print(f"🤖 Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Note: This might fail without proper Google Calendar credentials")
        
    except ImportError as e:
        print(f"❌ Could not import scheduler: {e}")

def check_environment():
    """Check if environment is properly configured"""
    print("🔧 ENVIRONMENT CHECK")
    print("=" * 40)
    
    # Check required environment variables
    required_vars = ['GEMINI_API_KEY', 'SECRET_KEY']
    optional_vars = ['CANVAS_API_URL', 'CANVAS_API_TOKEN']
    
    print("Required variables:")
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set")
    
    print("\nOptional variables:")
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Not set (optional)")
    
    # Check if credentials file exists
    if os.path.exists('credentials.json'):
        print("✅ Google Calendar credentials: Found")
    else:
        print("⚠️  Google Calendar credentials: Not found (optional)")
    
    # Check if notes directory exists
    if os.path.exists('agents/notes'):
        print("✅ Notes directory: Found")
    else:
        print("❌ Notes directory: Not found")
        print("Creating notes directory...")
        os.makedirs('agents/notes', exist_ok=True)
        print("✅ Notes directory: Created")

def main():
    """Main demo function"""
    print("🎯 AI AGENT SCHEDULER DEMO")
    print("=" * 50)
    print("This demo shows the core functionality of the AI agents")
    print("For the full web interface, run: python run.py")
    print("=" * 50)
    
    # Check environment
    check_environment()
    
    # Demo each agent
    demo_orchestrator()
    demo_gatherer()
    demo_scheduler()
    
    print("\n\n🎉 DEMO COMPLETE")
    print("=" * 50)
    print("To use the full web interface:")
    print("1. Configure your .env file with API keys")
    print("2. Run: python run.py")
    print("3. Open: http://localhost:5000")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()
