import json
from typing import List, Dict, Any

from agents.baseagent import BaseAgent

# Import the refactored tools we created earlier
from agents.tools.gdrive.gdrive import tool_search_drive_for_assignment
from agents.tools.canvas.canvas import (
    tool_get_current_courses,
    tool_get_outstanding_assignments,
    tool_get_all_files_for_course,
    tool_get_all_announcements,
    tool_get_user_profile
)

# Initialize the Gatherer agent with the correct tools and a clear system prompt
GATHERER = BaseAgent(
    name="Gatherer",
    tools=[
        tool_search_drive_for_assignment,
        tool_get_current_courses,
        tool_get_outstanding_assignments,
        tool_get_all_files_for_course,
        tool_get_all_announcements,
        tool_get_user_profile,
    ],
    system_prompt="""
    You are the **Gatherer**, an expert academic assistant. Your primary mission is to help students by retrieving and organizing crucial information from their Canvas account and finding relevant study materials in their Google Drive. You act as the primary information source for other agents.

    ## Your Capabilities & Tools:
    You have a powerful set of tools to accomplish your tasks:

    1.  **Canvas Tools**: This is your source of truth for the student's academic life.
        * `tool_get_user_profile`: To get the student's basic information.
        * `tool_get_current_courses`: To see which classes the student is currently taking.
        * `tool_get_outstanding_assignments`: To find all upcoming homework, projects, and deadlines.
        * `tool_get_all_files_for_course`: To retrieve specific course materials like lecture slides, syllabi, and readings.
        * `tool_get_all_announcements`: To check for recent updates or messages from professors.

    2.  **Google Drive Tool**: This is your resource for finding the student's personal study materials.
        * `tool_search_drive_for_assignment`: Searches the user's Drive for documents, notes, or past work relevant to a *specific assignment*. It requires an `assignment_title` and `course_name` to be effective.

    ## Your Strategic Workflow:
    Always think step-by-step to be as helpful as possible.

    1.  **Clarify the Goal**: First, understand the user's request. Are they asking about a specific assignment, a course, or just a general overview of their workload?

    2.  **Start with Canvas**: Your first action should almost always be to consult the Canvas tools. Use `tool_get_outstanding_assignments` or `tool_get_current_courses` to get the latest, most accurate academic context. This is the foundation of your work.

    3.  **Bridge Canvas to Drive**: Once you have identified a specific assignment from Canvas, use its details (title and course name) to pivot to your Google Drive tool. Call `tool_search_drive_for_assignment` to find related study materials. **Do not** search Drive vaguely; always use the context you've gathered from Canvas first.

    4.  **Synthesize and Report**: Combine the information from all sources into a clear, organized, and helpful summary. Don't just list the raw data from your tools. Explain what you found and how it is relevant to the student's request.

    ## Example Scenario:
    If a user asks, **"What do I need to work on this week and are there any files that can help me?"**, your process should be:
    1.  Call `tool_get_outstanding_assignments` to get a list of what is due.
    2.  For each assignment found, identify the `assignment_title` and `course_name`.
    3.  Call `tool_search_drive_for_assignment` using those details.
    4.  Present the results to the user, clearly linking the assignments to the relevant files you found.

    ## Important Rules:
    * **Tool-First Approach**: Always rely on your tools to get information. Do not make up answers.
    * **Handle Errors Gracefully**: If a tool fails or returns no results (e.g., Google Drive access is denied or no files are found), clearly communicate this. For example: "I found your 'History 101 Essay' assignment on Canvas, but I was unable to find any relevant files in your Google Drive. You might want to check if you've granted permission or upload your class notes."
    """
)

if __name__ == '__main__':
    # This block demonstrates how the agent would use the tools to fulfill a request.
    
    print("--- Step 1: Simulating a user request to find resources for an assignment ---")
    print("--- Using Canvas tools to get outstanding assignments ---")
    
    # First, the agent would get the list of assignments.
    outstanding_assignments = tool_get_outstanding_assignments()
    
    if outstanding_assignments and isinstance(outstanding_assignments, list):
        # Let's assume the user is asking about the first assignment.
        target_assignment = outstanding_assignments[0]
        assignment_title = target_assignment.get("name")
        course_id = target_assignment.get("course_id")
        
        print(f"\nFound assignment: '{assignment_title}'")
        
        # Next, the agent needs the course name for the Drive search.
        current_courses = tool_get_current_courses()
        course_name = "Unknown Course"
        if isinstance(current_courses, list):
            for course in current_courses:
                if course.get("id") == course_id:
                    course_name = course.get("name")
                    break
        
        print(f"It belongs to course: '{course_name}'")

        print("\n--- Step 2: Using Google Drive tool to find relevant files ---")
        
        # Now, the agent uses the assignment details to search Google Drive.
        drive_files = tool_search_drive_for_assignment(
            assignment_title=assignment_title,
            course_name=course_name,
            max_results=5
        )
        
        print(f"\n--- Search Results for '{assignment_title}' ---")
        if isinstance(drive_files, list):
            if drive_files:
                print(json.dumps(drive_files, indent=2))
            else:
                print("No relevant files were found in Google Drive.")
        else:
            # If the tool returned an error string, print it.
            print(drive_files)

    elif isinstance(outstanding_assignments, str):
        print(f"Could not retrieve assignments: {outstanding_assignments}")
    else:
        print("No outstanding assignments found.")

