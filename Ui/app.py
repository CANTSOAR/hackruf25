#!/usr/bin/env python3
"""
ScarletAgent — WOW landing + smooth chat
• Home splash intro (scarlet R zoom + flash), transparent hero, floating Rs
• Auth with hashed passwords
• Chat with mascot header, call placeholder, emoji preferences saved per user
• Hidden previous chats until “pull twice” to unlock (then merged)
• Hour-grouped timestamps + first message after login stamped
• Starts at /home
"""
from flask import Flask, request, redirect, url_for, session, jsonify, make_response, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

from models import SessionLocal, init_db, User, Message

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.environ.get("SCARLET_SECRET", "scarlet-demo-secret"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SAMESITE="Lax",
)

init_db()
db = SessionLocal()

# ------------------ helpers ------------------
def norm_username(u): return (u or "").strip().lower()
def current_user():
    uname = session.get("user")
    return db.query(User).filter_by(username=uname).first() if uname else None

def new_chat_session(user):
    sid = f"{user.username}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    session["current_chat"] = sid
    session["login_at"] = datetime.utcnow().isoformat()  # used for first timestamp display
    return sid

def get_current_chat(): return session.get("current_chat")
def add_message(user, role, text):
    msg = Message(user=user, role=role, text=text, chat_session=get_current_chat())
    db.add(msg); db.commit()

# ------------------ routes ------------------
@app.get("/")
def root():
    # Start on home, always
    return redirect(url_for("home"))

@app.get("/home")
def home():
    os.makedirs("static/images", exist_ok=True)
    return render_template("home.html", title="Home")

@app.route("/signup", methods=["GET","POST"])
def signup():
    err=None
    if request.method=="POST":
        u=norm_username(request.form.get("username"))
        p=(request.form.get("password") or "").strip()
        n=(request.form.get("name") or "").strip() or u
        if not u or not p:
            err="Username and password required."
        elif db.query(User).filter_by(username=u).first():
            err="Username already exists."
        else:
            user=User(username=u,name=n,password_hash=generate_password_hash(p))
            db.add(user); db.commit()
            session["user"]=u; new_chat_session(user)
            add_message(user,"bot",f"Hey {n}! Welcome to ScarletAgent.")
            return redirect(url_for("chat"))
    return render_template("auth.html", heading="Sign up", cta="Sign up", mode="signup", error=err)

@app.route("/login", methods=["GET","POST"])
def login():
    err=None
    if request.method=="POST":
        u=norm_username(request.form.get("username"))
        p=(request.form.get("password") or "").strip()
        user=db.query(User).filter_by(username=u).first()
        if user and check_password_hash(user.password_hash,p):
            session["user"]=u; new_chat_session(user)
            return redirect(url_for("chat"))
        err="Invalid username or password."
    return render_template("auth.html", heading="Sign in", cta="Sign in", mode="login", error=err)

@app.post("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.post("/new_chat")
def new_chat():
    user=current_user()
    if not user: return redirect(url_for("login"))
    new_chat_session(user)
    return redirect(url_for("chat"))

@app.get("/chat")
def chat():
    if not current_user(): return redirect(url_for("login"))
    return render_template("chat.html", title="Messages")

# ---------- preferences API ----------
@app.get("/api/prefs")
def get_prefs():
    user=current_user()
    if not user: return make_response(jsonify({"error":"unauthorized"}),401)
    return jsonify({"avatar_gender": user.avatar_gender or "person",
                    "avatar_tone":   user.avatar_tone   or "default"})

@app.post("/api/prefs")
def set_prefs():
    user=current_user()
    if not user: return make_response(jsonify({"error":"unauthorized"}),401)
    data=request.get_json(force=True)
    gender=(data.get("avatar_gender") or "person").lower()
    tone=(data.get("avatar_tone") or "default").lower()
    if gender not in {"man","woman","person"}: gender="person"
    if tone not in {"default","light","medium","dark","darker","darkest"}: tone="default"
    user.avatar_gender=gender; user.avatar_tone=tone
    db.commit()
    return jsonify({"ok":True})

# ---------- voice placeholder (ElevenLabs later) ----------
@app.post("/api/voice/start")
def voice_start():
    user=current_user()
    if not user: return make_response(jsonify({"error":"unauthorized"}),401)
    return jsonify({"ok": True, "message": "Voice call placeholder. ElevenLabs integration pending."})

# ---------- messages API ----------
@app.get("/api/messages")
def get_messages():
    user=current_user()
    if not user: return make_response(jsonify({"error":"unauthorized"}),401)
    before=request.args.get("before")
    q=db.query(Message).filter_by(user_id=user.id).order_by(Message.timestamp.desc())
    if before:
        q=q.filter(Message.timestamp<datetime.fromisoformat(before))
    msgs=q.limit(20).all()
    msgs.reverse()
    oldest=msgs[0].timestamp.isoformat() if msgs else None
    return jsonify({
        "messages":[{"role":m.role,"text":m.text,"timestamp":m.timestamp.isoformat()} for m in msgs],
        "oldest":oldest,
        "login_at": session.get("login_at")
    })

@app.post("/api/message")
def post_message():
    user=current_user()
    if not user: return make_response(jsonify({"error":"unauthorized"}),401)
    data=request.get_json(force=True)
    text=(data.get("text") or "").strip()
    if not text: return make_response(jsonify({"error":"empty"}),400)
    add_message(user,"user",text)
    add_message(user,"bot",f"Message received: '{text}'")
    return jsonify({"ok":True})

# ---------- errors ----------
@app.errorhandler(403)
def e403(_): return render_template("base.html",title="403 Forbidden"),403
@app.errorhandler(404)
def e404(_): return render_template("base.html",title="404 Not Found"),404

if __name__=="__main__":
    os.makedirs("static/images", exist_ok=True)
    print("\nScarletAgent → http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)