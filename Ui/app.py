#!/usr/bin/env python3
"""
ScarletAgent — Combined UI/UX + AI Voice Integration
Merges beautiful chat interface with ElevenLabs voice and Gemini agent
"""
import os
import io
import threading
from datetime import datetime, timedelta
from flask import Flask, request, redirect, url_for, session, jsonify, make_response, render_template, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Database imports
from snowflake.db_helper import (
    init_db, get_db,
    add_user, get_user_by_username, get_user_by_id,
    upsert_message_history, get_message_history
)

# Agent imports
from agents.intake import INTAKE

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SCARLET_SECRET", "scarlet-demo-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
)

# Initialize DB schema
init_db()

# Initialize ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
if elevenlabs_client:
    print("✓ ElevenLabs client initialized")

# Inactivity timer
inactivity_timer = None
NOTIFICATIONS = []

def handle_inactivity():
    """Called when user is inactive for 5 minutes"""
    print("\n--- User inactive for 5 minutes. Ending conversation. ---")
    try:
        INTAKE.run("the user is inactive")
    except Exception as e:
        print(f"Error in inactivity handler: {e}")

# ------------------ per-request DB connection ------------------
def conn():
    if "db" not in g:
        g.db = get_db()
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ------------------ helpers ------------------
def norm_username(u): 
    return (u or "").strip().lower()

def current_user():
    uname = session.get("user")
    if not uname:
        return None
    user_dict = get_user_by_username(conn(), uname)
    return user_dict

def new_chat_session(user):
    """Initialize new chat session"""
    session["login_at"] = datetime.utcnow().isoformat()
    # Load existing message history
    history = get_message_history(conn(), user['ID']) or {"messages": []}
    return history

def get_message_history_for_user():
    """Get message history for current user"""
    user = current_user()
    if not user:
        return {"messages": []}
    history = get_message_history(conn(), user['ID'])
    return history or {"messages": []}

def add_message(user, role, text):
    """Add a message to user's history"""
    history = get_message_history(conn(), user['ID']) or {"messages": []}
    history["messages"].append({
        "role": role,
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })
    upsert_message_history(conn(), user['ID'], history)

@app.context_processor
def inject_user():
    return {"nav_user": session.get("user")}

# ------------------ routes ------------------
@app.get("/")
def root():
    return redirect(url_for("home"))

@app.get("/home")
def home():
    return render_template("home.html", title="Home")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    err = None
    if request.method == "POST":
        u = norm_username(request.form.get("username"))
        p = (request.form.get("password") or "").strip()
        n = (request.form.get("name") or "").strip() or u
        if not u or not p:
            err = "Username and password required."
        elif get_user_by_username(conn(), u):
            err = "Username already exists."
        else:
            password_hash = generate_password_hash(p)
            user = add_user(conn(), u, n, password_hash)
            if user:
                session["user"] = u
                new_chat_session(user)
                add_message(user, "bot", f"Hey {n}! Welcome to ScarletAgent.")
                return redirect(url_for("chat"))
            else:
                err = "Error creating user."
    return render_template("auth.html", heading="Sign up", cta="Sign up", mode="signup", error=err)

@app.route("/login", methods=["GET", "POST"])
def login():
    err = None
    if request.method == "POST":
        u = norm_username(request.form.get("username"))
        p = (request.form.get("password") or "").strip()
        user = get_user_by_username(conn(), u)
        if user and check_password_hash(user['PASSWORD_HASH'], p):
            session["user"] = u
            new_chat_session(user)
            return redirect(url_for("chat"))
        err = "Invalid username or password."
    return render_template("auth.html", heading="Sign in", cta="Sign in", mode="login", error=err)

@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.get("/chat")
def chat():
    if not current_user():
        return redirect(url_for("login"))
    return render_template("chat.html", title="Messages")

@app.get("/profile")
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("profile.html", title="Profile Settings", user=user)

@app.get("/about")
def about():
    return render_template("about.html", title="About Us")

# ---------- messages API ----------
@app.get("/api/messages")
def get_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error":"unauthorized"}), 401)

    history = get_message_history(conn(), user['ID']) or {"messages": []}
    messages = history.get("messages", [])
    
    # Filter by before timestamp if provided
    before = request.args.get("before")
    if before:
        before_dt = datetime.fromisoformat(before)
        messages = [m for m in messages if datetime.fromisoformat(m["timestamp"]) < before_dt]
    
    # Return last 20 messages
    messages = messages[-20:]
    oldest = messages[0]["timestamp"] if messages else None

    return jsonify({
        "messages": messages,
        "oldest": oldest,
        "login_at": session.get("login_at")
    })

@app.post("/api/message")
def post_message():
    global inactivity_timer
    
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    
    # Cancel existing timer
    if inactivity_timer:
        inactivity_timer.cancel()
    
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    
    if not text:
        return make_response(jsonify({"error": "empty"}), 400)
    
    # Add user message
    add_message(user, "user", text)
    
    # Get AI response
    try:
        agent_response = INTAKE.run(text)
        
        # Check for end message
        if "{[\\THIS IS THE END MESSAGE/]}" in agent_response:
            agent_response = agent_response.replace("{[\\THIS IS THE END MESSAGE/]}", "").strip()
            if not agent_response:
                agent_response = "Consider it done."
        
        add_message(user, "bot", agent_response)
        
    except Exception as e:
        print(f"Agent error: {e}")
        agent_response = "I'm having trouble processing that. Can you try again?"
        add_message(user, "bot", agent_response)
    
    # Reset inactivity timer (5 minutes)
    inactivity_timer = threading.Timer(300.0, handle_inactivity)
    inactivity_timer.start()
    
    return jsonify({"ok": True})

# ---------- voice integration ----------
@app.post("/api/voice/interact")
def voice_interact():
    global inactivity_timer
    
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    
    if not elevenlabs_client:
        return make_response(jsonify({"error": "ElevenLabs not configured"}), 500)
    
    # Cancel existing timer
    if inactivity_timer:
        inactivity_timer.cancel()
    
    try:
        # Get audio from request
        audio_file = request.files.get('audio')
        if not audio_file:
            return make_response(jsonify({"error": "No audio provided"}), 400)
        
        # Transcribe audio
        transcribed_response = elevenlabs_client.speech_to_text.convert(
            file=audio_file.read(), 
            model_id="scribe_v1"
        )
        user_text = transcribed_response.text
        
        if not user_text:
            return make_response(jsonify({"error": "Could not transcribe audio"}), 400)
        
        # Add user message
        add_message(user, "user", user_text)
        
        # Get AI response
        agent_response = INTAKE.run(user_text)
        
        # Check for end message
        if "{[\\THIS IS THE END MESSAGE/]}" in agent_response:
            agent_response = agent_response.replace("{[\\THIS IS THE END MESSAGE/]}", "").strip()
            if not agent_response:
                agent_response = "Consider it done."
        
        add_message(user, "bot", agent_response)
        
        # Convert response to speech
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=agent_response
        )
        full_audio_bytes = b"".join(audio_generator)
        
        # Reset inactivity timer
        inactivity_timer = threading.Timer(300.0, handle_inactivity)
        inactivity_timer.start()
        
        return send_file(io.BytesIO(full_audio_bytes), mimetype='audio/mpeg')
        
    except Exception as e:
        print(f"Voice interaction error: {e}")
        return make_response(jsonify({"error": str(e)}), 500)

@app.post("/api/voice/start")
def voice_start():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    
    if not elevenlabs_client:
        return jsonify({
            "ok": False, 
            "message": "Voice features require ElevenLabs API key. Please configure in .env file."
        })
    
    return jsonify({
        "ok": True, 
        "message": "Voice ready! Use the microphone button to start recording."
    })

# ---------- notifications API ----------
@app.post("/api/notify")
def notify():
    """Receives notifications from orchestrator"""
    global NOTIFICATIONS
    message = request.json.get("message")
    if message:
        print(f"\n--- Storing Notification: '{message}' ---\n")
        NOTIFICATIONS.append(message)
    return jsonify({"status": "notification stored"}), 200

@app.get("/api/get-notifications")
def get_notifications():
    """Returns pending notifications"""
    global NOTIFICATIONS
    notifications_to_send = list(NOTIFICATIONS)
    NOTIFICATIONS.clear()
    return jsonify({"notifications": notifications_to_send})

# ---------- errors ----------
@app.errorhandler(403)
def e403(_): 
    return render_template("base.html", title="403 Forbidden"), 403

@app.errorhandler(404)
def e404(_): 
    return render_template("base.html", title="404 Not Found"), 404

if __name__ == "__main__":
    os.makedirs("static/images", exist_ok=True)
    print("\n" + "="*50)
    print("🎓 ScarletAgent → http://localhost:5000")
    print("="*50)
    if not ELEVENLABS_API_KEY:
        print("⚠️  ElevenLabs API key not found - voice features disabled")
    print()
    app.run(host="127.0.0.1", port=5000, debug=True)