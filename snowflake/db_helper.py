"""
Snowflake Database Models for ScarletAgent (fixed)
"""
import snowflake.connector
from snowflake.connector import Error
from snowflake.connector.cursor import DictCursor
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
            # Use DictCursor to get results as dictionaries
            self.cursor = self.connection.cursor(DictCursor)
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    PRIMARY KEY (id)
                )
            """)
            
            # Messages table (stores entire chat history as JSON)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_messages (
                    user_id INTEGER PRIMARY KEY,
                    history_json VARIANT,
                    FOREIGN KEY (user_id) REFERENCES scarlet_users(id)
                )
            """)

            # Canvas LMS Payload table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_canvas_lms (
                    user_id INTEGER PRIMARY KEY,
                    payload VARIANT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (user_id) REFERENCES scarlet_users(id)
                )
            """)

            # Google Calendar Token table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_google_cal_tokens (
                    user_id INTEGER PRIMARY KEY,
                    payload VARIANT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (user_id) REFERENCES scarlet_users(id)
                )
            """)

            # Google Drive Token table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scarlet_google_drive_tokens (
                    user_id INTEGER PRIMARY KEY,
                    payload VARIANT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (user_id) REFERENCES scarlet_users(id)
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

# --- User Functions ---

def add_user(db, username, name, password_hash):
    """Adds a new user and returns the full user object."""
    try:
        db.cursor.execute(
            "INSERT INTO scarlet_users (username, name, password_hash) VALUES (%s, %s, %s)",
            (username, name, password_hash)
        )
        db.connection.commit()
        return get_user_by_username(db, username)
    except Exception as e:
        db.connection.rollback()
        print(f"Error adding user: {e}")
        return None

def get_user_by_id(db, user_id):
    """Retrieves a user by their unique ID."""
    try:
        db.cursor.execute("SELECT * FROM scarlet_users WHERE id = %s", (user_id,))
        return db.cursor.fetchone()
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_user_by_username(db, username):
    """Retrieves a user by their username."""
    try:
        db.cursor.execute("SELECT * FROM scarlet_users WHERE username = %s", (username,))
        return db.cursor.fetchone()
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None

# --- Message History Functions ---

def upsert_message_history(db, user_id, history_dict):
    """Creates or updates the message history JSON for a user."""
    try:
        history_json = json.dumps(history_dict)
        db.cursor.execute("""
            MERGE INTO scarlet_messages t
            USING (SELECT %s AS user_id, PARSE_JSON(%s) AS history) s
            ON t.user_id = s.user_id
            WHEN MATCHED THEN UPDATE SET t.history_json = s.history
            WHEN NOT MATCHED THEN INSERT (user_id, history_json) VALUES (s.user_id, s.history)
        """, (user_id, history_json))
        db.connection.commit()
        return True
    except Exception as e:
        db.connection.rollback()
        print(f"Error upserting message history: {e}")
        return False

def get_message_history(db, user_id):
    """Retrieves the message history for a user."""
    try:
        db.cursor.execute("SELECT history_json FROM scarlet_messages WHERE user_id = %s", (user_id,))
        row = db.cursor.fetchone()
        if row and row['HISTORY_JSON']:
            return json.loads(row['HISTORY_JSON'])
        return None
    except Exception as e:
        print(f"Error getting message history: {e}")
        return None

# --- Helper function for upserting payloads ---

def _upsert_payload(db, table_name, user_id, payload_dict):
    """Generic helper to upsert a JSON payload for a user."""
    try:
        payload_json = json.dumps(payload_dict)
        query = f"""
            MERGE INTO {table_name} t
            USING (SELECT %s AS user_id, PARSE_JSON(%s) AS payload) s
            ON t.user_id = s.user_id
            WHEN MATCHED THEN UPDATE SET payload = s.payload, updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (user_id, payload) VALUES (s.user_id, s.payload)
        """
        db.cursor.execute(query, (user_id, payload_json))
        db.connection.commit()
        return True
    except Exception as e:
        db.connection.rollback()
        print(f"Error upserting payload for {table_name}: {e}")
        return False

def _get_payload(db, table_name, user_id):
    """Generic helper to retrieve a JSON payload for a user."""
    try:
        db.cursor.execute(f"SELECT payload FROM {table_name} WHERE user_id = %s", (user_id,))
        row = db.cursor.fetchone()
        if row and row['PAYLOAD']:
            # The VARIANT type is returned as a string, so we parse it
            return json.loads(row['PAYLOAD'])
        return None
    except Exception as e:
        print(f"Error getting payload from {table_name}: {e}")
        return None

# --- Canvas, GCal, GDrive Functions ---

def upsert_canvas_payload(db, user_id, payload_dict):
    return _upsert_payload(db, 'scarlet_canvas_lms', user_id, payload_dict)

def get_canvas_payload(db, user_id):
    return _get_payload(db, 'scarlet_canvas_lms', user_id)

def upsert_gcal_token(db, user_id, payload_dict):
    return _upsert_payload(db, 'scarlet_google_cal_tokens', user_id, payload_dict)

def get_gcal_token(db, user_id):
    return _get_payload(db, 'scarlet_google_cal_tokens', user_id)

def upsert_gdrive_token(db, user_id, payload_dict):
    return _upsert_payload(db, 'scarlet_google_drive_tokens', user_id, payload_dict)

def get_gdrive_token(db, user_id):
    return _get_payload(db, 'scarlet_google_drive_tokens', user_id)


# --- DB Initialization ---

def init_db():
    """Initializes the database and tables."""
    db = SnowflakeDB()
    if db.connect():
        db.init_tables()
        return db
    return None

def get_db():
    """Gets a new database connection."""
    db = SnowflakeDB()
    db.connect()
    return db