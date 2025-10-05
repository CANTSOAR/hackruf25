import json
import datetime as dt
import re
from typing import List, Dict, Any, Optional

from agents.baseagent import *

# This ID would typically be fetched based on the authenticated user.
USER_CANVAS_ID = 535680

class CanvasDataManager:
    """Manages loading and querying a user's Canvas data export."""

    def __init__(self, user_id: int):
        """
        Initializes the manager and loads the user's data from the JSON file.
        
        Args:
            user_id: The ID of the user whose data export should be loaded.
        """
        self.user_id = user_id
        self.data = self._load_data()
        if not self.data:
            raise FileNotFoundError(f"Could not load or parse data for user {self.user_id}")

    def _load_data(self) -> Dict[str, Any]:
        """Loads and parses the Canvas data from a JSON file."""
        try:
            # NOTE: Adjust this file path if your project structure is different.
            file_path = f"./canvas_extension/export_server/exports/canvas_export_{self.user_id}.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Export file for user {self.user_id} not found at {file_path}.")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from the export file for user {self.user_id}.")
            return {}
            
    @staticmethod
    def _clean_html(raw_html: str) -> str:
        """A static method to remove HTML tags from a string."""
        if not isinstance(raw_html, str):
            return ""
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def get_user_profile(self) -> Dict[str, Any]:
        """Retrieves the user's profile information from the data."""
        profile = self.data.get("profile", {})
        return {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "primary_email": profile.get("primary_email"),
            "bio": profile.get("bio")
        }

    def get_all_courses(self) -> List[Dict[str, Any]]:
        """Retrieves a list of all courses for the user."""
        course_list = []
        for course in self.data.get("courses", []):
            if course.get("name"): # Filter out courses without essential data
                course_list.append({
                    "id": course.get("id"),
                    "name": course.get("name"),
                    "course_code": course.get("course_code"),
                    "term": course.get("term", {})
                })
        return course_list

    def get_current_courses(self) -> List[Dict[str, Any]]:
        """Retrieves courses that are currently active based on the term end date."""
        all_courses = self.get_all_courses()
        current_courses = []
        now = dt.datetime.now(dt.timezone.utc)

        for course in all_courses:
            term_end_str = course.get("term", {}).get("end_at")
            if term_end_str:
                try:
                    term_end_date = dt.datetime.fromisoformat(term_end_str.replace('Z', '+00:00'))
                    if term_end_date > now:
                        current_courses.append(course)
                except (ValueError, TypeError):
                    continue
        return current_courses

    def get_outstanding_assignments(self, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Gets all active assignments with a due date in the future."""
        outstanding = []
        now = dt.datetime.now(dt.timezone.utc)
        
        current_course_ids = [course['id'] for course in self.get_current_courses()]
        target_course_ids = current_course_ids
        
        if course_id:
            if course_id in current_course_ids:
                target_course_ids = [course_id]
            else:
                return [] # The requested course is not active or doesn't exist

        for course in self.data.get("courses", []):
            if course.get("id") in target_course_ids:
                for assignment in course.get("assignments", []):
                    due_at_str = assignment.get("due_at")
                    if due_at_str:
                        try:
                            due_date = dt.datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
                            if due_date > now:
                                outstanding.append({
                                    "id": assignment.get("id"),
                                    "name": assignment.get("name"),
                                    "due_at": due_at_str,
                                    "course_id": assignment.get("course_id"),
                                    "html_url": assignment.get("html_url"),
                                    "description": self._clean_html(assignment.get("description", ""))
                                })
                        except (ValueError, TypeError):
                            continue
        return outstanding

    def get_all_files_for_course(self, course_id: int) -> List[Dict[str, Any]]:
        """Gets all files uploaded to a specific course."""
        files = []
        for course in self.data.get("courses", []):
            if course.get("id") == course_id:
                for file_item in course.get("files", []):
                    files.append({
                        "id": file_item.get("id"),
                        "display_name": file_item.get("display_name"),
                        "url": file_item.get("url"),
                        "modified_at": file_item.get("modified_at")
                    })
                return files # Found the course, no need to continue
        return files # Return empty list if course_id not found

    def get_all_announcements(self, course_id: int) -> List[Dict[str, Any]]:
        """Gets all announcements for a specific course, sorted by most recent."""
        announcements = []
        for course in self.data.get("courses", []):
            if course.get("id") == course_id:
                for ann in course.get("announcements", []):
                    announcements.append({
                        "id": ann.get("id"),
                        "title": ann.get("title"),
                        "message": self._clean_html(ann.get("message", "")),
                        "posted_at": ann.get("posted_at"),
                        "html_url": ann.get("html_url"),
                    })
                # Sort announcements by posted_at date, most recent first.
                announcements.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
                return announcements
        return announcements

# --- Agent Tools ---

@tool
def tool_get_user_profile() -> Dict[str, Any]:
    """
    Retrieves the user's profile information, including name, email, and bio.
    """
    try:
        manager = CanvasDataManager(USER_CANVAS_ID)
        return manager.get_user_profile()
    except Exception as e:
        return f"Error getting user profile: {e}"

@tool
def tool_get_current_courses() -> List[Dict[str, Any]]:
    """
    Retrieves a list of all currently active courses for the user.
    This is useful for finding out which courses to query for assignments or files.
    """
    try:
        manager = CanvasDataManager(USER_CANVAS_ID)
        return manager.get_current_courses()
    except Exception as e:
        return f"Error getting current courses: {e}"

@tool
def tool_get_outstanding_assignments(course_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Gets all upcoming assignments that have not passed their due date.
    Args:
        course_id (Optional[int]): If provided, filters assignments for only that course. 
                                   If omitted, gets outstanding assignments from ALL active courses.
    """
    try:
        manager = CanvasDataManager(USER_CANVAS_ID)
        return manager.get_outstanding_assignments(course_id)
    except Exception as e:
        return f"Error getting outstanding assignments: {e}"

@tool
def tool_get_all_files_for_course(course_id: int) -> List[Dict[str, Any]]:
    """
    Gets a list of all files uploaded to a specific course.
    Args:
        course_id (int): The ID of the course to retrieve files from. Get the ID from 'tool_get_current_courses'.
    """
    try:
        manager = CanvasDataManager(USER_CANVAS_ID)
        return manager.get_all_files_for_course(course_id)
    except Exception as e:
        return f"Error getting files for course {course_id}: {e}"

@tool
def tool_get_all_announcements(course_id: int) -> List[Dict[str, Any]]:
    """
    Gets all announcements for a specific course, sorted with the most recent first.
    Args:
        course_id (int): The ID of the course to retrieve announcements from. Get the ID from 'tool_get_current_courses'.
    """
    try:
        manager = CanvasDataManager(USER_CANVAS_ID)
        return manager.get_all_announcements(course_id)
    except Exception as e:
        return f"Error getting announcements for course {course_id}: {e}"


if __name__ == '__main__':
    # Example usage of the new CanvasDataManager class
    try:
        print("--- Initializing Canvas Data Manager ---")
        manager = CanvasDataManager(USER_CANVAS_ID)
        print("Manager initialized successfully.\n")

        print("--- Getting User Profile ---")
        user_profile = manager.get_user_profile()
        print(json.dumps(user_profile, indent=2))

        print("\n--- Getting Current Courses ---")
        current_courses = manager.get_current_courses()
        print(json.dumps(current_courses, indent=2))

        if current_courses:
            # Use the first course for more detailed examples
            first_course_id = current_courses[0]['id']
            print(f"\n--- Getting Outstanding Assignments for Course ID: {first_course_id} ---")
            outstanding = manager.get_outstanding_assignments(course_id=first_course_id)
            print(json.dumps(outstanding, indent=2))

            print(f"\n--- Getting All Files for Course ID: {first_course_id} ---")
            files = manager.get_all_files_for_course(course_id=first_course_id)
            print(json.dumps(files, indent=2))

            print(f"\n--- Getting All Announcements for Course ID: {first_course_id} ---")
            announcements = manager.get_all_announcements(course_id=first_course_id)
            print(json.dumps(announcements, indent=2))

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

