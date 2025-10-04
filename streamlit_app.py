#!/usr/bin/env python3
"""
Futuristic AI Agent Scheduler - Streamlit Interface
A modern, responsive web interface for AI agent communication
"""

import streamlit as st
import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Agent Scheduler",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for futuristic theme
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600;700&display=swap');
    
    /* Main theme colors */
    :root {
        --primary: #00d4ff;
        --secondary: #ff006e;
        --accent: #8338ec;
        --bg-dark: #0a0a0a;
        --bg-card: #1a1a1a;
        --text-light: #ffffff;
        --text-muted: #888888;
        --success: #00ff88;
        --warning: #ffaa00;
        --error: #ff3366;
    }
    
    /* Global styles */
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
        color: var(--text-light);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
    }
    
    /* Custom header */
    .main-header {
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
        text-align: center;
    }
    
    .main-header h1 {
        font-family: 'Orbitron', monospace;
        font-size: 3rem;
        font-weight: 900;
        color: white;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.8);
        margin: 0;
    }
    
    .main-header p {
        font-family: 'Exo 2', sans-serif;
        font-size: 1.2rem;
        color: rgba(255, 255, 255, 0.9);
        margin: 0.5rem 0 0 0;
    }
    
    /* Agent status cards */
    .agent-card {
        background: linear-gradient(145deg, var(--bg-card) 0%, #2a2a2a 100%);
        border: 1px solid var(--primary);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .agent-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 212, 255, 0.2);
    }
    
    .agent-card.active {
        border-color: var(--success);
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
    }
    
    .agent-card.error {
        border-color: var(--error);
        box-shadow: 0 0 20px rgba(255, 51, 102, 0.3);
    }
    
    .agent-card.processing {
        border-color: var(--warning);
        box-shadow: 0 0 20px rgba(255, 170, 0, 0.3);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online { background: var(--success); }
    .status-offline { background: var(--text-muted); }
    .status-processing { background: var(--warning); }
    .status-error { background: var(--error); }
    
    /* Chat interface */
    .chat-container {
        background: var(--bg-card);
        border: 1px solid var(--primary);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .message {
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 10px;
        animation: slideIn 0.3s ease;
    }
    
    .message.user {
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        margin-left: 20%;
    }
    
    .message.agent {
        background: linear-gradient(135deg, var(--bg-card) 0%, #2a2a2a 100%);
        border: 1px solid var(--primary);
        margin-right: 20%;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Progress bars */
    .progress-container {
        background: var(--bg-card);
        border: 1px solid var(--primary);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .progress-bar {
        background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        height: 8px;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        font-family: 'Exo 2', sans-serif;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 212, 255, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-card) 100%);
    }
    
    /* Metrics */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--primary);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
    }
    
    .metric-label {
        font-family: 'Exo 2', sans-serif;
        color: var(--text-muted);
        font-size: 0.9rem;
    }
    
    /* Animations */
    .fade-in {
        animation: fadeIn 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent);
    }
</style>
""", unsafe_allow_html=True)

class AgentScheduler:
    def __init__(self):
        self.agents = {
            'orchestrator': {'name': 'Orchestrator', 'status': 'offline', 'last_update': None},
            'gatherer': {'name': 'Gatherer', 'status': 'offline', 'last_update': None},
            'scheduler': {'name': 'Scheduler', 'status': 'offline', 'last_update': None}
        }
        self.messages = []
        self.current_task = None
        self.task_progress = 0
        
    def update_agent_status(self, agent_name: str, status: str, message: str = ""):
        """Update agent status and add to messages"""
        self.agents[agent_name]['status'] = status
        self.agents[agent_name]['last_update'] = datetime.now()
        
        if message:
            self.messages.append({
                'type': 'agent',
                'agent': agent_name,
                'content': message,
                'timestamp': datetime.now(),
                'status': status
            })
    
    def add_user_message(self, message: str):
        """Add user message to chat"""
        self.messages.append({
            'type': 'user',
            'content': message,
            'timestamp': datetime.now()
        })
    
    def get_agent_status_icon(self, status: str) -> str:
        """Get status icon for agent"""
        icons = {
            'online': '🟢',
            'offline': '⚫',
            'processing': '🟡',
            'error': '🔴'
        }
        return icons.get(status, '⚫')
    
    def render_agent_cards(self):
        """Render agent status cards"""
        st.markdown("### 🤖 Agent Status")
        
        cols = st.columns(3)
        
        for i, (agent_id, agent_data) in enumerate(self.agents.items()):
            with cols[i]:
                status_icon = self.get_agent_status_icon(agent_data['status'])
                
                card_class = f"agent-card {agent_data['status']}"
                
                st.markdown(f"""
                <div class="{card_class}">
                    <h4>{status_icon} {agent_data['name']}</h4>
                    <p><strong>Status:</strong> {agent_data['status'].title()}</p>
                    <p><strong>Last Update:</strong> {agent_data['last_update'].strftime('%H:%M:%S') if agent_data['last_update'] else 'Never'}</p>
                </div>
                """, unsafe_allow_html=True)
    
    def render_chat_interface(self):
        """Render chat interface"""
        st.markdown("### 💬 Agent Communication")
        
        # Chat messages
        chat_container = st.container()
        with chat_container:
            for message in self.messages[-10:]:  # Show last 10 messages
                if message['type'] == 'user':
                    st.markdown(f"""
                    <div class="message user">
                        <strong>You:</strong> {message['content']}
                        <br><small>{message['timestamp'].strftime('%H:%M:%S')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    status_icon = self.get_agent_status_icon(message.get('status', 'offline'))
                    st.markdown(f"""
                    <div class="message agent">
                        <strong>{status_icon} {message.get('agent', 'Agent').title()}:</strong> {message['content']}
                        <br><small>{message['timestamp'].strftime('%H:%M:%S')}</small>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Chat input
        user_input = st.text_input("Send message to agents:", key="chat_input")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🚀 Send Message", key="send_message"):
                if user_input:
                    self.add_user_message(user_input)
                    self.process_user_request(user_input)
                    st.rerun()
        
        with col2:
            if st.button("🔄 Refresh Status", key="refresh_status"):
                self.check_agent_status()
                st.rerun()
        
        with col3:
            if st.button("🧹 Clear Chat", key="clear_chat"):
                self.messages = []
                st.rerun()
    
    def render_task_progress(self):
        """Render current task progress"""
        if self.current_task:
            st.markdown("### ⚡ Current Task Progress")
            
            progress_container = st.container()
            with progress_container:
                st.markdown(f"""
                <div class="progress-container">
                    <h4>🎯 {self.current_task['name']}</h4>
                    <p>{self.current_task['description']}</p>
                    <div class="progress-bar" style="width: {self.task_progress}%;"></div>
                    <p>Progress: {self.task_progress}%</p>
                </div>
                """, unsafe_allow_html=True)
    
    def render_metrics(self):
        """Render system metrics"""
        st.markdown("### 📊 System Metrics")
        
        cols = st.columns(4)
        
        with cols[0]:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">3</div>
                <div class="metric-label">Active Agents</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">12</div>
                <div class="metric-label">Tasks Completed</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">98%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[3]:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">2.3s</div>
                <div class="metric-label">Avg Response</div>
            </div>
            """, unsafe_allow_html=True)
    
    def process_user_request(self, request: str):
        """Process user request and coordinate agents"""
        # Simulate agent coordination
        self.current_task = {
            'name': 'Processing Request',
            'description': f'Analyzing: "{request}"',
            'start_time': datetime.now()
        }
        self.task_progress = 0
        
        # Simulate agent responses
        self.simulate_agent_workflow(request)
    
    def simulate_agent_workflow(self, request: str):
        """Simulate agent workflow with progress updates"""
        # Orchestrator starts
        self.update_agent_status('orchestrator', 'processing', f"Analyzing request: {request}")
        time.sleep(1)
        self.task_progress = 25
        
        # Gatherer processes
        self.update_agent_status('gatherer', 'processing', "Gathering relevant data and materials...")
        time.sleep(1)
        self.task_progress = 50
        
        # Scheduler coordinates
        self.update_agent_status('scheduler', 'processing', "Creating schedule and calendar events...")
        time.sleep(1)
        self.task_progress = 75
        
        # Completion
        self.update_agent_status('orchestrator', 'online', "Task completed successfully!")
        self.update_agent_status('gatherer', 'online', "Data processing complete")
        self.update_agent_status('scheduler', 'online', "Schedule created and synced")
        self.task_progress = 100
        
        self.current_task = None
    
    def check_agent_status(self):
        """Check agent status (simulated)"""
        for agent_id in self.agents:
            # Simulate random status updates
            import random
            statuses = ['online', 'processing', 'error']
            weights = [0.7, 0.2, 0.1]
            status = random.choices(statuses, weights=weights)[0]
            
            if status == 'online':
                self.update_agent_status(agent_id, status, "Ready for new tasks")
            elif status == 'processing':
                self.update_agent_status(agent_id, status, "Working on assigned task...")
            else:
                self.update_agent_status(agent_id, status, "Error occurred, retrying...")

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = AgentScheduler()
    
    scheduler = st.session_state.scheduler
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI AGENT SCHEDULER</h1>
        <p>Advanced AI Coordination System • Real-time Agent Communication • Futuristic Interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")
        
        if st.button("🔄 Initialize Agents"):
            scheduler.update_agent_status('orchestrator', 'online', "Orchestrator initialized")
            scheduler.update_agent_status('gatherer', 'online', "Gatherer ready")
            scheduler.update_agent_status('scheduler', 'online', "Scheduler active")
            st.success("All agents initialized!")
        
        if st.button("🧪 Test Communication"):
            scheduler.add_user_message("Test message from user")
            scheduler.update_agent_status('orchestrator', 'processing', "Received test message")
            st.info("Test message sent to agents")
        
        if st.button("📊 Generate Report"):
            scheduler.add_user_message("Generate system report")
            scheduler.update_agent_status('orchestrator', 'processing', "Generating comprehensive report...")
            st.info("Report generation started")
        
        st.markdown("---")
        st.markdown("### 🔧 System Status")
        st.markdown(f"**Active Agents:** {sum(1 for agent in scheduler.agents.values() if agent['status'] == 'online')}")
        st.markdown(f"**Messages:** {len(scheduler.messages)}")
        st.markdown(f"**Current Task:** {'Yes' if scheduler.current_task else 'No'}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Agent status cards
        scheduler.render_agent_cards()
        
        # Chat interface
        scheduler.render_chat_interface()
        
        # Task progress
        scheduler.render_task_progress()
    
    with col2:
        # System metrics
        scheduler.render_metrics()
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🎯 Process Assignment", key="process_assignment"):
            scheduler.add_user_message("Process Canvas assignment")
            scheduler.process_user_request("Process Canvas assignment")
            st.rerun()
        
        if st.button("📅 Create Schedule", key="create_schedule"):
            scheduler.add_user_message("Create study schedule")
            scheduler.process_user_request("Create study schedule")
            st.rerun()
        
        if st.button("📚 Gather Materials", key="gather_materials"):
            scheduler.add_user_message("Gather course materials")
            scheduler.process_user_request("Gather course materials")
            st.rerun()
        
        if st.button("🔄 Sync Calendar", key="sync_calendar"):
            scheduler.add_user_message("Sync with Google Calendar")
            scheduler.process_user_request("Sync with Google Calendar")
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
        <p>🚀 AI Agent Scheduler • Powered by Advanced AI Coordination • Built with Streamlit</p>
        <p>Real-time Communication • Futuristic Interface • Next-Gen Scheduling</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
