#!/usr/bin/env python3
"""
Agent Communication Interface
Handles async communication between Streamlit UI and AI agents
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import queue
import uuid
from dataclasses import dataclass
from enum import Enum

class AgentStatus(Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    PROCESSING = "processing"
    ERROR = "error"
    COMPLETED = "completed"

@dataclass
class AgentMessage:
    id: str
    agent_name: str
    content: str
    status: AgentStatus
    timestamp: datetime
    task_id: Optional[str] = None
    progress: int = 0

@dataclass
class Task:
    id: str
    name: str
    description: str
    status: str
    progress: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    agents_involved: List[str] = None
    result: Optional[Dict] = None

class AgentInterface:
    """Handles communication between UI and AI agents"""
    
    def __init__(self):
        self.agents = {
            'orchestrator': {
                'name': 'Orchestrator',
                'status': AgentStatus.OFFLINE,
                'last_update': None,
                'capabilities': ['coordination', 'planning', 'decision_making']
            },
            'gatherer': {
                'name': 'Gatherer', 
                'status': AgentStatus.OFFLINE,
                'last_update': None,
                'capabilities': ['data_extraction', 'canvas_integration', 'material_analysis']
            },
            'scheduler': {
                'name': 'Scheduler',
                'status': AgentStatus.OFFLINE,
                'last_update': None,
                'capabilities': ['calendar_management', 'time_optimization', 'event_creation']
            }
        }
        
        self.message_queue = queue.Queue()
        self.task_queue = queue.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.message_history: List[AgentMessage] = []
        self.callbacks: List[Callable] = []
        
        # Start background processing
        self._start_background_processing()
    
    def _start_background_processing(self):
        """Start background thread for processing messages and tasks"""
        self.processing_thread = threading.Thread(target=self._background_processor, daemon=True)
        self.processing_thread.start()
    
    def _background_processor(self):
        """Background processor for handling async operations"""
        while True:
            try:
                # Process messages
                if not self.message_queue.empty():
                    message = self.message_queue.get_nowait()
                    self._process_message(message)
                
                # Process tasks
                if not self.task_queue.empty():
                    task = self.task_queue.get_nowait()
                    self._process_task(task)
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                print(f"Error in background processor: {e}")
                time.sleep(1)
    
    def _process_message(self, message: AgentMessage):
        """Process incoming agent message"""
        self.message_history.append(message)
        
        # Update agent status
        if message.agent_name in self.agents:
            self.agents[message.agent_name]['status'] = message.status
            self.agents[message.agent_name]['last_update'] = message.timestamp
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    def _process_task(self, task: Task):
        """Process task with agent coordination"""
        self.active_tasks[task.id] = task
        
        # Simulate agent workflow
        self._simulate_agent_workflow(task)
    
    def _simulate_agent_workflow(self, task: Task):
        """Simulate realistic agent workflow"""
        try:
            # Phase 1: Orchestrator analysis
            self._send_agent_message(
                agent_name='orchestrator',
                content=f"Analyzing task: {task.name}",
                status=AgentStatus.PROCESSING,
                task_id=task.id,
                progress=10
            )
            time.sleep(1)
            
            # Phase 2: Gatherer data collection
            self._send_agent_message(
                agent_name='gatherer',
                content="Collecting relevant data and materials...",
                status=AgentStatus.PROCESSING,
                task_id=task.id,
                progress=30
            )
            time.sleep(2)
            
            # Phase 3: Scheduler coordination
            self._send_agent_message(
                agent_name='scheduler',
                content="Creating optimized schedule...",
                status=AgentStatus.PROCESSING,
                task_id=task.id,
                progress=60
            )
            time.sleep(1)
            
            # Phase 4: Final coordination
            self._send_agent_message(
                agent_name='orchestrator',
                content="Finalizing coordination and validation...",
                status=AgentStatus.PROCESSING,
                task_id=task.id,
                progress=80
            )
            time.sleep(1)
            
            # Phase 5: Completion
            self._send_agent_message(
                agent_name='orchestrator',
                content=f"Task '{task.name}' completed successfully!",
                status=AgentStatus.COMPLETED,
                task_id=task.id,
                progress=100
            )
            
            # Update task status
            task.status = 'completed'
            task.progress = 100
            task.completed_at = datetime.now()
            task.result = {
                'success': True,
                'message': 'Task completed successfully',
                'data': {'task_id': task.id, 'completion_time': task.completed_at.isoformat()}
            }
            
            # Clean up after delay
            threading.Timer(5.0, lambda: self._cleanup_task(task.id)).start()
            
        except Exception as e:
            self._send_agent_message(
                agent_name='orchestrator',
                content=f"Error processing task: {str(e)}",
                status=AgentStatus.ERROR,
                task_id=task.id
            )
            
            task.status = 'error'
            task.result = {'success': False, 'error': str(e)}
    
    def _send_agent_message(self, agent_name: str, content: str, status: AgentStatus, 
                           task_id: Optional[str] = None, progress: int = 0):
        """Send message from agent"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            content=content,
            status=status,
            timestamp=datetime.now(),
            task_id=task_id,
            progress=progress
        )
        
        self.message_queue.put(message)
    
    def _cleanup_task(self, task_id: str):
        """Clean up completed task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
    
    def submit_task(self, name: str, description: str) -> str:
        """Submit new task for processing"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            description=description,
            status='pending',
            progress=0,
            created_at=datetime.now(),
            agents_involved=['orchestrator', 'gatherer', 'scheduler']
        )
        
        self.task_queue.put(task)
        return task_id
    
    def get_agent_status(self, agent_name: str) -> Dict:
        """Get current status of specific agent"""
        if agent_name in self.agents:
            return {
                'name': self.agents[agent_name]['name'],
                'status': self.agents[agent_name]['status'].value,
                'last_update': self.agents[agent_name]['last_update'],
                'capabilities': self.agents[agent_name]['capabilities']
            }
        return None
    
    def get_all_agents_status(self) -> Dict[str, Dict]:
        """Get status of all agents"""
        return {name: self.get_agent_status(name) for name in self.agents.keys()}
    
    def get_recent_messages(self, limit: int = 20) -> List[AgentMessage]:
        """Get recent messages"""
        return self.message_history[-limit:] if self.message_history else []
    
    def get_active_tasks(self) -> List[Task]:
        """Get currently active tasks"""
        return list(self.active_tasks.values())
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.active_tasks.get(task_id)
    
    def initialize_agents(self):
        """Initialize all agents"""
        for agent_name in self.agents:
            self._send_agent_message(
                agent_name=agent_name,
                content=f"{self.agents[agent_name]['name']} initialized and ready",
                status=AgentStatus.ONLINE
            )
    
    def test_communication(self):
        """Test agent communication"""
        self._send_agent_message(
            agent_name='orchestrator',
            content="Communication test initiated",
            status=AgentStatus.PROCESSING
        )
        
        time.sleep(0.5)
        
        self._send_agent_message(
            agent_name='orchestrator',
            content="Communication test successful - all systems operational",
            status=AgentStatus.ONLINE
        )
    
    def add_callback(self, callback: Callable):
        """Add callback for message notifications"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

# Global agent interface instance
agent_interface = AgentInterface()

# Convenience functions for Streamlit
def get_agent_interface() -> AgentInterface:
    """Get global agent interface instance"""
    return agent_interface

def submit_user_request(request: str) -> str:
    """Submit user request as task"""
    return agent_interface.submit_task(
        name=f"User Request: {request[:50]}...",
        description=request
    )

def get_system_status() -> Dict:
    """Get overall system status"""
    agents_status = agent_interface.get_all_agents_status()
    active_tasks = agent_interface.get_active_tasks()
    recent_messages = agent_interface.get_recent_messages(10)
    
    return {
        'agents': agents_status,
        'active_tasks': len(active_tasks),
        'recent_messages': len(recent_messages),
        'system_health': 'healthy' if all(
            agent['status'] in ['online', 'processing'] 
            for agent in agents_status.values()
        ) else 'degraded'
    }
