#!/usr/bin/env python3
"""
ScarletAgent — WOW landing + smooth chat
"""
import os
from datetime import datetime, timedelta
from flask import Flask, request, redirect, url_for, session, jsonify, make_response, render_template, g
from werkzeug.security import generate_password_hash, check_password_hash

from Ui.models import init_db, get_db, User, Message

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SCARLET_SECRET", "scarlet-demo-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
)

# Initialize DB schema
init_db()

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
def norm_username(u): return (u or "").strip().lower()

def current_user():
    uname = session.get("user")
    if not uname:
        return None
    return User.get_by_username(conn(), uname)

def new_chat_session(user):
    sid = f"{user.username}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    session["current_chat"] = sid
    session["login_at"] = datetime.utcnow().isoformat()
    return sid

def get_current_chat():
    return session.get("current_chat")

def add_message(user, role, text):
    Message.create(conn(), user.id, role, text, get_current_chat())

# Make `user` available in all templates (optional convenience)
@app.context_processor
def inject_user():
    return {"nav_user": session.get("user")}

# ------------------ routes ------------------
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
        elif User.get_by_username(conn(), u):
            err = "Username already exists."
        else:
            password_hash = generate_password_hash(p)
            user = User.create(conn(), u, n, password_hash)
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
        user = User.get_by_username(conn(), u)
        if user and check_password_hash(user.password_hash, p):
            session["user"] = u
            new_chat_session(user)
            return redirect(url_for("chat"))
        err = "Invalid username or password."
    return render_template("auth.html", heading="Sign in", cta="Sign in", mode="login", error=err)

# Accept GET too (nice UX)
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

# ---------- preferences API ----------
@app.get("/api/prefs")
def get_prefs():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    return jsonify({
        "avatar_gender": user.avatar_gender or "person",
        "avatar_tone": user.avatar_tone or "default"
    })

@app.post("/api/prefs")
def set_prefs():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    data = request.get_json(force=True)
    gender = (data.get("avatar_gender") or "person").lower()
    tone = (data.get("avatar_tone") or "default").lower()
    if gender not in {"man", "woman", "person"}:
        gender = "person"
    if tone not in {"default", "light", "medium", "dark", "darker", "darkest"}:
        tone = "default"
    user.update_preferences(conn(), gender, tone)
    return jsonify({"ok": True})

# ---------- voice placeholder ----------
@app.post("/api/voice/start")
def voice_start():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    return jsonify({"ok": True, "message": "Voice call placeholder. ElevenLabs integration pending."})

# ---------- messages API ----------
@app.get("/api/messages")
def get_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error":"unauthorized"}), 401)

    before = request.args.get("before")
    msgs = Message.get_messages(
        conn(),
        user.id,
        chat_session=get_current_chat(),
        before=before,
        limit=20
    )
    msgs.reverse()
    oldest = msgs[0].timestamp.isoformat() if msgs else None

    return jsonify({
        "messages": [
            {"role": m.role, "text": m.text, "timestamp": m.timestamp.isoformat()}
            for m in msgs
        ],
        "oldest": oldest,
        "login_at": session.get("login_at")
    })

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

# ---------- cache flush (client → server) ----------
@app.post("/api/flush_messages")
def flush_messages():
    user = current_user()
    if not user:
        return make_response(jsonify({"error": "unauthorized"}), 401)
    data = request.get_json(force=True)
    messages = data.get("messages", [])

    flushed_count = 0
    for msg in messages:
        role = msg.get("role")
        text = msg.get("text")
        if role and text:
            Message.create(conn(), user.id, role, text, get_current_chat())
            flushed_count += 1

    return jsonify({"ok": True, "flushed": flushed_count})

# ---------- errors ----------
@app.errorhandler(403)
def e403(_): return render_template("base.html", title="403 Forbidden"), 403

@app.errorhandler(404)
def e404(_): return render_template("base.html", title="404 Not Found"), 404

if __name__ == "__main__":
    os.makedirs("static/images", exist_ok=True)
    print("\nScarletAgent → http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)