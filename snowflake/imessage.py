#!/usr/bin/env python3
"""
Enhanced iMessage-Style AI Agent Chat
Full-featured chat application with AI agents and Snowflake integration
"""

import streamlit as st
import snowflake.connector
from snowflake.connector import Error
import hashlib
import secrets
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Agent Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced iMessage-style CSS with animations and better UX
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #f2f2f7;
        color: #000;
    }
    
    .stApp {
        background: #f2f2f7;
    }
    
    /* Login page styles */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    .login-card {
        background: white;
        border-radius: 20px;
        padding: 3rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        width: 100%;
        max-width: 400px;
        text-align: center;
        animation: fadeInScale 0.5s ease;
    }
    
    @keyframes fadeInScale {
        from {
            opacity: 0;
            transform: scale(0.95);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    .login-header {
        margin-bottom: 2rem;
    }
    
    .login-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1d1d1f;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #86868b;
        font-size: 1.1rem;
    }
    
    /* Chat interface styles */
    .chat-container {
        display: flex;
        height: 100vh;
        background: #f2f2f7;
    }
    
    .sidebar {
        width: 320px;
        background: white;
        border-right: 1px solid #e5e5ea;
        display: flex;
        flex-direction: column;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
    }
    
    .sidebar-header {
        padding: 1.5rem;
        border-bottom: 1px solid #e5e5ea;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .sidebar-header h2 {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .user-info {
        font-size: 0.9rem;
        opacity: 0.9;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    
    .agent-status-container {
        margin-top: 1rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .agent-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
    }
    
    .agent-status:last-child {
        margin-bottom: 0;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #34c759;
        box-shadow: 0 0 8px rgba(52, 199, 89, 0.5);
    }
    
    .status-dot.offline {
        background: #ff3b30;
        box-shadow: 0 0 8px rgba(255, 59, 48, 0.5);
    }
    
    .status-dot.processing {
        background: #ff9500;
        box-shadow: 0 0 8px rgba(255, 149, 0, 0.5);
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { 
            opacity: 1;
            transform: scale(1);
        }
        50% { 
            opacity: 0.7;
            transform: scale(1.1);
        }
    }
    
    .chat-list {
        flex: 1;
        overflow-y: auto;
        padding: 0.5rem;
    }
    
    .chat-item {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        position: relative;
    }
    
    .chat-item:hover {
        background: #f2f2f7;
        transform: translateX(2px);
    }
    
    .chat-item.active {
        background: #e3f2fd;
        border-color: #007aff;
    }
    
    .chat-item h3 {
        font-size: 1rem;
        font-weight: 600;
        color: #1d1d1f;
        margin-bottom: 0.25rem;
    }
    
    .chat-item p {
        font-size: 0.9rem;
        color: #86868b;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .chat-item .timestamp {
        font-size: 0.8rem;
        color: #86868b;
        margin-top: 0.25rem;
    }
    
    .new-chat-btn {
        margin: 1rem;
        padding: 0.75rem;
        background: #007aff;
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    
    .new-chat-btn:hover {
        background: #0056b3;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
    }
    
    .main-chat {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: #f2f2f7;
        overflow: hidden;
    }
    
    .chat-header {
        background: white;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e5ea;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    .chat-header h3 {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1d1d1f;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .chat-actions {
        display: flex;
        gap: 0.5rem;
    }
    
    .chat-action-btn {
        padding: 0.5rem 1rem;
        background: #f2f2f7;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
    }
    
    .chat-action-btn:hover {
        background: #e5e5ea;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        scroll-behavior: smooth;
    }
    
    .message-wrapper {
        display: flex;
        flex-direction: column;
        animation: slideIn 0.3s ease;
    }
    
    .message-wrapper.user {
        align-items: flex-end;
    }
    
    .message-wrapper.agent {
        align-items: flex-start;
    }
    
    .message {
        max-width: 70%;
        padding: 0.75rem 1rem;
        border-radius: 18px;
        font-size: 1rem;
        line-height: 1.4;
        word-wrap: break-word;
        position: relative;
    }
    
    .message.user {
        background: #007aff;
        color: white;
        border-bottom-right-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
    }
    
    .message.agent {
        background: white;
        color: #1d1d1f;
        border-bottom-left-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .message.system {
        background: #f2f2f7;
        color: #86868b;
        align-self: center;
        text-align: center;
        font-size: 0.9rem;
        border-radius: 12px;
        padding: 0.5rem 1rem;
        max-width: 80%;
    }
    
    .agent-label {
        font-size: 0.75rem;
        color: #86868b;
        margin-bottom: 0.25rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .message-time {
        font-size: 0.75rem;
        color: #86868b;
        margin-top: 0.25rem;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .chat-input-container {
        background: white;
        padding: 1rem 1.5rem;
        border-top: 1px solid #e5e5ea;
        display: flex;
        gap: 0.75rem;
        align-items: flex-end;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
    }
    
    .input-wrapper {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .chat-input {
        border: 2px solid #e5e5ea;
        border-radius: 20px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        resize: none;
        max-height: 100px;
        font-family: inherit;
        transition: all 0.2s ease;
    }
    
    .chat-input:focus {
        outline: none;
        border-color: #007aff;
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
    }
    
    .send-button {
        background: #007aff;
        color: white;
        border: none;
        border-radius: 50%;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 1.2rem;
    }
    
    .send-button:hover:not(:disabled) {
        background: #0056b3;
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
    }
    
    .send-button:disabled {
        background: #e5e5ea;
        cursor: not-allowed;
        transform: none;
    }
    
    /* Loading indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background: white;
        border-radius: 18px;
        border-bottom-left-radius: 4px;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .typing-dots {
        display: flex;
        gap: 0.25rem;
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        background: #86868b;
        border-radius: 50%;
        animation: typing 1.4s infinite;
    }
    
    .typing-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.4;
        }
        30% {
            transform: translateY(-10px);
            opacity: 1;
        }
    }
    
    /* Notification badge */
    .notification-badge {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: #ff3b30;
        color: white;
        border-radius: 10px;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-align: center;
        padding: 2rem;
    }
    
    .empty-state h2 {
        color: #86868b;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .empty-state p {
        color: #86868b;
        font-size: 1.1rem;
        max-width: 400px;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #c7c7cc;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #86868b;
    }
    
    /* Hide Streamlit elements */
    .stApp > header {
        display: none;
    }
    
    #MainMenu {
        visibility: hidden;
    }
    
    footer {
        visibility: hidden;
    }
    
    /* Logout button */
    .logout-btn {
        padding: 0.5rem 1rem;
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
        margin-top: 1rem;
    }
    
    .logout-btn:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: translateY(-2px);
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .sidebar {
            width: 100%;
            position: fixed;
            top: 0;
            left: -100%;
            height: 100vh;
            z-index: 1000;
            transition: left 0.3s ease;
        }
        
        .sidebar.open {
            left: 0;
        }
        
        .main-chat {
            width: 100%;
        }
        
        .message {
            max-width: 85%;
        }
    }
</style>
""", unsafe_allow_html=True)


class SnowflakeManager:
    """Manages Snowflake database connections and operations"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
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
            self.initialize_tables()
            return True
        except Error as e:
            st.error(f"Failed to connect to Snowflake: {e}")
            return False
    
    def initialize_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Users table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Chat sessions table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_name VARCHAR(100) DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Messages table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    message_type VARCHAR(20) NOT NULL,
                    agent_name VARCHAR(50),
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    status VARCHAR(20) DEFAULT 'sent',
                    metadata VARIANT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Agent interactions table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_interactions (
                    id INTEGER AUTOINCREMENT PRIMARY KEY,
                    message_id INTEGER NOT NULL,
                    agent_name VARCHAR(50) NOT NULL,
                    action VARCHAR(100),
                    result TEXT,
                    duration_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """)
            
            self.connection.commit()
            
        except Error as e:
            st.error(f"Error initializing tables: {e}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


class AIAgentOrchestrator:
    """Orchestrates AI agent interactions"""
    
    def __init__(self):
        self.agents = {
            'orchestrator': {'status': 'online', 'description': 'Main coordinator'},
            'gatherer': {'status': 'online', 'description': 'Information gatherer'},
            'scheduler': {'status': 'online', 'description': 'Task scheduler'}
        }
    
    def process_message(self, message: str, user_context: Dict) -> Dict[str, Any]:
        """Process user message through AI agents"""
        start_time = time.time()
        
        # Simulate agent processing
        response = {
            'agent': 'orchestrator',
            'content': '',
            'actions': [],
            'duration_ms': 0
        }
        
        # Determine message intent and route to appropriate agent
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['schedule', 'meeting', 'calendar', 'appointment']):
            response['agent'] = 'scheduler'
            response['content'] = f"I'll help you schedule that. What time works best for you?"
            response['actions'].append('schedule_request')
            
        elif any(word in message_lower for word in ['find', 'search', 'lookup', 'information']):
            response['agent'] = 'gatherer'
            response['content'] = f"I'm searching for information about: {message}"
            response['actions'].append('information_search')
            
        else:
            response['agent'] = 'orchestrator'
            response['content'] = f"I understand you said: '{message}'. How can I help you with that?"
            response['actions'].append('general_conversation')
        
        response['duration_ms'] = int((time.time() - start_time) * 1000)
        return response
    
    def get_agent_status(self, agent_name: str) -> str:
        """Get status of specific agent"""
        return self.agents.get(agent_name, {}).get('status', 'offline')
    
    def update_agent_status(self, agent_name: str, status: str):
        """Update agent status"""
        if agent_name in self.agents:
            self.agents[agent_name]['status'] = status


class EnhancediMessageChat:
    """Main chat application class"""
    
    def __init__(self):
        self.db = SnowflakeManager()
        self.orchestrator = AIAgentOrchestrator()
        
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
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user login"""
        try:
            self.db.cursor.execute("""
                SELECT id, username, email, password_hash, salt, last_login
                FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            
            result = self.db.cursor.fetchone()
            if not result:
                return None
            
            user_id, username, email, stored_hash, salt, last_login = result
            
            if self.verify_password(password, stored_hash, salt):
                self.db.cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP() WHERE id = %s
                """, (user_id,))
                self.db.connection.commit()
                
                return {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'last_login': last_login
                }
            
            return None
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
    
    def create_user(self, username: str, email: str, password: str) -> tuple:
        """Create new user account"""
        try:
            # Validate input
            if len(username) < 3:
                return False, "Username must be at least 3 characters"
            if len(password) < 6:
                return False, "Password must be at least 6 characters"
            if '@' not in email:
                return False, "Invalid email address"
            
            # Check if user exists
            self.db.cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            if self.db.cursor.fetchone():
                return False, "Username or email already exists"
            
            # Hash password
            password_hash, salt = self.hash_password(password)
            
            # Insert user
            self.db.cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (%s, %s, %s, %s)
            """, (username, email, password_hash, salt))
            
            self.db.connection.commit()
            return True, "Account created successfully! Please log in."
            
        except Exception as e:
            return False, f"Error creating account: {e}"
    
    def get_user_sessions(self, user_id: int) -> List:
        """Get user's chat sessions"""
        try:
            self.db.cursor.execute("""
                SELECT s.id, s.session_name, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                WHERE s.user_id = %s AND s.is_active = TRUE
                GROUP BY s.id, s.session_name, s.created_at, s.updated_at
                ORDER BY s.updated_at DESC
            """, (user_id,))
            
            return self.db.cursor.fetchall()
            
        except Exception as e:
            st.error(f"Error fetching sessions: {e}")
            return []
    
    def create_chat_session(self, user_id: int, session_name: str = "New Chat") -> Optional[int]:
        """Create new chat session"""
        try:
            self.db.cursor.execute("""
                INSERT INTO chat_sessions (user_id, session_name)
                VALUES (%s, %s)
            """, (user_id, session_name))
            
            self.db.connection.commit()
            
            # Get the last inserted ID
            self.db.cursor.execute("SELECT LAST_INSERT_ID()")
            return self.db.cursor.fetchone()[0]
            
        except Exception as e:
            st.error(f"Error creating session: {e}")
            return None
    
    def save_message(self, session_id: int, user_id: int, message_type: str, 
                    content: str, agent_name: str = None, metadata: Dict = None) -> Optional[int]:
        """Save message to database"""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            self.db.cursor.execute("""
                INSERT INTO messages (session_id, user_id, message_type, agent_name, content, metadata)
                VALUES (%s, %s, %s, %s, %s, PARSE_JSON(%s))
            """, (session_id, user_id, message_type, agent_name, content, metadata_json))
            
            # Update session timestamp
            self.db.cursor.execute("""
                UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP() WHERE id = %s
            """, (session_id,))
            
            self.db.connection.commit()
            
            self.db.cursor.execute("SELECT LAST_INSERT_ID()")
            return self.db.cursor.fetchone()[0]
            
        except Exception as e:
            st.error(f"Error saving message: {e}")
            return None
    
    def get_messages(self, session_id: int, limit: int = 50) -> List:
        """Get messages for a session"""
        try:
            self.db.cursor.execute("""
                SELECT id, message_type, agent_name, content, timestamp, status
                FROM messages
                WHERE session_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (session_id, limit))
            
            return self.db.cursor.fetchall()
            
        except Exception as e:
            st.error(f"Error fetching messages: {e}")
            return []
    
    def delete_session(self, session_id: int):
        """Soft delete a chat session"""
        try:
            self.db.cursor.execute("""
                UPDATE chat_sessions SET is_active = FALSE WHERE id = %s
            """, (session_id,))
            self.db.connection.commit()
        except Exception as e:
            st.error(f"Error deleting session: {e}")
    
    def render_login_page(self):
        """Render login/registration page"""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 3rem 0;">
                <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">💬</h1>
                <h2 style="color: #1d1d1f; margin-bottom: 0.5rem;">AI Agent Chat</h2>
                <p style="color: #86868b; font-size: 1.1rem;">Connect with intelligent AI agents</p>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Sign In", "Create Account"])
            
            with tab1:
                self.render_login_form()
            
            with tab2:
                self.render_register_form()
    
    def render_login_form(self):
        """Render login form"""
        with st.form("login_form", clear_on_submit=True):
            st.text_input("Username", key="login_username", placeholder="Enter your username")
            st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            with col2:
                if st.form_submit_button("Demo Mode", use_container_width=True):
                    st.info("Demo mode: Try username 'demo' with password 'demo123'")
            
            if submit:
                username = st.session_state.login_username
                password = st.session_state.login_password
                
                if username and password:
                    if self.db.connect():
                        user = self.authenticate_user(username, password)
                        if user:
                            st.session_state.user = user
                            st.session_state.current_session = None
                            st.success("Login successful!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
                    else:
                        st.error("❌ Database connection failed. Please check your configuration.")
                else:
                    st.warning("⚠️ Please fill in all fields")
    
    def render_register_form(self):
        """Render registration form"""
        with st.form("register_form", clear_on_submit=True):
            st.text_input("Username", key="reg_username", placeholder="Choose a username (min 3 characters)")
            st.text_input("Email", key="reg_email", placeholder="Enter your email")
            st.text_input("Password", type="password", key="reg_password", placeholder="Create a password (min 6 characters)")
            st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Confirm your password")
            
            submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            
            if submit:
                username = st.session_state.reg_username
                email = st.session_state.reg_email
                password = st.session_state.reg_password
                confirm = st.session_state.reg_confirm
                
                if username and email and password and confirm:
                    if password != confirm:
                        st.error("❌ Passwords do not match")
                    else:
                        if self.db.connect():
                            success, message = self.create_user(username, email, password)
                            if success:
                                st.success(f"✅ {message}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                        else:
                            st.error("❌ Database connection failed")
                else:
                    st.warning("⚠️ Please fill in all fields")
    
    def render_chat_interface(self):
        """Render main chat interface"""
        if not self.db.connect():
            st.error("Database connection failed")
            return
        
        user = st.session_state.user
        
        # Create layout
        col_sidebar, col_chat = st.columns([1, 3])
        
        with col_sidebar:
            self.render_sidebar(user)
        
        with col_chat:
            if st.session_state.current_session:
                self.render_chat_area(user)
            else:
                self.render_empty_state()
    
    def render_sidebar(self, user: Dict):
        """Render sidebar with sessions"""
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem;">
            <h2 style="margin: 0; font-size: 1.5rem;">💬 Chats</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">
                Welcome, <strong>{user['username']}</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Agent status
        with st.expander("🤖 Agent Status", expanded=True):
            for agent_name, agent_info in self.orchestrator.agents.items():
                status = agent_info['status']
                emoji = "🟢" if status == "online" else "🔴" if status == "offline" else "🟡"
                st.markdown(f"{emoji} **{agent_name.title()}**: {status}")
        
        st.markdown("---")
        
        # New chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            session_id = self.create_chat_session(user['id'])
            if session_id:
                st.session_state.current_session = session_id
                st.rerun()
        
        st.markdown("### Recent Chats")
        
        # Get and display sessions
        sessions = self.get_user_sessions(user['id'])
        
        if sessions:
            for session in sessions:
                session_id, session_name, created_at, updated_at, msg_count = session
                is_active = session_id == st.session_state.current_session
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"{'📍' if is_active else '💬'} {session_name}",
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                    ):
                        st.session_state.current_session = session_id
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"delete_{session_id}"):
                        self.delete_session(session_id)
                        if st.session_state.current_session == session_id:
                            st.session_state.current_session = None
                        st.rerun()
                
                st.caption(f"💬 {msg_count} messages • {updated_at.strftime('%m/%d %H:%M')}")
                st.markdown("---")
        else:
            st.info("No chats yet. Create a new chat to get started!")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    def render_empty_state(self):
        """Render empty state when no chat is selected"""
        st.markdown("""
        <div class="empty-state">
            <h2>👋 Welcome to AI Agent Chat</h2>
            <p>Select a chat from the sidebar or create a new one to start chatting with AI agents.</p>
            <br>
            <p style="font-size: 0.9rem;">
                Our agents can help you with:<br>
                🗓️ Scheduling meetings<br>
                🔍 Finding information<br>
                💬 General conversation
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_chat_area(self, user: Dict):
        """Render main chat area"""
        session_id = st.session_state.current_session
        
        # Chat header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown("### 💬 Chat")
        with col2:
            session_name = st.text_input("Rename", value="Chat Session", label_visibility="collapsed")
        with col3:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.markdown("---")
        
        # Messages container
        messages_container = st.container()
        
        with messages_container:
            messages = self.get_messages(session_id)
            
            if not messages:
                st.info("👋 Start the conversation! Send a message below.")
            else:
                for msg in messages:
                    msg_id, msg_type, agent_name, content, timestamp, status = msg
                    
                    if msg_type == 'user':
                        st.markdown(f"""
                        <div class="message-wrapper user">
                            <div class="message user">
                                {content}
                            </div>
                            <div class="message-time">{timestamp.strftime('%I:%M %p')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="message-wrapper agent">
                            <div class="agent-label">🤖 {agent_name or 'AI Assistant'}</div>
                            <div class="message agent">
                                {content}
                            </div>
                            <div class="message-time">{timestamp.strftime('%I:%M %p')}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Chat input
        with st.form("chat_input_form", clear_on_submit=True):
            col1, col2 = st.columns([5, 1])
            
            with col1:
                user_input = st.text_area(
                    "Message",
                    placeholder="Type your message here...",
                    label_visibility="collapsed",
                    height=80,
                    key="user_message"
                )
            
            with col2:
                send_button = st.form_submit_button("📤 Send", use_container_width=True, type="primary")
            
            if send_button and user_input.strip():
                # Save user message
                self.save_message(session_id, user['id'], 'user', user_input.strip())
                
                # Process with AI agents
                with st.spinner("🤖 AI agents are thinking..."):
                    # Update agent status
                    self.orchestrator.update_agent_status('orchestrator', 'processing')
                    
                    # Get AI response
                    response = self.orchestrator.process_message(user_input.strip(), user)
                    
                    # Save AI response
                    self.save_message(
                        session_id, 
                        user['id'], 
                        'agent', 
                        response['content'],
                        response['agent'],
                        {'actions': response['actions'], 'duration_ms': response['duration_ms']}
                    )
                    
                    # Reset agent status
                    self.orchestrator.update_agent_status('orchestrator', 'online')
                
                st.success("Message sent!")
                time.sleep(0.5)
                st.rerun()


def main():
    """Main application entry point"""
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_session' not in st.session_state:
        st.session_state.current_session = None
    
    # Initialize chat system
    if 'chat' not in st.session_state:
        st.session_state.chat = EnhancediMessageChat()
    
    chat = st.session_state.chat
    
    # Route to appropriate page
    if st.session_state.user is None:
        chat.render_login_page()
    else:
        chat.render_chat_interface()


if __name__ == "__main__":
    main()