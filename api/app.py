import os
import io
import threading
from flask import Flask, request, jsonify, send_file, render_template_string
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# --- AGENT IMPORTS ---
from agents.intake import INTAKE

# --- 1. SETUP ---
load_dotenv()
app = Flask(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
print("ElevenLabs client initialized successfully.")

# --- INACTIVITY TIMER & NOTIFICATIONS SETUP ---
inactivity_timer = None
NOTIFICATIONS = []

def handle_inactivity():
    """
    This function is called by the timer when the user has been inactive.
    It triggers the Intake agent to end the conversation.
    """
    print("\n--- User inactive for 5 minutes. Automatically ending conversation. ---")
    INTAKE.run("the user is inactive")

# --- 2. HTML & JAVASCRIPT FRONTEND ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asynchronous Agent Interface</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding-top: 60px; background-color: #f7f7f7; color: #333; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #111; }
        textarea { width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; border: none; border-radius: 4px; color: white; background-color: #007bff; font-size: 16px; cursor: pointer; margin-bottom: 10px; }
        button:hover { background-color: #0056b3; }
        #recordButton { background-color: #dc3545; }
        #recordButton.recording { background-color: #28a745; }
        #responseArea { margin-top: 20px; padding: 10px; background-color: #e9ecef; border-radius: 4px; }
        #notification-banner {
            position: fixed; top: -100px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 500px;
            background-color: #28a745; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            text-align: center; font-size: 16px; z-index: 1000; transition: top 0.5s ease-in-out;
        }
    </style>
</head>
<body>
    <div id="notification-banner"></div>
    <div class="container">
        <h1>Interact with Agent</h1>
        <textarea id="textInput" rows="3" placeholder="Type your message here..."></textarea>
        <button onclick="sendText()">Send Text</button>
        <button id="recordButton" onclick="toggleRecording()">Start Recording</button>
        <div id="responseArea">
            <strong>Agent Response:</strong>
            <p id="responseText"></p>
            <audio id="responseAudio" controls autoplay></audio>
        </div>
    </div>
    <script>
        window.onload = function() { checkForNotifications(); };
        async function checkForNotifications() {
            try {
                const response = await fetch('/api/get-notifications');
                const data = await response.json();
                if (data.notifications && data.notifications.length > 0) {
                    showNotification(data.notifications[0]);
                }
            } catch (error) { console.error('Error fetching notifications:', error); }
        }
        function showNotification(message) {
            const banner = document.getElementById('notification-banner');
            banner.innerText = message;
            banner.style.top = '20px';
            setTimeout(() => { banner.style.top = '-100px'; }, 5000);
        }
        
        let mediaRecorder, audioChunks = [];

        async function sendText() {
            const text = document.getElementById('textInput').value;
            if (!text) return;
            document.getElementById('responseText').innerText = 'Processing...';
            const response = await fetch('/api/interact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            const data = await response.json();
            document.getElementById('responseText').innerText = data.response;
            document.getElementById('responseAudio').src = '';
        }

        function toggleRecording() {
            const recordButton = document.getElementById('recordButton');
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                recordButton.innerText = 'Start Recording';
                recordButton.classList.remove('recording');
            } else {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.start();
                        audioChunks = [];
                        recordButton.innerText = 'Stop Recording';
                        recordButton.classList.add('recording');
                        mediaRecorder.ondataavailable = event => {
                            audioChunks.push(event.data);
                        };
                        mediaRecorder.onstop = sendAudio;
                    }).catch(err => console.error("Error accessing microphone:", err));
            }
        }

        async function sendAudio() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            document.getElementById('responseText').innerText = 'Processing audio...';
            document.getElementById('responseAudio').src = '';
            const response = await fetch('/api/interact', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const error = await response.json();
                document.getElementById('responseText').innerText = `Error: ${error.error}`;
                return;
            }
            const audioResponseBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioResponseBlob);
            const responseAudio = document.getElementById('responseAudio');
            responseAudio.src = audioUrl;
            responseAudio.play().catch(e => console.error("Autoplay was prevented:", e));
            document.getElementById('responseText').innerText = 'Audio response received. Playing...';
        }
    </script>
</body>
</html>
"""

# --- 3. FLASK API ENDPOINTS ---
@app.route('/')
def home():
    """Serves the frontend HTML page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/interact', methods=['POST'])
def interact():
    """Handles the main interaction with the Intake agent and manages the inactivity timer."""
    global inactivity_timer

    if inactivity_timer:
        inactivity_timer.cancel()
    
    content_type = request.headers.get('Content-Type')
    user_text = ""

    try:
        if 'application/json' in content_type:
            user_text = request.json.get('text')
        elif 'multipart/form-data' in content_type:
            audio_file = request.files['audio']
            transcribed_response = client.speech_to_text.convert(file=audio_file.read(), model_id="scribe_v1")
            user_text = transcribed_response.text
        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

        if not user_text:
            return jsonify({"error": "No input provided"}), 400

        agent_response_text = INTAKE.run(user_text)

        inactivity_timer = threading.Timer(300.0, handle_inactivity)
        inactivity_timer.start()
        print("\n--- Inactivity timer reset for 5 minutes. ---")

        if 'application/json' in content_type:
            return jsonify({"response": agent_response_text})
        else:
            audio_generator = client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=agent_response_text
            )
            full_audio_bytes = b"".join(audio_generator)
            return send_file(io.BytesIO(full_audio_bytes), mimetype='audio/mpeg')

    except Exception as e:
        print(f"An error occurred during interaction: {e}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

@app.route('/api/notify', methods=['POST'])
def notify():
    """Receives the final status from the orchestrator and stores it."""
    global NOTIFICATIONS
    message = request.json.get("message")
    if message:
        print(f"\n--- Storing Notification: '{message}' ---\n")
        NOTIFICATIONS.append(message)
    return jsonify({"status": "notification stored"}), 200

@app.route('/api/get-notifications', methods=['GET'])
def get_notifications():
    """Serves pending notifications to the frontend and then clears them."""
    global NOTIFICATIONS
    notifications_to_send = list(NOTIFICATIONS)
    NOTIFICATIONS.clear()
    return jsonify({"notifications": notifications_to_send})

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)

