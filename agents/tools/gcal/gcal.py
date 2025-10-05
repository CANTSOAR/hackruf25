import os.path
import datetime
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.baseagent import *

# This scope allows for full read, edit, and creation access.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarManager:
    """A manager to handle all Google Calendar API interactions."""
    
    def __init__(self):
        """Initializes the manager and authorizes the Google Calendar service."""
        self.service = self._get_service()
        if not self.service:
            raise Exception("Failed to initialize Google Calendar service.")

    def _get_service(self):
        """Gets an authorized Google Calendar service object."""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}. Re-authenticating.")
                    creds = None # Force re-authentication
            
            if not creds:
                # Ensure your credentials file is named correctly
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())
        
        try:
            return build("calendar", "v3", credentials=creds)
        except HttpError as error:
            print(f"An error occurred building the service: {error}")
            return None

    def list_calendars(self):
        """Returns a list of the user's calendars."""
        try:
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])
            if not calendars:
                return "No calendars found."

            # Format for agent-friendly output
            return [
                {"summary": cal["summary"], "id": cal["id"]} for cal in calendars
            ]
        except HttpError as error:
            return f"An error occurred while listing calendars: {error}"

    def list_events(self, calendar_id: str = 'primary', max_results: int = 10):
        """Returns upcoming events from a specific calendar."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            if not events:
                return f"No upcoming events found on calendar '{calendar_id}'."

            # Format for agent-friendly output
            event_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list.append(f"'{event['summary']}' at '{start}'")
            return event_list
        except HttpError as error:
            return f"An error occurred while listing events: {error}"

    def create_event(self, calendar_id: str, summary: str, start_time: datetime.datetime, end_time: datetime.datetime):
        """Creates an event on a specified calendar and returns its link."""
        if not start_time.tzinfo or not end_time.tzinfo:
            raise ValueError("Start and end times must be timezone-aware.")

        event = {
            'summary': summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': str(start_time.tzinfo)},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': str(end_time.tzinfo)},
        }
        
        try:
            created_event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            link = created_event.get('htmlLink')
            return f"Event '{summary}' created successfully. View it here: {link}"
        except HttpError as error:
            return f"An error occurred while creating the event: {error}"

    def create_calendar(self, summary: str, time_zone: str = 'America/New_York'):
        """Creates a new calendar and returns its details."""
        calendar_body = {'summary': summary, 'timeZone': time_zone}
        try:
            created_calendar = self.service.calendars().insert(body=calendar_body).execute()
            return {
                "message": "Calendar created successfully!",
                "id": created_calendar['id'],
                "summary": created_calendar['summary']
            }
        except HttpError as error:
            return f"An error occurred while creating the calendar: {error}"

# --- Agent Tools ---

@tool
def tool_list_calendars():
    """
    This tool gets the available Google Calendars for the user, so you can choose which one to interact with.
    Returns a list of calendar objects, each with a 'summary' and 'id'.
    """
    try:
        manager = GoogleCalendarManager()
        return manager.list_calendars()
    except Exception as e:
        return f"Error listing Google Calendars: {e}. Ask the user to authorize access if needed."
    
@tool
def tool_list_events(calendar_id: str = "primary"):
    """
    This tool pulls upcoming events from a specific calendar to get context on what already exists.
    Use a calendar ID from 'tool_list_calendars' or 'primary' for the default calendar.
    """
    try:
        manager = GoogleCalendarManager()
        return manager.list_events(calendar_id=calendar_id)
    except Exception as e:
        return f"Error listing events on calendar '{calendar_id}': {e}."
    
@tool
def tool_create_event(calendar_id: str, event_summary: str, start_time: datetime.datetime, end_time: datetime.datetime):
    """
    This tool creates an event on a calendar to schedule new items.
    The start_time and end_time must be timezone-aware datetime objects.
    """
    try:
        manager = GoogleCalendarManager()
        return manager.create_event(calendar_id, event_summary, start_time, end_time)
    except Exception as e:
        return f"Error creating event on calendar '{calendar_id}': {e}."
    
@tool
def tool_create_calendar(calendar_summary: str, time_zone: str = "America/New_York"):
    """
    This tool creates a new calendar. Use this sparingly, only when a new, separate calendar is explicitly needed.
    """
    try:
        manager = GoogleCalendarManager()
        return manager.create_calendar(calendar_summary, time_zone)
    except Exception as e:
        return f"Error creating calendar '{calendar_summary}': {e}."

if __name__ == "__main__":
    # Example usage of the manager class
    print("--- Initializing Google Calendar Manager ---")
    try:
        calendar_manager = GoogleCalendarManager()
        print("Service initialized successfully.\n")

        # --- 1. List all available calendars ---
        print("--- Listing Calendars ---")
        my_calendars = calendar_manager.list_calendars()
        print(my_calendars)
        print("-" * 20)

        # --- 2. List upcoming events on the primary calendar ---
        print("\n--- Listing Upcoming Events (Primary Calendar) ---")
        upcoming_events = calendar_manager.list_events(calendar_id='primary')
        print(upcoming_events)
        print("-" * 20)

        # --- 3. Create a new event ---
        print("\n--- Creating a New Event ---")
        tz = ZoneInfo("America/New_York")
        start = datetime.datetime(2025, 11, 5, 14, 0, 0, tzinfo=tz) # Nov 5, 2025 @ 2:00 PM ET
        end = datetime.datetime(2025, 11, 5, 15, 0, 0, tzinfo=tz)   # Nov 5, 2025 @ 3:00 PM ET
        
        result = calendar_manager.create_event(
            calendar_id='primary', 
            summary="Review Q4 Agent Performance", 
            start_time=start, 
            end_time=end
        )
        print(result)
        print("-" * 20)

        # --- 4. Create a new calendar ---
        # print("\n--- Creating a New Calendar ---")
        # new_cal_result = calendar_manager.create_calendar(summary="Agent Test Calendar")
        # print(new_cal_result)
        # print("-" * 20)
        
    except Exception as e:
        print(f"An error occurred during execution: {e}")