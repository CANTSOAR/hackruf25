#!/usr/bin/env python3
"""
Example usage of the Canvas Data Gatherer Agent
This shows how to use the gatherer agent in a real application
"""

from agents.gatherer import gatherer
import json

def example_usage():
    """Example of how to use the gatherer agent"""
    
    print("Canvas Data Gatherer Agent - Example Usage")
    print("=" * 50)
    
    # Example 1: Simple assignment processing
    print("\n1. Processing a single assignment:")
    print("-" * 30)
    
    result = gatherer.run("""
    I have a Canvas assignment due next week. The assignment URL is:
    https://canvas.university.edu/courses/12345/assignments/67890
    
    Please help me:
    1. Read the assignment details
    2. Find relevant course materials
    3. Create a study plan
    4. Add it to my Google Calendar
    """)
    
    print("Result:", result)
    
    # Example 2: Batch processing multiple assignments
    print("\n\n2. Processing multiple assignments:")
    print("-" * 30)
    
    result = gatherer.run("""
    I have several assignments due this month:
    - Math homework due in 3 days (course 111)
    - English essay due in 1 week (course 222)
    - Science project due in 2 weeks (course 333)
    
    Please process all of them and create a comprehensive study schedule.
    """)
    
    print("Result:", result)
    
    # Example 3: Priority-based processing
    print("\n\n3. Priority-based assignment processing:")
    print("-" * 30)
    
    result = gatherer.run("""
    I need to prioritize my assignments based on:
    - Due dates (sooner = higher priority)
    - Point values (more points = higher priority)
    - Difficulty level (harder = more time needed)
    
    Process my assignments and create a priority-based study schedule.
    """)
    
    print("Result:", result)

if __name__ == "__main__":
    example_usage()
