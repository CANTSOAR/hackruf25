#!/usr/bin/env python3
"""
Web Integration Example for Voice Agent
Shows how to integrate the voice conversation agent with Flask/FastAPI.
"""

import os
import tempfile
import logging
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template_string
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import our voice agent
from voice_agent import create_voice_agent_from_env, process_audio_for_web, VoiceAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize voice agent (this would be done once at startup)
try:
    voice_agent = create_voice_agent_from_env()
    logger.info("Voice agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize voice agent: {e}")
    voice_agent = None


# =============================================================================
# FLASK INTEGRATION EXAMPLE
# =============================================================================

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Conversation Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        button { padding: 10px 20px; font-size: 16px; margin: 10px; }
        .recording { background: #ff4444; color: white; }
        .processing { background: #4444ff; color: white; }
        .response { background: #44ff44; color: white; }
        #status { padding: 10px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 Voice Conversation Agent</h1>
        
        <div id="status">Ready to listen...</div>
        
        <button id="startBtn" onclick="startRecording()">Start Recording</button>
        <button id="stopBtn" onclick="stopRecording()" disabled>Stop Recording</button>
        <button onclick="clearHistory()">Clear History</button>
        
        <div id="conversation"></div>
    </div>

    <script>
        let mediaRecorder;
        let audioChunks = [];
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = () => {
                    processAudio();
                };
                
                mediaRecorder.start();
                
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('status').innerHTML = 'Recording...';
                document.getElementById('status').className = 'recording';
                
            } catch (error) {
                alert('Error accessing microphone: ' + error.message);
            }
        }
        
        function stopRecording() {
            if (mediaRecorder) {
                mediaRecorder.stop();
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('status').innerHTML = 'Processing...';
                document.getElementById('status').className = 'processing';
            }
        }
        
        async function processAudio() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            try {
                const response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    addToConversation('You', 'Audio recorded');
                    addToConversation('Assistant', result.response_text);
                    document.getElementById('status').innerHTML = 'Ready to listen...';
                    document.getElementById('status').className = '';
                } else {
                    document.getElementById('status').innerHTML = 'Error: ' + result.error;
                    document.getElementById('status').className = 'error';
                }
                
            } catch (error) {
                document.getElementById('status').innerHTML = 'Error: ' + error.message;
                document.getElementById('status').className = 'error';
            }
            
            audioChunks = [];
        }
        
        function addToConversation(speaker, message) {
            const conversation = document.getElementById('conversation');
            const div = document.createElement('div');
            div.innerHTML = `<strong>${speaker}:</strong> ${message}`;
            div.style.margin = '10px 0';
            div.style.padding = '10px';
            div.style.backgroundColor = speaker === 'You' ? '#e3f2fd' : '#f3e5f5';
            div.style.borderRadius = '5px';
            conversation.appendChild(div);
        }
        
        function clearHistory() {
            document.getElementById('conversation').innerHTML = '';
            voice_agent.conversation_manager.clear_conversation();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/process_audio', methods=['POST'])
def process_audio_flask():
    """
    Flask endpoint to process audio files.
    This is where the voice agent integrates with the web backend.
    """
    if not voice_agent:
        return jsonify({'success': False, 'error': 'Voice agent not initialized'}), 500
    
    try:
        # Get uploaded audio file
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No audio file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Process the audio using our voice agent
            result = process_audio_for_web(temp_path, voice_agent)
            return jsonify(result)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file: {e}")
                
    except Exception as e:
        logger.error(f"Flask audio processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/conversation_history')
def get_conversation_history():
    """Get conversation history."""
    if not voice_agent:
        return jsonify({'error': 'Voice agent not initialized'}), 500
    
    history = voice_agent.conversation_manager.get_conversation_history()
    return jsonify({'history': history})

@app.route('/clear_history', methods=['POST'])
def clear_conversation_history():
    """Clear conversation history."""
    if not voice_agent:
        return jsonify({'error': 'Voice agent not initialized'}), 500
    
    voice_agent.conversation_manager.clear_conversation()
    return jsonify({'success': True})


# =============================================================================
# FASTAPI INTEGRATION EXAMPLE
# =============================================================================

fastapi_app = FastAPI(title="Voice Conversation API", version="1.0.0")

@fastapi_app.post("/process_audio")
async def process_audio_fastapi(audio: UploadFile = File(...)):
    """
    FastAPI endpoint to process audio files.
    This is where the voice agent integrates with the web backend.
    """
    if not voice_agent:
        raise HTTPException(status_code=500, detail="Voice agent not initialized")
    
    try:
        # Validate file type
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Process the audio using our voice agent
            result = process_audio_for_web(temp_path, voice_agent)
            return JSONResponse(content=result)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FastAPI audio processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/conversation_history")
async def get_conversation_history_fastapi():
    """Get conversation history."""
    if not voice_agent:
        raise HTTPException(status_code=500, detail="Voice agent not initialized")
    
    history = voice_agent.conversation_manager.get_conversation_history()
    return JSONResponse(content={'history': history})

@fastapi_app.post("/clear_history")
async def clear_conversation_history_fastapi():
    """Clear conversation history."""
    if not voice_agent:
        raise HTTPException(status_code=500, detail="Voice agent not initialized")
    
    voice_agent.conversation_manager.clear_conversation()
    return JSONResponse(content={'success': True})

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        'status': 'healthy',
        'voice_agent_initialized': voice_agent is not None
    })


# =============================================================================
# RUNNING THE SERVERS
# =============================================================================

def run_flask_app():
    """Run Flask development server."""
    print("🌐 Starting Flask server...")
    print("💡 Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)

def run_fastapi_app():
    """Run FastAPI development server."""
    print("🌐 Starting FastAPI server...")
    print("💡 Open http://localhost:8000/docs for API documentation")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "flask":
            run_flask_app()
        elif sys.argv[1] == "fastapi":
            run_fastapi_app()
        else:
            print("Usage: python web_integration_example.py [flask|fastapi]")
    else:
        print("Choose a web framework:")
        print("1. Flask (with web interface)")
        print("2. FastAPI (API only)")
        choice = input("Enter 1 or 2: ")
        
        if choice == "1":
            run_flask_app()
        elif choice == "2":
            run_fastapi_app()
        else:
            print("Invalid choice")
