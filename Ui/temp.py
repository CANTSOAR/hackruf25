#!/usr/bin/env python3
"""
Merged app.py with ElevenLabs + ScarletAgent frontend
Updated to use function-based Snowflake DB helpers
"""
import os
import io
import threading
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

from flask import (
    Flask, request, redirect, url_for, session, jsonify,
    make_response, render_template, g, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

# --- Snowflake DB helpers ---
from snowflake.db_helper import (
    init_db, get_db,
    add_user, get_user_by_username, get_user_by_id,
    upsert_message_history, get_message_history,
    upsert_canvas_payload, upsert_gcal_token, upsert_gdrive_token
)

# --- ElevenLabs client and Intake agent ---
from elevenlabs.client import ElevenLabs
from agents.intake import INTAKE

# --- Load environment ---
load_dotenv()

# --- Flask app setup ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.getenv("SCARLET_SECRET", "scarlet-demo-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
)

# --- Initialize DB schema once at startup ---
db_init = init_db()

# ------------------ per-request DB connection ------------------
def conn():
    if "db" not in g:
        g.db = get_db()
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db:
        db.close()

# ------------------ ElevenLabs setup ------------------
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
if client:
    print("✓ ElevenLabs client initialized")
else:
    print("⚠ ElevenLabs disabled (no API key)")

# ------------------ inactivity timer & notifications ------------------
inactivity_timer = None
NOTIFICATIONS = []

def handle_inactivity():
    print("\n--- User inactive for 5 minutes. Ending conversation. ---")
    try:
        INTAKE.run("the user is inactive")
    except Exception as e:
        print("Error on inactivity:", e)

# ------------------ helpers ------------------
def norm_username(u): return (u or "").strip().lower()

def current_user():
    uname = session.get("user")
    if not uname:
        return None
    return get_user_by_username(conn(), uname)

def new_chat_session(user):
    sid = f"{user['USERNAME']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    session["current_chat"] = sid
    session["login_at"] = datetime.utcnow().isoformat()
    return sid

def get_current_chat():
    return session.get("current_chat")

def add_message(user, role, text):
    """Append a message to scarlet_messages JSON history."""
    db = conn()
    history = get_message_history(db, user["ID"]) or []
    history.append({
        "role": role,
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
        "chat_session": get_current_chat()
    })
    upsert_message_history(db, user["ID"], history)

# Inject user into templates
@app.context_processor
def inject_user():
    return {"nav_user": session.get("user")}

# ------------------ Frontend routes ------------------
@app.get("/")
def root():
    return redirect(url_for("home"))

@app.get("/home")
def home():
    os.makedirs("static/images", exist_ok=True)
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
        if user and check_password_hash(user["PASSWORD_HASH"], p):
            session["user"] = u
            new_chat_session(user)
            return redirect(url_for("chat"))
        err = "Invalid username or password."
    return render_template("auth.html", heading="Sign in", cta="Sign in", mode="login", error=err)

@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.post("/new_chat")
def new_chat():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    new_chat_session(user)
    return redirect(url_for("chat"))

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

# ------------------ Preferences API ------------------
@app.get("/api/prefs")
def get_prefs():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    return jsonify({"avatar_gender": "person", "avatar_tone": "default"})

@app.post("/api/prefs")
def set_prefs():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    return jsonify({"ok": True})

# ------------------ Canvas / Tokens storage ------------------
@app.post("/api/store_main")
def store_main():
    data = request.get_json(force=True)
    profile_id = data.get("profile_id")
    primary_email = data.get("primary_email")
    canvas_json = data.get("canvas_json")
    gcal_token_json = data.get("gcal_token_json")
    gdrive_token_json = data.get("gdrive_token_json")

    db = conn()
    ok1 = upsert_canvas_payload(db, profile_id, canvas_json)
    ok2 = upsert_gcal_token(db, profile_id, gcal_token_json)
    ok3 = upsert_gdrive_token(db, profile_id, gdrive_token_json)

    if ok1 and ok2 and ok3:
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False}), 500

# ------------------ ElevenLabs / AI endpoints ------------------
@app.post("/api/interact")
def interact():
    global inactivity_timer
    if inactivity_timer:
        inactivity_timer.cancel()

    content_type = request.headers.get("Content-Type", "")
    user_text = ""

    try:
        if "application/json" in content_type:
            user_text = request.json.get("text")
        elif "multipart/form-data" in content_type:
            audio_file = request.files["audio"]
            if not client:
                return jsonify({"error": "TTS/STT unavailable"}), 503
            transcribed = client.speech_to_text.convert(file=audio_file.read(), model_id="scribe_v1")
            user_text = getattr(transcribed, "text", None) or transcribed.get("text")
        else:
            return jsonify({"error": "Unsupported Content-Type"}), 415

        if not user_text:
            return jsonify({"error": "No input provided"}), 400

        agent_response = INTAKE.run(user_text)

        inactivity_timer = threading.Timer(300.0, handle_inactivity)
        inactivity_timer.start()

        if "application/json" in content_type:
            user = current_user()
            if user:
                add_message(user, "user", user_text)
                add_message(user, "bot", agent_response)
            return jsonify({"response": agent_response})
        else:
            audio_gen = client.text_to_speech.convert(voice_id=ELEVENLABS_VOICE_ID, text=agent_response)
            full_audio = b"".join(audio_gen) if hasattr(audio_gen, "__iter__") else audio_gen
            return send_file(io.BytesIO(full_audio), mimetype="audio/mpeg")

    except Exception as e:
        print("interact error:", e)
        return jsonify({"error": str(e)}), 500

@app.post("/api/notify")
def notify():
    global NOTIFICATIONS
    message = request.json.get("message")
    if message:
        NOTIFICATIONS.append(message)
    return jsonify({"status": "notification stored"})

@app.get("/api/get-notifications")
def get_notifications():
    global NOTIFICATIONS
    out = list(NOTIFICATIONS)
    NOTIFICATIONS.clear()
    return jsonify({"notifications": out})

# ------------------ Messages API ------------------
@app.get("/api/messages")
def get_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)

    history = get_message_history(conn(), user["ID"]) or []
    return jsonify({"messages": history, "login_at": session.get("login_at")})

@app.post("/api/message")
def post_message():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return make_response(jsonify({"error": "empty"}), 400)
    add_message(user, "user", text)
    add_message(user, "bot", f"Message received: '{text}'")
    return jsonify({"ok": True})

@app.post("/api/flush_messages")
def flush_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    msgs = request.get_json(force=True).get("messages", [])
    for msg in msgs:
        add_message(user, msg.get("role"), msg.get("text"))
    return jsonify({"ok": True, "flushed": len(msgs)})

# ------------------ Errors ------------------
@app.errorhandler(403)
def e403(_): return render_template("base.html", title="403 Forbidden"), 403

@app.errorhandler(404)
def e404(_): return render_template("base.html", title="404 Not Found"), 404

# ------------------ Run ------------------
if __name__ == "__main__":
    os.makedirs("static/images", exist_ok=True)
    print("\nScarletAgent merged → http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
