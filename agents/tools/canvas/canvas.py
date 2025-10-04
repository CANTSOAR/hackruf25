import json
import datetime as dt
import re
from typing import List, Dict, Any, Optional
from agents.baseagent import *

# This ID will eventually be fetched from a database for the specific user.
USER_CANVAS_ID = 535680

def _clean_html(raw_html: str) -> str:
    """Removes HTML tags from a string."""
    if not isinstance(raw_html, str):
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

@tool
def load_data() -> Dict[str, Any]:
    """
    Loads the user's Canvas data export from a JSON file.

    Returns:
        A dictionary containing the parsed JSON data.
        Returns an empty dictionary if the file is not found or is invalid.
    """
    try:
        # NOTE: You may need to adjust this file path based on your project structure.
        with open(f"./canvas_extension/export_server/exports/canvas_export_{USER_CANVAS_ID}.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Export file for user {USER_CANVAS_ID} not found.")
        return {}
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from the export file.")
        return {}

@tool
def get_all_courses() -> List[Dict[str, Any]]:
    """
    Retrieves a list of all courses for the user.

    Returns:
        A list of dictionaries, where each dictionary represents a course
        with its most important fields.
    """
    data = load_data()
    course_list = []
    for course in data.get("courses", []):
        if course.get("name"): # Filter out courses without essential data
            course_list.append({
                "id": course.get("id"),
                "name": course.get("name"),
                "course_code": course.get("course_code"),
                "term": course.get("term", {})
            })
    return course_list

@tool
def get_current_courses() -> List[Dict[str, Any]]:
    """
    Retrieves courses that are currently active based on the term end date.

    Returns:
        A list of dictionaries for each active course.
    """
    all_courses = get_all_courses()
    current_courses = []
    now = dt.datetime.now(dt.timezone.utc)

    for course in all_courses:
        term_end_str = course.get("term", {}).get("end_at")
        if term_end_str:
            try:
                term_end_date = dt.datetime.strptime(term_end_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
                if term_end_date > now:
                    current_courses.append(course)
            except (ValueError, TypeError):
                # Ignore courses with invalid date formats
                continue
    return current_courses

@tool
def get_outstanding_assignments(course_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Gets all active assignments with a due date in the future.

    Args:
        course_id: If provided, filters assignments for only this course.

    Returns:
        A list of assignment dictionaries with key information.
    """
    data = load_data()
    outstanding = []
    now = dt.datetime.now(dt.timezone.utc)
    
    target_course_ids = [course['id'] for course in get_current_courses()]
    if course_id:
        if course_id in target_course_ids:
            target_course_ids = [course_id]
        else:
            return [] # The requested course is not active or doesn't exist

    for course in data.get("courses", []):
        if course.get("id") in target_course_ids:
            for assignment in course.get("assignments", []):
                due_at_str = assignment.get("due_at")
                if due_at_str:
                    try:
                        due_date = dt.datetime.strptime(due_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
                        if due_date > now:
                            outstanding.append({
                                "id": assignment.get("id"),
                                "name": assignment.get("name"),
                                "due_at": assignment.get("due_at"),
                                "points_possible": assignment.get("points_possible"),
                                "course_id": assignment.get("course_id"),
                                "html_url": assignment.get("html_url"),
                                "description": _clean_html(assignment.get("description", ""))
                            })
                    except (ValueError, TypeError):
                        continue
    return outstanding

@tool
def get_all_assignments_for_course(course_id: int) -> List[Dict[str, Any]]:
    """
    Gets all assignments for a specific course, regardless of due date.

    Args:
        course_id: The ID of the course to retrieve assignments from.

    Returns:
        A list of all assignment dictionaries for that course.
    """
    data = load_data()
    assignments = []
    for course in data.get("courses", []):
        if course.get("id") == course_id:
            for assignment in course.get("assignments", []):
                 assignments.append({
                    "id": assignment.get("id"),
                    "name": assignment.get("name"),
                    "due_at": assignment.get("due_at"),
                    "points_possible": assignment.get("points_possible"),
                    "course_id": assignment.get("course_id"),
                    "html_url": assignment.get("html_url"),
                    "description": _clean_html(assignment.get("description", ""))
                })
            break # Found the course, no need to continue
    return assignments

@tool
def get_all_files_for_course(course_id: int) -> List[Dict[str, Any]]:
    """
    Gets all files uploaded to a specific course.

    Args:
        course_id: The ID of the course.

    Returns:
        A list of file dictionaries with key information.
    """
    data = load_data()
    files = []
    for course in data.get("courses", []):
        if course.get("id") == course_id:
            for file_item in course.get("files", []):
                files.append({
                    "id": file_item.get("id"),
                    "display_name": file_item.get("display_name"),
                    "url": file_item.get("url"),
                    "content-type": file_item.get("content-type"),
                    "size": file_item.get("size"),
                    "modified_at": file_item.get("modified_at")
                })
            break
    return files

@tool
def get_all_announcements(course_id: int) -> List[Dict[str, Any]]:
    """
    Gets all announcements for a specific course.

    Args:
        course_id: The ID of the course.

    Returns:
        A list of announcement dictionaries with key information, sorted by most recent.
    """
    data = load_data()
    announcements = []
    
    for course in data.get("courses", []):
        if course.get("id") == course_id:
            for announcement in course.get("announcements", []):
                attachments_list = []
                for attachment in announcement.get("attachments", []):
                    attachments_list.append({
                        "id": attachment.get("id"),
                        "display_name": attachment.get("display_name"),
                        "url": attachment.get("url")
                    })

                announcements.append({
                    "id": announcement.get("id"),
                    "title": announcement.get("title"),
                    "message": _clean_html(announcement.get("message", "")),
                    "posted_at": announcement.get("posted_at"),
                    "read_state": announcement.get("read_state"),
                    "author_name": announcement.get("author", {}).get("display_name"),
                    "html_url": announcement.get("html_url"),
                    "course_id": course.get("id"),
                    "attachments": attachments_list
                })
            break # Found the course, no need to continue

    # Sort announcements by posted_at date, most recent first.
    announcements.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
    
    return announcements

if __name__ == '__main__':
    # Example usage of the functions
    print("--- Getting Current Courses ---")
    current_courses = get_current_courses()
    print(json.dumps(current_courses, indent=2))

    if current_courses:
        first_course_id = current_courses[0]['id']
        print(f"\n--- Getting Outstanding Assignments for Course ID: {first_course_id} ---")
        outstanding_assignments = get_outstanding_assignments(course_id=first_course_id)
        print(json.dumps(outstanding_assignments, indent=2))

        print(f"\n--- Getting All Files for Course ID: {first_course_id} ---")
        course_files = get_all_files_for_course(course_id=first_course_id)
        print(json.dumps(course_files, indent=2))

        print(f"\n--- Getting All Announcements for Course ID: {first_course_id} ---")
        course_announcements = get_all_announcements(course_id=first_course_id)
        print(json.dumps(course_announcements, indent=2))

    print("\n--- Getting All Outstanding Assignments from All Courses ---")
    all_outstanding = get_outstanding_assignments()
    print(json.dumps(all_outstanding, indent=2))

