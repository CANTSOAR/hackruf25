import os.path
import datetime
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.baseagent import *

# Scope for full read/write access to calendars
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Gets an authorized Google Calendar service object."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ensure your credentials file is named correctly
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def list_calendars(service):
    """(Function 1) Lists all of the user's calendars."""
    print("Getting the list of calendars...")
    try:
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get("items", [])
        if not calendars:
            print("No calendars found.")
            return
        print("Your calendars:")
        for calendar in calendars:
            summary = calendar["summary"]
            cal_id = calendar["id"]
            print(f"- {summary} (ID: {cal_id})")
    except HttpError as error:
        print(f"An error occurred: {error}")

def list_events(service, calendar_id='primary'):
    """(Function 2) Lists the next 10 upcoming events on a specific calendar."""
    print(f"\nGetting upcoming events from calendar: {calendar_id}")
    try:
        # 'Z' indicates UTC time
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        print("Upcoming events:")
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"- {start} | {event['summary']}")

    except HttpError as error:
        print(f"An error occurred: {error}")

def create_event(service, calendar_id, summary, start_time, end_time):
    """(Function 3) Creates a new event at a specific time."""
    print(f"\nCreating event on calendar: {calendar_id}...")
    
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': str(start_time.tzinfo),
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': str(end_time.tzinfo),
        },
    }
    
    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Event created successfully!")
        print(f"View it here: {created_event.get('htmlLink')}")
    except HttpError as error:
        print(f"An error occurred: {error}")

def create_calendar(service, summary, time_zone='America/New_York'):
    """(Function 4) Creates a new calendar."""
    print(f"\nCreating a new calendar named '{summary}'...")
    calendar_body = {
        'summary': summary,
        'timeZone': time_zone
    }
    try:
        created_calendar = service.calendars().insert(body=calendar_body).execute()
        print("Calendar created successfully!")
        print(f"  ID: {created_calendar['id']}")
        print(f"  Summary: {created_calendar['summary']}")
    except HttpError as error:
        print(f"An error occurred: {error}")

@tool
def tool_list_calendars():
    """
    This tool is used to get the available google calendars of the user, so that you can choose which ones to interact with later.
    If there are errors, communicate that with the orchestrator.
    """
    try:
        service = get_calendar_service()

        if service:
            return list_calendars(service)
        else:
            raise(Exception("Google Calendar Service not enabled, please ask user to enable"))
        
    except Exception as e:
        return f"Error with listing google calendars: {e}"
    
@tool
def tool_list_events(calendar_id: str = "primary"):
    """
    This tool is used to pull all the events from a specific calendar. You can use this to get context from the calendar and see what already exists.
    If there are errors, communicate that with the orchestrator.
    """
    try:
        service = get_calendar_service()

        if service:
            return list_events(service, calendar_id = calendar_id)
        else:
            raise(Exception("Google Calendar Service not enabled, please ask user to enable"))
        
    except Exception as e:
        return f"Error with listing google events on calendar {calendar_id}: {e}"
    
@tool
def tool_create_event(calendar_id, event_summary, start, end):
    """
    This tool is used to create an event on a calendar. You can use this to schedule in new events and allocate time to ojbectives.
    If there are errors, communicate that with the orchestrator.
    """
    try:
        service = get_calendar_service()

        if service:
            return create_event(service, calendar_id, event_summary, start, end)
        else:
            raise(Exception("Google Calendar Service not enabled, please ask user to enable"))
        
    except Exception as e:
        return f"Error with creating event on calendar {calendar_id}: {e}"
    
@tool
def tool_create_calendar(calendar_summary: str, time_zone: str = "America/New_York"):
    """
    This tool is used to create a whole new calendar for the user. You can use this to create a brand new calendar if needed, but this should be used sparingly.
    If there are errors, communicate that with the orchestrator.
    """
    try:
        service = get_calendar_service()

        if service:
            return create_calendar(service, calendar_summary, time_zone)
        else:
            raise(Exception("Google Calendar Service not enabled, please ask user to enable"))
        
    except Exception as e:
        return f"Error with creating calendar {calendar_summary}: {e}"

if __name__ == "__main__":
    service = get_calendar_service()
    if service:
        # --- 1. READ ALL AVAILABLE CALENDARS ---
        list_calendars(service)
        
        # --- 2. READ ALL EVENTS ON A SPECIFIC CALENDAR ---
        # Using 'primary' for the user's main calendar
        list_events(service, calendar_id='primary')
        
        # --- 3. CREATE A NEW EVENT AT A SPECIFIC TIME ---
        # Define the event details
        event_summary = "Team Meeting about Project X"
        
        # Set the timezone (e.g., Eastern Time)
        tz = ZoneInfo("America/New_York")
        
        # Define start and end time with timezone information
        start = datetime.datetime(2025, 10, 28, 10, 0, 0, tzinfo=tz)
        end = datetime.datetime(2025, 10, 28, 11, 0, 0, tzinfo=tz)
        
        create_event(service, 'primary', event_summary, start, end)