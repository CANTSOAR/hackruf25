#!/usr/bin/env python3
"""
ScarletAgent — Full Flask App with Snowflake Integration + Session-based User Tracking
"""
import os
import io
import threading
from datetime import datetime, timedelta
from pathlib import Path
from flask import (
    Flask, request, redirect, url_for, session, jsonify,
    make_response, render_template, g, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)  # finds your .env no matter where you launch from
from elevenlabs.client import ElevenLabs


# Snowflake imports
from snowflake.db_helper import (
    init_db, get_db,
    add_user, get_user_by_username, get_user_by_id,
    upsert_message_history, get_message_history,
    upsert_canvas_payload, get_canvas_payload,
    upsert_gcal_token, get_gcal_token, delete_gcal_token,
    upsert_gdrive_token, get_gdrive_token, delete_gdrive_token
)

# Agent placeholder (for later integration)
from agents.intake import INTAKE

# -------------------- Flask App Config --------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SCARLET_SECRET", "scarlet-demo-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
)

# Initialize Snowflake DB once on startup
try:
    init_db()
except Exception as e:
    print(f"⚠️  Snowflake init error: {e}")

# Initialize ElevenLabs (voice)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
if elevenlabs_client:
    print("🎤 ElevenLabs voice client initialized.")

# -------------------- Global State --------------------
inactivity_timer = None
NOTIFICATIONS = []

def handle_inactivity():
    """Ends chat session after 5 min inactivity."""
    print("\n[!] User inactive for 5 minutes — ending session.")
    try:
        INTAKE.run("The user has gone inactive.")
    except Exception as e:
        print(f"Inactivity handler error: {e}")

# -------------------- DB Connection per Request --------------------
def conn():
    if "db" not in g:
        g.db = get_db()
    return g.db

@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db:
        db.close()

# -------------------- User Helpers --------------------
def norm_username(u):
    return (u or "").strip().lower()

def current_user():
    """Return user dict if logged in."""
    uname = session.get("user")
    if not uname:
        return None
    return get_user_by_username(conn(), uname)

def new_chat_session(user):
    session["login_at"] = datetime.utcnow().isoformat()
    session["user_id"] = user["ID"]
    history = get_message_history(conn(), user["ID"]) or {"messages": []}
    return history

def add_message(user, role, text):
    history = get_message_history(conn(), user["ID"]) or {"messages": []}
    history["messages"].append({
        "role": role,
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })
    upsert_message_history(conn(), user["ID"], history)

@app.context_processor
def inject_user():
    """Injects user info globally into templates."""
    return {"nav_user": session.get("user")}

# -------------------- ROUTES --------------------

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
                session["user_id"] = user["ID"]
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
            session["user_id"] = user["ID"]
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

    uid = user["ID"]
    canvas_connected = bool(get_canvas_payload(conn(), uid))
    gcal_connected   = bool(get_gcal_token(conn(), uid))
    gdrive_connected = bool(get_gdrive_token(conn(), uid))

    return render_template(
        "profile.html",
        title="Profile Settings",
        user=user,
        canvas_connected=canvas_connected,
        gcal_connected=gcal_connected,
        gdrive_connected=gdrive_connected,
    )

@app.get("/about")
def about():
    return render_template("about.html", title="About Us")

@app.get("/debug/snowflake")
def debug_snowflake():
    try:
        db = get_db()
        db.cursor.execute("SELECT CURRENT_ACCOUNT() AS acct, CURRENT_REGION() AS region")
        row = db.cursor.fetchone()
        return jsonify({"ok": True, "account": row["ACCT"], "region": row["REGION"]})
    except Exception as e:
        # Don’t print secrets—just which vars are missing + a message
        import os
        missing = [k for k in ["SNOWFLAKE_USER","SNOWFLAKE_PASSWORD","SNOWFLAKE_ACCOUNT",
                               "SNOWFLAKE_WAREHOUSE","SNOWFLAKE_DATABASE","SNOWFLAKE_SCHEMA",
                               "SNOWFLAKE_ROLE"] if not os.getenv(k)]
        return jsonify({"ok": False, "error": str(e), "missing_env": missing}), 500

# -------------------- API: Messages --------------------
@app.get("/api/messages")
def get_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)

    history = get_message_history(conn(), user["ID"]) or {"messages": []}
    msgs = history.get("messages", [])
    before = request.args.get("before")
    if before:
        before_dt = datetime.fromisoformat(before)
        msgs = [m for m in msgs if datetime.fromisoformat(m["timestamp"]) < before_dt]

    msgs = msgs[-20:]
    oldest = msgs[0]["timestamp"] if msgs else None

    return jsonify({
        "messages": msgs,
        "oldest": oldest,
        "login_at": session.get("login_at")
    })

@app.post("/api/message")
def post_message():
    global inactivity_timer
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)

    if inactivity_timer:
        inactivity_timer.cancel()

    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return make_response(jsonify({"error": "empty"}), 400)

    add_message(user, "user", text)

    try:
        response = INTAKE.run(text)
        add_message(user, "bot", response)
    except Exception as e:
        print("Agent error:", e)
        response = "I'm having trouble processing that."
        add_message(user, "bot", response)

    inactivity_timer = threading.Timer(300.0, handle_inactivity)
    inactivity_timer.start()

    return jsonify({
        "ok": True,
        "message": {"role": "bot", "text": response, "timestamp": datetime.utcnow().isoformat()}
    })

# ---------- Integrations: Google Calendar ----------
@app.post("/api/integrations/gcal/link")
def api_gcal_link():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    # Stub payload; replace with real OAuth token later
    upsert_gcal_token(conn(), user["ID"], {"enabled": True})
    return jsonify({"ok": True})

@app.post("/api/integrations/gcal/unlink")
def api_gcal_unlink():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    delete_gcal_token(conn(), user["ID"])
    return jsonify({"ok": True})


# ---------- Integrations: Google Drive ----------
@app.post("/api/integrations/gdrive/link")
def api_gdrive_link():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    upsert_gdrive_token(conn(), user["ID"], {"enabled": True})
    return jsonify({"ok": True})

@app.post("/api/integrations/gdrive/unlink")
def api_gdrive_unlink():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    delete_gdrive_token(conn(), user["ID"])
    return jsonify({"ok": True})


# ---------- Integrations: Canvas (simple on/off payload) ----------
@app.post("/api/integrations/canvas/save")
def api_canvas_save():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled"))
    upsert_canvas_payload(conn(), user["ID"], {"enabled": enabled})
    return jsonify({"ok": True, "enabled": enabled})

# -------------------- Errors --------------------
@app.errorhandler(403)
def e403(_): 
    return render_template("base.html", title="403 Forbidden"), 403

@app.errorhandler(404)
def e404(_): 
    return render_template("base.html", title="404 Not Found"), 404

# -------------------- Run --------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 ScarletAgent running → http://localhost:5000")
    print("="*60)
    app.run(host="127.0.0.1", port=5000, debug=True)