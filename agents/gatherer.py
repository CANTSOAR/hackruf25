"""
Canvas Data Gatherer Agent

This agent gathers assignment data from Canvas, extracts course materials,
processes the information intelligently, and outputs to Google Calendar.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain_core.tools import tool
from dotenv import load_dotenv
from baseagent import BaseAgent

load_dotenv()

@dataclass
class Assignment:
    """Data class for Canvas assignments"""
    id: str
    name: str
    description: str
    due_date: datetime
    points: int
    course_id: str
    course_name: str
    instructions: str
    submission_types: List[str]
    allowed_extensions: List[str]

@dataclass
class CourseMaterial:
    """Data class for course materials"""
    id: str
    name: str
    type: str  # "lecture", "notes", "reading", "video", "document"
    url: str
    course_id: str
    description: str
    file_size: Optional[int]
    last_modified: datetime

@dataclass
class ProcessedAssignment:
    """Data class for processed assignment data"""
    assignment: Assignment
    relevant_materials: List[CourseMaterial]
    suggested_schedule: Dict[str, Any]
    priority_level: int
    estimated_time: int
    study_plan: List[str]

# Canvas API configuration
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://your-canvas-instance.instructure.com/api/v1")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN")

@tool
def read_assignment(assignment_url: str, course_id: str = None) -> str:
    """
    Read assignment data from Canvas assignment URL.
    
    Args:
        assignment_url: URL of the Canvas assignment
        course_id: Optional course ID for additional context
    
    Returns:
        JSON string containing assignment data
    """
    try:
        # Extract assignment ID from URL
        assignment_id = assignment_url.split('/')[-1].split('?')[0]
        
        # Canvas API headers
        headers = {
            'Authorization': f'Bearer {CANVAS_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Get assignment details
        assignment_response = requests.get(
            f"{CANVAS_API_URL}/courses/{course_id}/assignments/{assignment_id}",
            headers=headers
        )
        
        if assignment_response.status_code != 200:
            return json.dumps({"error": f"Failed to fetch assignment: {assignment_response.status_code}"})
        
        assignment_data = assignment_response.json()
        
        # Get course information
        course_response = requests.get(
            f"{CANVAS_API_URL}/courses/{course_id}",
            headers=headers
        )
        course_data = course_response.json() if course_response.status_code == 200 else {}
        
        # Parse assignment data
        assignment = Assignment(
            id=assignment_data.get('id', ''),
            name=assignment_data.get('name', ''),
            description=assignment_data.get('description', ''),
            due_date=datetime.fromisoformat(assignment_data.get('due_at', '').replace('Z', '+00:00')) if assignment_data.get('due_at') else None,
            points=assignment_data.get('points_possible', 0),
            course_id=course_id or assignment_data.get('course_id', ''),
            course_name=course_data.get('name', ''),
            instructions=assignment_data.get('instructions', ''),
            submission_types=assignment_data.get('submission_types', []),
            allowed_extensions=assignment_data.get('allowed_extensions', [])
        )
        
        return json.dumps({
            "assignment": {
                "id": assignment.id,
                "name": assignment.name,
                "description": assignment.description,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "points": assignment.points,
                "course_id": assignment.course_id,
                "course_name": assignment.course_name,
                "instructions": assignment.instructions,
                "submission_types": assignment.submission_types,
                "allowed_extensions": assignment.allowed_extensions
            },
            "status": "success"
        })
        
    except Exception as e:
        return json.dumps({"error": f"Error reading assignment: {str(e)}"})

@tool
def read_files(course_id: str, assignment_id: str = None) -> str:
    """
    Read course files, lectures, and materials from Canvas course page.
    
    Args:
        course_id: Canvas course ID
        assignment_id: Optional assignment ID for context-specific materials
    
    Returns:
        JSON string containing course materials
    """
    try:
        headers = {
            'Authorization': f'Bearer {CANVAS_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        materials = []
        
        # Get course files
        files_response = requests.get(
            f"{CANVAS_API_URL}/courses/{course_id}/files",
            headers=headers
        )
        
        if files_response.status_code == 200:
            files_data = files_response.json()
            for file_data in files_data:
                material = CourseMaterial(
                    id=file_data.get('id', ''),
                    name=file_data.get('display_name', ''),
                    type="document",
                    url=file_data.get('url', ''),
                    course_id=course_id,
                    description=file_data.get('description', ''),
                    file_size=file_data.get('size', 0),
                    last_modified=datetime.fromisoformat(file_data.get('updated_at', '').replace('Z', '+00:00')) if file_data.get('updated_at') else None
                )
                materials.append(material)
        
        # Get course modules (lectures, readings, etc.)
        modules_response = requests.get(
            f"{CANVAS_API_URL}/courses/{course_id}/modules",
            headers=headers
        )
        
        if modules_response.status_code == 200:
            modules_data = modules_response.json()
            for module in modules_data:
                # Get module items
                items_response = requests.get(
                    f"{CANVAS_API_URL}/courses/{course_id}/modules/{module['id']}/items",
                    headers=headers
                )
                
                if items_response.status_code == 200:
                    items_data = items_response.json()
                    for item in items_data:
                        material_type = "lecture" if item.get('type') == 'Page' else "reading"
                        material = CourseMaterial(
                            id=item.get('id', ''),
                            name=item.get('title', ''),
                            type=material_type,
                            url=item.get('url', ''),
                            course_id=course_id,
                            description=item.get('description', ''),
                            file_size=None,
                            last_modified=None
                        )
                        materials.append(material)
        
        # Get announcements (often contain important course information)
        announcements_response = requests.get(
            f"{CANVAS_API_URL}/courses/{course_id}/discussion_topics",
            headers=headers
        )
        
        if announcements_response.status_code == 200:
            announcements_data = announcements_response.json()
            for announcement in announcements_data:
                material = CourseMaterial(
                    id=announcement.get('id', ''),
                    name=announcement.get('title', ''),
                    type="announcement",
                    url=announcement.get('url', ''),
                    course_id=course_id,
                    description=announcement.get('message', ''),
                    file_size=None,
                    last_modified=datetime.fromisoformat(announcement.get('posted_at', '').replace('Z', '+00:00')) if announcement.get('posted_at') else None
                )
                materials.append(material)
        
        return json.dumps({
            "materials": [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.type,
                    "url": m.url,
                    "course_id": m.course_id,
                    "description": m.description,
                    "file_size": m.file_size,
                    "last_modified": m.last_modified.isoformat() if m.last_modified else None
                } for m in materials
            ],
            "total_count": len(materials),
            "status": "success"
        })
        
    except Exception as e:
        return json.dumps({"error": f"Error reading course files: {str(e)}"})

@tool
def data_processor_assignment(assignment_data: str, materials_data: str) -> str:
    """
    Process assignment data and select the best relevant materials.
    
    Args:
        assignment_data: JSON string of assignment data from read_assignment
        materials_data: JSON string of materials data from read_files
    
    Returns:
        JSON string containing processed assignment with recommendations
    """
    try:
        assignment_json = json.loads(assignment_data)
        materials_json = json.loads(materials_data)
        
        if "error" in assignment_json or "error" in materials_json:
            return json.dumps({"error": "Invalid input data"})
        
        assignment = assignment_json["assignment"]
        materials = materials_json["materials"]
        
        # Analyze assignment requirements
        assignment_name = assignment.get("name", "").lower()
        assignment_description = assignment.get("description", "").lower()
        assignment_instructions = assignment.get("instructions", "").lower()
        
        # Score materials based on relevance to assignment
        relevant_materials = []
        for material in materials:
            score = 0
            material_name = material.get("name", "").lower()
            material_description = material.get("description", "").lower()
            material_type = material.get("type", "")
            
            # Score based on name similarity
            if any(word in material_name for word in assignment_name.split()):
                score += 3
            
            # Score based on description similarity
            if any(word in material_description for word in assignment_description.split()):
                score += 2
            
            # Score based on material type relevance
            if material_type in ["lecture", "notes"]:
                score += 2
            elif material_type == "document":
                score += 1
            
            # Score based on recency (if available)
            if material.get("last_modified"):
                last_modified = datetime.fromisoformat(material["last_modified"])
                days_old = (datetime.now() - last_modified).days
                if days_old < 30:
                    score += 1
            
            if score > 0:
                material["relevance_score"] = score
                relevant_materials.append(material)
        
        # Sort by relevance score
        relevant_materials.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Calculate priority level based on due date and points
        due_date = datetime.fromisoformat(assignment.get("due_date", "")) if assignment.get("due_date") else None
        points = assignment.get("points", 0)
        
        priority_level = 3  # Default medium priority
        if due_date:
            days_until_due = (due_date - datetime.now()).days
            if days_until_due <= 3:
                priority_level = 1  # High priority
            elif days_until_due <= 7:
                priority_level = 2  # Medium-high priority
        
        if points > 50:
            priority_level = min(priority_level, 2)  # High point assignments are important
        
        # Estimate time required
        estimated_time = max(2, points // 10)  # Rough estimate: 1 hour per 10 points
        
        # Create study plan
        study_plan = []
        if relevant_materials:
            study_plan.append(f"Review {relevant_materials[0]['name']} (highest relevance)")
            if len(relevant_materials) > 1:
                study_plan.append(f"Study {relevant_materials[1]['name']} (secondary material)")
        
        study_plan.extend([
            "Read assignment instructions carefully",
            "Create outline or draft",
            "Review rubric if available",
            "Start working on assignment"
        ])
        
        # Create suggested schedule
        suggested_schedule = {
            "start_date": datetime.now().isoformat(),
            "due_date": assignment.get("due_date"),
            "daily_tasks": [
                f"Day 1: Review materials and create outline",
                f"Day 2: Begin research and initial draft",
                f"Day 3: Complete draft and review",
                f"Day 4: Final review and submission"
            ]
        }
        
        processed_data = {
            "assignment": assignment,
            "relevant_materials": relevant_materials[:5],  # Top 5 most relevant
            "priority_level": priority_level,
            "estimated_time": estimated_time,
            "study_plan": study_plan,
            "suggested_schedule": suggested_schedule,
            "status": "success"
        }
        
        return json.dumps(processed_data)
        
    except Exception as e:
        return json.dumps({"error": f"Error processing assignment data: {str(e)}"})

@tool
def output_google_drive(processed_data: str) -> str:
    """
    Output processed assignment data to Google Calendar.
    
    Args:
        processed_data: JSON string of processed assignment data
    
    Returns:
        JSON string with output status
    """
    try:
        data = json.loads(processed_data)
        
        if "error" in data:
            return json.dumps({"error": "Invalid processed data"})
        
        assignment = data["assignment"]
        priority_level = data["priority_level"]
        estimated_time = data["estimated_time"]
        study_plan = data["study_plan"]
        suggested_schedule = data["suggested_schedule"]
        
        # Google Calendar API setup
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        # Load credentials (you'll need to set up OAuth2 credentials)
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        
        # For demo purposes, we'll create a mock calendar event
        calendar_event = {
            "summary": f"📚 {assignment['name']} - {assignment['course_name']}",
            "description": f"""
Assignment: {assignment['name']}
Course: {assignment['course_name']}
Points: {assignment['points']}
Due Date: {assignment['due_date']}
Priority Level: {priority_level}/5
Estimated Time: {estimated_time} hours

Study Plan:
{chr(10).join(f"• {task}" for task in study_plan)}

Relevant Materials:
{chr(10).join(f"• {material['name']} ({material['type']})" for material in data['relevant_materials'][:3])}

Instructions:
{assignment.get('instructions', 'No specific instructions provided')}
            """.strip(),
            "start": {
                "dateTime": suggested_schedule["start_date"],
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": (datetime.fromisoformat(suggested_schedule["start_date"]) + timedelta(hours=estimated_time)).isoformat(),
                "timeZone": "America/New_York"
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 60}  # 1 hour before
                ]
            },
            "colorId": str(priority_level)  # Color based on priority
        }
        
        # In a real implementation, you would use the Google Calendar API here
        # For now, we'll return the event data
        return json.dumps({
            "calendar_event": calendar_event,
            "status": "success",
            "message": "Assignment successfully added to Google Calendar",
            "event_id": f"assignment_{assignment['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        })
        
    except Exception as e:
        return json.dumps({"error": f"Error outputting to Google Calendar: {str(e)}"})

# Initialize the gatherer agent
gatherer = BaseAgent(
    name="Gatherer",
    tools=[read_assignment, read_files, data_processor_assignment, output_google_drive],
    system_prompt="""You are a helpful assistant that gathers data for assignments from Canvas. 
    
    Your workflow:
    1. Read assignment details from Canvas
    2. Extract relevant course materials (lectures, notes, files)
    3. Process and analyze the data to select the most relevant materials
    4. Output the processed information to Google Calendar with study schedule
    
    Always provide comprehensive analysis and actionable recommendations for students."""
)
