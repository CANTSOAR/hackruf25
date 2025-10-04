#!/usr/bin/env python3
"""
Flask Web Application for AI Agent Scheduling System
Provides a responsive web interface for the agent-based scheduling system
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import traceback

# Import agent modules
from agents.baseagent import BaseAgent
from agents.gatherer import gatherer
from agents.scheduler import SCHEDULER
from agents.orchestrator import ORCHESTOR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Global message log for session management
message_logs = {}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with the orchestrator agent"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Initialize session if not exists
        if session_id not in message_logs:
            message_logs[session_id] = []
        
        # Add user message to log
        message_logs[session_id].append({
            'type': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Process with orchestrator
        try:
            response = ORCHESTOR.run(user_message)
            
            # Add agent response to log
            message_logs[session_id].append({
                'type': 'agent',
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'response': response,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
            error_response = f"I encountered an error processing your request: {str(e)}"
            
            message_logs[session_id].append({
                'type': 'error',
                'content': error_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'response': error_response,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
    
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/process-assignment', methods=['POST'])
def process_assignment():
    """Process a Canvas assignment using the gatherer agent"""
    try:
        data = request.get_json()
        assignment_url = data.get('assignment_url', '').strip()
        course_id = data.get('course_id', '').strip()
        
        if not assignment_url:
            return jsonify({'error': 'Assignment URL is required'}), 400
        
        # Use gatherer agent to process assignment
        query = f"Process this Canvas assignment: {assignment_url}"
        if course_id:
            query += f" for course {course_id}"
        
        response = gatherer.run(query)
        
        return jsonify({
            'result': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Assignment processing error: {str(e)}")
        return jsonify({'error': f'Error processing assignment: {str(e)}'}), 500

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get calendar events"""
    try:
        calendar_id = request.args.get('calendar_id', 'primary')
        
        # Use scheduler agent to get events
        response = SCHEDULER.run(f"List all events from calendar {calendar_id}")
        
        return jsonify({
            'events': response,
            'calendar_id': calendar_id,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Calendar events error: {str(e)}")
        return jsonify({'error': f'Error getting calendar events: {str(e)}'}), 500

@app.route('/api/calendar/create-event', methods=['POST'])
def create_calendar_event():
    """Create a new calendar event"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        start_time = data.get('start_time', '').strip()
        end_time = data.get('end_time', '').strip()
        calendar_id = data.get('calendar_id', 'primary')
        description = data.get('description', '')
        
        if not all([title, start_time, end_time]):
            return jsonify({'error': 'Title, start_time, and end_time are required'}), 400
        
        # Use scheduler agent to create event
        query = f"Create event '{title}' from {start_time} to {end_time} on calendar {calendar_id}"
        if description:
            query += f" with description: {description}"
        
        response = SCHEDULER.run(query)
        
        return jsonify({
            'result': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Calendar creation error: {str(e)}")
        return jsonify({'error': f'Error creating calendar event: {str(e)}'}), 500

@app.route('/api/calendar/list', methods=['GET'])
def list_calendars():
    """List available calendars"""
    try:
        response = SCHEDULER.run("List all available calendars")
        
        return jsonify({
            'calendars': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Calendar listing error: {str(e)}")
        return jsonify({'error': f'Error listing calendars: {str(e)}'}), 500

@app.route('/api/messages/<session_id>')
def get_messages(session_id):
    """Get message history for a session"""
    try:
        messages = message_logs.get(session_id, [])
        return jsonify({
            'messages': messages,
            'session_id': session_id
        })
    
    except Exception as e:
        logger.error(f"Message retrieval error: {str(e)}")
        return jsonify({'error': f'Error retrieving messages: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'agents': {
            'orchestrator': 'active',
            'gatherer': 'active', 
            'scheduler': 'active'
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create notes directory if it doesn't exist
    os.makedirs('agents/notes', exist_ok=True)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', 'False').lower() == 'true'
    )
