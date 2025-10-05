from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = "chat.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)      # stored lowercase
    name = Column(String(100))
    password_hash = Column(String(255))
    # saved preferences
    avatar_gender = Column(String(10), default="person")   # 'man' | 'woman' | 'person'
    avatar_tone   = Column(String(10), default="default")  # 'default','light','medium','dark','darker','darkest'
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_session = Column(String(40), index=True)   # logical thread
    role = Column(String(10))                       # 'user' | 'bot'
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="messages")

def init_db():
    # Create tables if not exist
    Base.metadata.create_all(engine)
    # Quick SQLite “migration” to add new columns if missing
    try:
        with engine.begin() as conn:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
            if 'avatar_gender' not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_gender VARCHAR(10) DEFAULT 'person'")
            if 'avatar_tone' not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_tone VARCHAR(10) DEFAULT 'default'")
    except Exception as e:
        print("Schema ensure warning:", e)