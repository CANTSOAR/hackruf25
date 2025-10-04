#!/usr/bin/env python3
"""
Test script for the Canvas Data Gatherer Agent
This script demonstrates how to use the gatherer agent to process Canvas assignments
"""

import json
from agents.gatherer import gatherer

def test_gatherer_workflow():
    """Test the complete gatherer workflow"""
    
    print("=== Canvas Data Gatherer Agent Test ===\n")
    
    # Test 1: Read assignment data
    print("1. Reading Assignment Data...")
    print("-" * 40)
    
    # Mock assignment URL and course ID for testing
    assignment_url = "https://canvas.example.com/courses/123/assignments/456"
    course_id = "123"
    
    try:
        assignment_result = gatherer.run(f"Read assignment from {assignment_url} for course {course_id}")
        print("Assignment data retrieved successfully!")
        print(f"Result: {assignment_result}")
    except Exception as e:
        print(f"Error reading assignment: {e}")
        # Create mock assignment data for testing
        assignment_data = json.dumps({
            "assignment": {
                "id": "456",
                "name": "Machine Learning Project",
                "description": "Implement a machine learning algorithm for classification",
                "due_date": "2024-02-15T23:59:00Z",
                "points": 100,
                "course_id": "123",
                "course_name": "CS 101 - Introduction to Computer Science",
                "instructions": "Create a Python implementation of a classification algorithm. Include documentation and test cases.",
                "submission_types": ["online_upload"],
                "allowed_extensions": [".py", ".pdf", ".docx"]
            },
            "status": "success"
        })
        print("Using mock assignment data for testing...")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Read course files and materials
    print("2. Reading Course Materials...")
    print("-" * 40)
    
    try:
        materials_result = gatherer.run(f"Read all course files and materials for course {course_id}")
        print("Course materials retrieved successfully!")
        print(f"Result: {materials_result}")
    except Exception as e:
        print(f"Error reading materials: {e}")
        # Create mock materials data for testing
        materials_data = json.dumps({
            "materials": [
                {
                    "id": "1",
                    "name": "Introduction to Machine Learning",
                    "type": "lecture",
                    "url": "https://canvas.example.com/files/1",
                    "course_id": "123",
                    "description": "Basic concepts of machine learning",
                    "file_size": 1024,
                    "last_modified": "2024-01-15T10:00:00Z"
                },
                {
                    "id": "2",
                    "name": "Classification Algorithms Notes",
                    "type": "notes",
                    "url": "https://canvas.example.com/files/2",
                    "course_id": "123",
                    "description": "Detailed notes on classification algorithms",
                    "file_size": 2048,
                    "last_modified": "2024-01-20T14:30:00Z"
                },
                {
                    "id": "3",
                    "name": "Python Programming Guide",
                    "type": "document",
                    "url": "https://canvas.example.com/files/3",
                    "course_id": "123",
                    "description": "Python programming reference",
                    "file_size": 5120,
                    "last_modified": "2024-01-10T09:15:00Z"
                }
            ],
            "total_count": 3,
            "status": "success"
        })
        print("Using mock materials data for testing...")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Process assignment data
    print("3. Processing Assignment Data...")
    print("-" * 40)
    
    try:
        # Use mock data if API calls failed
        if 'assignment_data' not in locals():
            assignment_data = json.dumps({
                "assignment": {
                    "id": "456",
                    "name": "Machine Learning Project",
                    "description": "Implement a machine learning algorithm for classification",
                    "due_date": "2024-02-15T23:59:00Z",
                    "points": 100,
                    "course_id": "123",
                    "course_name": "CS 101 - Introduction to Computer Science",
                    "instructions": "Create a Python implementation of a classification algorithm. Include documentation and test cases.",
                    "submission_types": ["online_upload"],
                    "allowed_extensions": [".py", ".pdf", ".docx"]
                },
                "status": "success"
            })
        
        if 'materials_data' not in locals():
            materials_data = json.dumps({
                "materials": [
                    {
                        "id": "1",
                        "name": "Introduction to Machine Learning",
                        "type": "lecture",
                        "url": "https://canvas.example.com/files/1",
                        "course_id": "123",
                        "description": "Basic concepts of machine learning",
                        "file_size": 1024,
                        "last_modified": "2024-01-15T10:00:00Z"
                    },
                    {
                        "id": "2",
                        "name": "Classification Algorithms Notes",
                        "type": "notes",
                        "url": "https://canvas.example.com/files/2",
                        "course_id": "123",
                        "description": "Detailed notes on classification algorithms",
                        "file_size": 2048,
                        "last_modified": "2024-01-20T14:30:00Z"
                    }
                ],
                "total_count": 2,
                "status": "success"
            })
        
        processed_result = gatherer.run(f"Process assignment data: {assignment_data} and materials data: {materials_data}")
        print("Assignment data processed successfully!")
        print(f"Result: {processed_result}")
        
    except Exception as e:
        print(f"Error processing data: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Output to Google Calendar
    print("4. Outputting to Google Calendar...")
    print("-" * 40)
    
    try:
        # Create mock processed data
        processed_data = json.dumps({
            "assignment": {
                "id": "456",
                "name": "Machine Learning Project",
                "course_name": "CS 101 - Introduction to Computer Science",
                "points": 100,
                "due_date": "2024-02-15T23:59:00Z",
                "instructions": "Create a Python implementation of a classification algorithm. Include documentation and test cases."
            },
            "priority_level": 1,
            "estimated_time": 10,
            "study_plan": [
                "Review Introduction to Machine Learning (highest relevance)",
                "Study Classification Algorithms Notes (secondary material)",
                "Read assignment instructions carefully",
                "Create outline or draft",
                "Review rubric if available",
                "Start working on assignment"
            ],
            "relevant_materials": [
                {
                    "name": "Introduction to Machine Learning",
                    "type": "lecture"
                },
                {
                    "name": "Classification Algorithms Notes",
                    "type": "notes"
                }
            ],
            "suggested_schedule": {
                "start_date": "2024-02-01T09:00:00Z",
                "due_date": "2024-02-15T23:59:00Z"
            },
            "status": "success"
        })
        
        calendar_result = gatherer.run(f"Output processed data to Google Calendar: {processed_data}")
        print("Calendar event created successfully!")
        print(f"Result: {calendar_result}")
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 5: Complete workflow
    print("5. Complete Workflow Test...")
    print("-" * 40)
    
    try:
        complete_workflow = gatherer.run("""
        I need help with a Canvas assignment. Please:
        1. Read the assignment details from https://canvas.example.com/courses/123/assignments/456
        2. Extract all relevant course materials for course 123
        3. Process the data to find the most relevant materials
        4. Create a study schedule and output to Google Calendar
        
        The assignment is about machine learning classification and is due in 2 weeks.
        """)
        
        print("Complete workflow executed successfully!")
        print(f"Result: {complete_workflow}")
        
    except Exception as e:
        print(f"Error in complete workflow: {e}")
    
    print("\n" + "="*60)
    print("GATHERER AGENT TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_gatherer_workflow()
