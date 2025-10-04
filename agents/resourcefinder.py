"""
ResourceFinder Agent

This agent finds relevant Google Drive documents and resources that help students
understand and complete assignments. It runs after the Gatherer agent and takes
assignment objects as input.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain_core.tools import tool
from dotenv import load_dotenv
from .baseagent import BaseAgent
from .tools.drive.drive_auth import DriveAuthHandler
from .tools.drive.drive_search import search_drive_for_assignment

load_dotenv()

@dataclass
class Assignment:
    """Data class for assignments from Gatherer agent"""
    title: str
    description: str
    course: str
    due_date: str
    attachments: List[str] = None

@dataclass
class ResourceResult:
    """Data class for resource search results"""
    file_id: str
    name: str
    mime_type: str
    web_view_link: str
    snippet: str
    relevance_score: float
    why_useful: str

class ResourceFinderAgent:
    """Agent that finds relevant Google Drive resources for assignments"""
    
    def __init__(self):
        self.name = "ResourceFinder"
        self.drive_auth = DriveAuthHandler()
        self.service = None
        
    def authenticate_drive(self) -> Dict[str, Any]:
        """Authenticate with Google Drive API"""
        try:
            success = self.drive_auth.authenticate()
            if success:
                self.service = self.drive_auth.get_service()
                return {"success": True, "message": "Drive authentication successful"}
            else:
                return {"success": False, "message": "Drive authentication failed"}
        except Exception as e:
            return {"success": False, "message": f"Drive authentication error: {e}"}
    
    def extract_keywords_from_assignment(self, assignment: Assignment) -> List[str]:
        """
        Extract relevant keywords from assignment using LLM
        
        Args:
            assignment: Assignment object from Gatherer
            
        Returns:
            List of relevant keywords for searching
        """
        # This would typically use an LLM to extract keywords
        # For MVP, we'll use simple keyword extraction
        
        keywords = []
        
        # Extract from title
        title_words = assignment.title.lower().split()
        keywords.extend([word.strip('.,!?;:"') for word in title_words if len(word) > 3])
        
        # Extract from description
        desc_words = assignment.description.lower().split()
        keywords.extend([word.strip('.,!?;:"') for word in desc_words if len(word) > 3])
        
        # Add course name
        if assignment.course:
            keywords.append(assignment.course.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'use', 'using', 'provide', 'analysis'
        }
        
        keywords = [kw for kw in keywords if kw not in stop_words and len(kw) > 2]
        
        # Remove duplicates and limit
        return list(set(keywords))[:15]
    
    def find_resources(self, assignment_data: Dict[str, Any], max_results: int = 5) -> Dict[str, Any]:
        """
        Find relevant Drive resources for an assignment
        
        Args:
            assignment_data: Assignment information from Gatherer
            max_results: Maximum number of results to return
            
        Returns:
            JSON response with found resources
        """
        assignment_id = str(uuid.uuid4())[:8]  # Generate short ID
        
        try:
            # Check if Drive is authenticated
            if not self.service:
                auth_result = self.authenticate_drive()
                if not auth_result["success"]:
                    return {
                        "assignment_id": assignment_id,
                        "results": [],
                        "notes": f"Google Drive access not available: {auth_result['message']}. Please either: 1) Grant Drive permissions, 2) Share a specific Drive folder, or 3) Upload relevant files directly."
                    }
            
            # Convert assignment data to Assignment object
            assignment = Assignment(
                title=assignment_data.get('title', ''),
                description=assignment_data.get('description', ''),
                course=assignment_data.get('course', ''),
                due_date=assignment_data.get('due_date', ''),
                attachments=assignment_data.get('attachments', [])
            )
            
            # Search for relevant files
            results = search_drive_for_assignment(
                self.service, 
                assignment_data, 
                max_results=max_results
            )
            
            # Generate notes
            notes = []
            if not results:
                notes.append("No relevant files found in your Google Drive. Consider uploading course materials or sharing a specific folder.")
            elif len(results) < max_results:
                notes.append(f"Found {len(results)} relevant files. You might want to upload more course materials for better coverage.")
            else:
                notes.append(f"Found {len(results)} highly relevant files from your Drive.")
            
            return {
                "assignment_id": assignment_id,
                "results": results,
                "notes": " ".join(notes)
            }
            
        except Exception as e:
            return {
                "assignment_id": assignment_id,
                "results": [],
                "notes": f"Error searching Drive resources: {str(e)}. Please check your Drive permissions or try uploading files directly."
            }
    
    def handle_fallback(self, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle fallback when Drive access is not available
        
        Args:
            assignment_data: Assignment information
            
        Returns:
            Fallback response with suggestions
        """
        assignment_id = str(uuid.uuid4())[:8]
        
        # Generate helpful suggestions based on assignment
        suggestions = []
        
        title = assignment_data.get('title', '').lower()
        description = assignment_data.get('description', '').lower()
        course = assignment_data.get('course', '')
        
        if 'data' in title or 'analysis' in title:
            suggestions.extend([
                "Upload your dataset files (CSV, Excel, etc.)",
                "Share any data analysis templates or examples",
                "Include any relevant research papers or documentation"
            ])
        
        if 'report' in title or 'essay' in title:
            suggestions.extend([
                "Upload assignment templates or rubrics",
                "Share relevant research materials",
                "Include any writing guides or examples"
            ])
        
        if course:
            suggestions.append(f"Upload {course} course materials, lecture notes, or readings")
        
        return {
            "assignment_id": assignment_id,
            "results": [],
            "notes": f"Google Drive access not available. For this {assignment_data.get('title', 'assignment')}, consider: {'; '.join(suggestions[:3])}. You can upload files directly or share a Drive folder link.",
            "fallback_suggestions": suggestions
        }

# Tool functions for LangChain integration
@tool
def find_drive_resources(assignment_data: str) -> str:
    """
    Find relevant Google Drive resources for an assignment.
    
    Args:
        assignment_data: JSON string containing assignment information from Gatherer
        
    Returns:
        JSON string with found resources and relevance scores
    """
    try:
        # Parse assignment data
        assignment_json = json.loads(assignment_data)
        
        # Initialize ResourceFinder
        finder = ResourceFinderAgent()
        
        # Try to find resources
        result = finder.find_resources(assignment_json, max_results=5)
        
        return json.dumps(result)
        
    except json.JSONDecodeError:
        return json.dumps({
            "assignment_id": "error",
            "results": [],
            "notes": "Invalid assignment data format. Expected JSON string."
        })
    except Exception as e:
        return json.dumps({
            "assignment_id": "error", 
            "results": [],
            "notes": f"Error finding resources: {str(e)}"
        })

@tool
def check_drive_access() -> str:
    """
    Check if Google Drive access is available and test connection.
    
    Returns:
        JSON string with connection status and user info
    """
    try:
        finder = ResourceFinderAgent()
        auth_result = finder.authenticate_drive()
        
        if auth_result["success"]:
            # Test connection
            test_result = finder.drive_auth.test_connection()
            return json.dumps(test_result)
        else:
            return json.dumps({
                "success": False,
                "error": auth_result["message"],
                "user_email": None,
                "user_name": None
            })
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Drive access check failed: {str(e)}",
            "user_email": None,
            "user_name": None
        })

@tool
def suggest_fallback_resources(assignment_data: str) -> str:
    """
    Provide fallback suggestions when Drive access is not available.
    
    Args:
        assignment_data: JSON string containing assignment information
        
    Returns:
        JSON string with fallback suggestions
    """
    try:
        assignment_json = json.loads(assignment_data)
        finder = ResourceFinderAgent()
        
        result = finder.handle_fallback(assignment_json)
        return json.dumps(result)
        
    except json.JSONDecodeError:
        return json.dumps({
            "assignment_id": "error",
            "results": [],
            "notes": "Invalid assignment data format."
        })
    except Exception as e:
        return json.dumps({
            "assignment_id": "error",
            "results": [],
            "notes": f"Error generating fallback suggestions: {str(e)}"
        })

# Initialize the ResourceFinder agent
resourcefinder = BaseAgent(
    name="ResourceFinder",
    tools=[find_drive_resources, check_drive_access, suggest_fallback_resources],
    system_prompt="""You are a helpful assistant that finds relevant Google Drive documents and resources to help students complete their assignments.

Your workflow:
1. Take assignment data from the Gatherer agent (title, description, course, due date, attachments)
2. Search the student's Google Drive for relevant documents and files
3. Extract content snippets and calculate relevance scores
4. Return the top N most relevant resources with explanations of why they're useful
5. If Drive access is unavailable, provide helpful fallback suggestions

Key capabilities:
- Search Google Drive using intelligent keyword extraction
- Extract text content from Google Docs, PDFs, and other file types
- Calculate relevance scores based on content matching and metadata
- Generate helpful explanations of why each resource is useful
- Handle authentication and permission issues gracefully
- Provide fallback suggestions when Drive access is unavailable

Always prioritize student privacy and require explicit consent for Drive access. Provide clear explanations of why each resource is helpful for the specific assignment."""
)

if __name__ == "__main__":
    # Test the ResourceFinder agent
    test_assignment = {
        "title": "Data101 Homework 3 - Medicare Data Analysis",
        "description": "Use the provided Medicare dataset and analyze the relationship between patient age and claim amounts. Provide summary statistics and make two visualizations. Deliver a 2 page report and a reproducible Jupyter notebook.",
        "course": "Data101",
        "due_date": "2025-10-11",
        "attachments": []
    }
    
    # Test the agent
    result = resourcefinder.run(f"""
    Please find relevant Google Drive resources for this assignment:
    {json.dumps(test_assignment)}
    """)
    
    print("ResourceFinder Test Result:")
    print(result)
