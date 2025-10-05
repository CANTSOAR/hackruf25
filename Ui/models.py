"""
Snowflake Database Models for ScarletAgent (fixed)
"""
import snowflake.connector
from snowflake.connector import Error
import os
from datetime import datetime
import json


class SnowflakeDB:
    """Snowflake database connection manager"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                user=os.getenv('SNOWFLAKE_USER', 'LAWRENCIUMX'),
                password=os.getenv('SNOWFLAKE_PASSWORD', 'EdUZZWw76XcvDJ9'),
                account=os.getenv('SNOWFLAKE_ACCOUNT', 'TMLYSUD-QO29207'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database=os.getenv('SNOWFLAKE_DATABASE', 'SNOWFLAKE_LEARNING_DB'),
                schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
                role=os.getenv('SNOWFLAKE_ROLE', 'SYSADMIN')
            )
            self.cursor = self.connection.cursor()
            return True
        except Error as e:
            print(f"Snowflake connection error: {e}")
            return False
    
    def init_tables(self):
        """Create tables if they don't exist"""
        try:
            # Users table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_users (
                    id INTEGER AUTOINCREMENT,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(200),
                    password_hash VARCHAR(255) NOT NULL,
                    avatar_gender VARCHAR(20) DEFAULT 'person',
                    avatar_tone VARCHAR(20) DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    PRIMARY KEY (id)
                )
            """)
            
            # Messages table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_messages (
                    id INTEGER AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    text STRING NOT NULL,
                    chat_session VARCHAR(200),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES scarlet_users(id)
                )
            """)
            #Main
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS main (
                    profile_id BIGINT PRIMARY KEY,
                    primary_email VARCHAR(255),
                    canvas_json VARIANT,
                    gcal_token_json VARIANT,
                    gdrive_token_json VARIANT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.connection.commit()
            print("✓ Snowflake tables initialized")
            
        except Error as e:
            print(f"Error initializing tables: {e}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


class User:
    """User model for Snowflake"""
    
    def __init__(self, id=None, username=None, name=None, password_hash=None, 
                 avatar_gender='person', avatar_tone='default'):
        self.id = id
        self.username = username
        self.name = name
        self.password_hash = password_hash
        self.avatar_gender = avatar_gender
        self.avatar_tone = avatar_tone
    
    @staticmethod
    def create(db, username, name, password_hash):
        """Create a new user"""
        try:
            db.cursor.execute("""
                INSERT INTO scarlet_users (username, name, password_hash)
                VALUES (%s, %s, %s)
            """, (username, name, password_hash))
            db.connection.commit()
            return User.get_by_username(db, username)
        except Exception as e:
            db.connection.rollback()
            print(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def get_by_username(db, username):
        """Get user by username"""
        try:
            db.cursor.execute("""
                SELECT id, username, name, password_hash, avatar_gender, avatar_tone
                FROM scarlet_users WHERE username = %s
            """, (username,))
            row = db.cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    name=row[2],
                    password_hash=row[3],
                    avatar_gender=row[4],
                    avatar_tone=row[5]
                )
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_preferences(self, db, avatar_gender, avatar_tone):
        """Update user preferences"""
        try:
            db.cursor.execute("""
                UPDATE scarlet_users 
                SET avatar_gender = %s, avatar_tone = %s
                WHERE id = %s
            """, (avatar_gender, avatar_tone, self.id))
            db.connection.commit()
            self.avatar_gender = avatar_gender
            self.avatar_tone = avatar_tone
            return True
        except Exception as e:
            db.connection.rollback()
            print(f"Error updating preferences: {e}")
            return False

    @staticmethod
    def upsert_record(db, profile_id, primary_email, canvas_data, gcal_token_data, gdrive_token_data):
        try:
            db.cursor.execute("""
                MERGE INTO main t
                USING (SELECT %s AS profile_id, %s AS primary_email, 
                              PARSE_JSON(%s) AS canvas_json, 
                              PARSE_JSON(%s) AS gcal_token_json,
                              PARSE_JSON(%s) AS gdrive_token_json) s
                ON t.profile_id = s.profile_id
                WHEN MATCHED THEN UPDATE SET 
                    primary_email = s.primary_email,
                    canvas_json = s.canvas_json,
                    gcal_token_json = s.gcal_token_json
                    gdrive_token_json = s.gdrive_token_json
                WHEN NOT MATCHED THEN INSERT (profile_id, primary_email, canvas_json, gcal_token_json, gdrive_token_json)
                VALUES (s.profile_id, s.primary_email, s.canvas_json, s.gcal_token_json, s.gdrive_token_json)
            """, (profile_id, primary_email, json.dumps(canvas_data), json.dumps(gcal_token_data), json.dumps(gdrive_token_data)))
            db.connection.commit()
            return True
        except Exception as e:
            db.connection.rollback()
            print(f"Error upserting record: {e}")
            return False


class Message:
    """Message model for Snowflake"""
    
    def __init__(self, id=None, user_id=None, role=None, text=None, 
                 chat_session=None, timestamp=None):
        self.id = id
        self.user_id = user_id
        self.role = role
        self.text = text
        self.chat_session = chat_session
        self.timestamp = timestamp or datetime.utcnow()
    
    @staticmethod
    def create(db, user_id, role, text, chat_session=None):
        """Create a new message"""
        try:
            db.cursor.execute("""
                INSERT INTO scarlet_messages (user_id, role, text, chat_session)
                VALUES (%s, %s, %s, %s)
            """, (user_id, role, text, chat_session))
            db.connection.commit()
            return True
        except Exception as e:
            db.connection.rollback()
            raise  # <-- make sure you see it in Flask logs

    
    @staticmethod
    def get_messages(db, user_id, chat_session=None, before=None, limit=20):
        """Get messages for a user"""
        try:
            query = """
                SELECT id, user_id, role, text, chat_session, timestamp
                FROM scarlet_messages
                WHERE user_id = %s
            """
            params = [user_id]

            if chat_session:
                query += " AND (chat_session = %s OR chat_session IS NULL)"
                params.append(chat_session)

            if before:
                query += " AND timestamp < %s"
                params.append(before)

            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)

            db.cursor.execute(query, tuple(params))

            messages = []
            for row in db.cursor.fetchall():
                messages.append(Message(
                    id=row[0],
                    user_id=row[1],
                    role=row[2],
                    text=row[3],
                    chat_session=row[4],
                    timestamp=row[5]
                ))

            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []



# Initialize Snowflake database
def init_db():
    db = SnowflakeDB()
    if db.connect():
        db.init_tables()
        return db
    return None

# Get or create Snowflake database connection
def get_db():
    db = SnowflakeDB()
    db.connect()
    return db