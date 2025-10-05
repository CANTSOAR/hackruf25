#!/usr/bin/env python3
"""
Database setup for AI Agent Scheduler - Snowflake Version (FIXED)
"""

import snowflake.connector
from snowflake.connector import Error
import os
from dotenv import load_dotenv
import hashlib
import secrets

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def _get_last_identity(self) -> int:
        """Helper to reliably get the last inserted IDENTITY (AUTOINCREMENT) ID in Snowflake."""
        try:
            # FIX: Use LAST_IDENTITY() for reliable retrieval from AUTOINCREMENT columns
            self.cursor.execute("SELECT LAST_IDENTITY()")
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Warning: Could not retrieve last identity: {e}")
            return None

    def connect(self):
        """Connect to Snowflake database"""
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
            
            if self.connection:
                self.cursor = self.connection.cursor()
                print("✅ Connected to Snowflake database")
                return True
                
        except Error as e:
            # Recommending user checks for the 250001 error
            print(f"❌ Error connecting to Snowflake: {e}")
            print("\n🚨 CRITICAL CHECKLIST for 250001 Error:")
            print("1. Verify **Password** and **Username** are 100% correct (test in web browser).")
            print("2. Verify the connected **User** has been granted the **Role** ('SYSADMIN' or custom).")
            print("3. Verify the connected **User** has **USAGE** privilege on the **Warehouse** ('COMPUTE_WH').")
            return False
        
    def create_tables(self):
        """Create database tables"""
        try:
            # Users table 
            users_table = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP_NTZ,
    is_active BOOLEAN DEFAULT TRUE
)
"""
            
            # Chat sessions table
            sessions_table = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_name VARCHAR(100) DEFAULT 'New Chat',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""
            
            # Messages table 
            # Note: The CHECK constraint was removed in an earlier step to resolve a Snowflake compatibility error.
            messages_table = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    message_type VARCHAR(10) NOT NULL,
    agent_name VARCHAR(50),
    content TEXT NOT NULL,
    timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""
            
            # Agent status table
            agent_status_table = """
CREATE TABLE IF NOT EXISTS agent_status (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    last_update TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""
            
            # Execute table creation - these need access to all variables above
            self.cursor.execute(users_table)
            self.cursor.execute(sessions_table) 
            self.cursor.execute(messages_table)
            self.cursor.execute(agent_status_table)
            self.connection.commit()
            
            print("✅ Database tables created successfully")
            return True
            
        except Error as e:
            print(f"❌ Error creating tables: {e}")
            return False    
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        password_hash, _ = self.hash_password(password, salt)
        return password_hash == stored_hash
    
    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create new user account"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s", 
                (username, email)
            )
            if self.cursor.fetchone():
                print(f"User with username '{username}' or email '{email}' already exists.")
                return False
            
            password_hash, salt = self.hash_password(password)
            
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (%s, %s, %s, %s)
            """, (username, email, password_hash, salt))
            
            self.connection.commit()
            
            print(f"✅ User {username} created successfully")
            return True
            
        except Error as e:
            print(f"❌ Error creating user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> dict:
        """Authenticate user login"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                SELECT id, username, email, password_hash, salt, last_login
                FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            
            user = self.cursor.fetchone()
            if not user:
                return None
            
            user_id, username, email, stored_hash, salt, last_login = user
            
            if self.verify_password(password, stored_hash, salt):
                # FIX: Use %s for parameterization
                self.cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """, (user_id,))
                
                self.connection.commit()
                
                return {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'last_login': last_login
                }
            
            return None
            
        except Error as e:
            print(f"❌ Error authenticating user: {e}")
            return None
    
    def create_chat_session(self, user_id: int, session_name: str = "New Chat") -> int:
        """Create new chat session"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                INSERT INTO chat_sessions (user_id, session_name)
                VALUES (%s, %s)
            """, (user_id, session_name))
            
            self.connection.commit()
            
            # FIX: Use the reliable helper function
            return self._get_last_identity()
            
        except Error as e:
            print(f"❌ Error creating chat session: {e}")
            return None
    
    def get_user_sessions(self, user_id: int) -> list:
        """Get user's chat sessions"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                SELECT id, session_name, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY updated_at DESC
            """, (user_id,))
            
            return self.cursor.fetchall()
            
        except Error as e:
            print(f"❌ Error getting user sessions: {e}")
            return []
    
    def save_message(self, session_id: int, user_id: int, message_type: str, 
                        content: str, agent_name: str = None, status: str = "sent") -> int:
        """Save message to database"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                INSERT INTO messages (session_id, user_id, message_type, agent_name, content, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, user_id, message_type, agent_name, content, status))
            
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s
            """, (session_id,))

            self.connection.commit()
            
            # FIX: Use the reliable helper function
            return self._get_last_identity()
            
        except Error as e:
            print(f"❌ Error saving message: {e}")
            return None
    
    def get_messages(self, session_id: int, limit: int = 50, offset: int = 0) -> list:
        """Get messages for a session"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("""
                SELECT id, message_type, agent_name, content, timestamp, status
                FROM messages
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """, (session_id, limit, offset))
            
            return self.cursor.fetchall()
            
        except Error as e:
            print(f"❌ Error getting messages: {e}")
            return []
    
    def get_message_count(self, session_id: int) -> int:
        """Get total message count for a session"""
        try:
            # FIX: Use %s for parameterization
            self.cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = %s", (session_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
            
        except Error as e:
            print(f"❌ Error getting message count: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")

def setup_database():
    """Setup database with tables"""
    db = DatabaseManager()
    
    if db.connect():
        if db.create_tables():
            print("✅ Database setup completed successfully")
            return True
    
    return False

if __name__ == "__main__":
    setup_database()