import os
import json
import datetime
from datetime import timedelta
from typing import List, Dict, Any, Optional, Tuple
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.baseagent import *

# Scopes include full calendar access to create events and list them.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

DEFAULT_TIMEZONE = "America/New_York"
TZ = ZoneInfo(DEFAULT_TIMEZONE)

class GoogleCalendarManager:
    """
    Extended calendar manager matching the Scheduler spec:
    - list_events(calendar_id, start, end) returns all events in timeframe (structured)
    - create_event(..., description) supports folder link attachment
    - schedule_assignments_batch supports intelligent defaults, non-conflicting scheduling,
      multiple exam prep sessions, and returns machine-parseable results (per assignment).
    """

    def __init__(self, token_file: str = "./token.json", credentials_file: str = "./credentials.json"):
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.service = self._get_service()
        if not self.service:
            raise Exception("Failed to initialize Google Calendar service.")

    def _get_service(self):
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}. Re-authenticating.")
                    creds = None
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Google Calendar credentials not found at: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
        try:
            return build("calendar", "v3", credentials=creds)
        except HttpError as e:
            print(f"Error building calendar service: {e}")
            return None

    # -------------------------
    # Basic calendar helpers
    # -------------------------
    def list_events(self, calendar_id: str = "primary", time_min: Optional[datetime.datetime] = None, time_max: Optional[datetime.datetime] = None, max_results: int = 2500) -> Dict[str, Any]:
        """
        Returns all events between time_min and time_max (both timezone-aware datetimes).
        Output format:
        {"status":"ok", "events":[{id, summary, start, end, htmlLink, description}], "calendar_id": ...}
        """
        if time_min is None:
            time_min = datetime.datetime.now(TZ)
        if time_max is None:
            time_max = time_min + timedelta(days=30)

        if not time_min.tzinfo or not time_max.tzinfo:
            raise ValueError("time_min and time_max must be timezone-aware datetimes.")

        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=max_results
            ).execute()
            items = events_result.get("items", [])
            events = []
            for e in items:
                start = e["start"].get("dateTime", e["start"].get("date"))
                end = e["end"].get("dateTime", e["end"].get("date"))
                events.append({
                    "id": e.get("id"),
                    "summary": e.get("summary"),
                    "start": start,
                    "end": end,
                    "htmlLink": e.get("htmlLink"),
                    "description": e.get("description", "")
                })
            return {"status": "ok", "calendar_id": calendar_id, "events": events}
        except HttpError as e:
            return {"status": "error", "error": str(e)}

    def create_event(self, calendar_id: str, event_summary: str, start_time: datetime.datetime, end_time: datetime.datetime, description: str = "") -> Dict[str, Any]:
        """
        Creates an event and returns structured output:
        { status: "ok", event: {id, summary, start, end, htmlLink}, or {status:"error", error:...} }
        """
        if not start_time.tzinfo or not end_time.tzinfo:
            raise ValueError("Start and end must be timezone-aware datetimes.")

        event_body = {
            "summary": event_summary,
            "start": {"dateTime": start_time.isoformat(), "timeZone": str(start_time.tzinfo)},
            "end": {"dateTime": end_time.isoformat(), "timeZone": str(end_time.tzinfo)},
        }
        if description:
            event_body["description"] = description

        try:
            created = self.service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return {"status": "ok", "event": {
                "id": created.get("id"),
                "summary": created.get("summary"),
                "start": created.get("start"),
                "end": created.get("end"),
                "htmlLink": created.get("htmlLink")
            }}
        except HttpError as e:
            return {"status": "error", "error": str(e)}

    # -------------------------
    # Scheduling helpers
    # -------------------------
    @staticmethod
    def _overlaps(a_start: datetime.datetime, a_end: datetime.datetime, b_start: datetime.datetime, b_end: datetime.datetime) -> bool:
        return (a_start < b_end) and (b_start < a_end)

    def _existing_event_intervals(self, events: List[Dict[str, Any]]) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        intervals = []
        for e in events:
            s_raw = e.get("start")
            e_raw = e.get("end")
            try:
                s_dt = datetime.datetime.fromisoformat(s_raw) if "T" in str(s_raw) else datetime.datetime.fromisoformat(s_raw)
                e_dt = datetime.datetime.fromisoformat(e_raw) if "T" in str(e_raw) else datetime.datetime.fromisoformat(e_raw)
            except Exception:
                # Fallback: skip if cannot parse
                continue
            if not s_dt.tzinfo:
                s_dt = s_dt.replace(tzinfo=TZ)
            if not e_dt.tzinfo:
                e_dt = e_dt.replace(tzinfo=TZ)
            intervals.append((s_dt, e_dt))
        return intervals

    def _find_free_slot(self, day_start: datetime.datetime, day_end: datetime.datetime, duration: timedelta, existing_intervals: List[Tuple[datetime.datetime, datetime.datetime]], avoid_windows: List[Tuple[int, int]] = [(12,13), (18,19)]) -> Optional[Tuple[datetime.datetime, datetime.datetime]]:
        """
        Search the day's working hours for a free slot of `duration`.
        - avoid_windows: list of (hour_start, hour_end) to avoid (local hours)
        Returns (start_dt, end_dt) or None.
        """
        candidate = day_start
        while candidate + duration <= day_end:
            candidate_end = candidate + duration
            # Avoid meal windows: check hour overlap
            hour_ok = True
            for aw in avoid_windows:
                aw_start = candidate.replace(hour=aw[0], minute=0, second=0, microsecond=0)
                aw_end = candidate.replace(hour=aw[1], minute=0, second=0, microsecond=0)
                if self._overlaps(candidate, candidate_end, aw_start, aw_end):
                    hour_ok = False
                    break
            if not hour_ok:
                candidate += timedelta(minutes=30)
                continue

            conflict = False
            for (ex_s, ex_e) in existing_intervals:
                if self._overlaps(candidate, candidate_end, ex_s, ex_e):
                    conflict = True
                    # move past this conflicting event
                    candidate = ex_e
                    break
            if not conflict:
                return (candidate, candidate_end)
        return None

    def schedule_assignments_batch(self, assignments: List[Dict[str, Any]], calendar_id: str = "primary") -> Dict[str, Any]:
        """
        Given a list of assignments (each should include at least: id, title, due_date (ISO str), type(optional: 'exam'/'homework'), estimated_hours(optional)),
        schedule events for each assignment using intelligent defaults, non-conflicting slot selection,
        attach a placeholder for folder links in description (or real folder link if provided in assignment['folder_link']).
        Returns structured dict keyed by assignment id with created event entries or errors.

        Intelligent defaults:
          - session duration: default 2 hours
          - schedule starts: 2 days before due date (for a single session)
          - exam prep: 3-4 sessions spread across 7 days ending on the day before due date
          - allowed hours: 09:00 - 22:00 local time
        """
        results: Dict[str, Any] = {}
        # Determine a wide timeframe to fetch existing events
        earliest = None
        latest = None
        for a in assignments:
            try:
                due = datetime.datetime.fromisoformat(a["due_date"])
                if due.tzinfo is None:
                    due = due.replace(tzinfo=TZ)
                start_window = due - timedelta(days=14)  # look back two weeks
                if earliest is None or start_window < earliest:
                    earliest = start_window
                if latest is None or due + timedelta(days=1) > latest:
                    latest = due + timedelta(days=1)
            except Exception:
                continue

        if earliest is None:
            earliest = datetime.datetime.now(TZ)
        if latest is None:
            latest = earliest + timedelta(days=14)

        # Fetch existing events in timeframe
        existing = self.list_events(calendar_id=calendar_id, time_min=earliest, time_max=latest)
        if existing.get("status") != "ok":
            return {"status": "error", "error": "Could not fetch existing events", "detail": existing}

        existing_intervals = self._existing_event_intervals(existing.get("events", []))

        # allowed daily window
        window_start_hour = 9
        window_end_hour = 22

        for a in assignments:
            aid = a.get("id") or a.get("title")
            results[aid] = {"scheduled": [], "errors": []}
            try:
                due = datetime.datetime.fromisoformat(a["due_date"])
                if due.tzinfo is None:
                    due = due.replace(tzinfo=TZ)
            except Exception:
                results[aid]["errors"].append("Invalid due_date format; expected ISO datetime string.")
                continue

            kind = a.get("type", "homework")
            duration_hours = a.get("estimated_hours", 2)
            duration = timedelta(hours=duration_hours)

            # Plan windows:
            if kind.lower() == "exam":
                # exam prep: 3-4 sessions over the 7 days prior to due date (not conflicting)
                num_sessions = a.get("prep_sessions", 3)
                prep_span_days = a.get("prep_span_days", 7)
                # distribute sessions over the span: choose days evenly
                span_start = due - timedelta(days=prep_span_days)
                days = []
                if prep_span_days <= 0:
                    span_start = due - timedelta(days=7)
                    prep_span_days = 7
                delta = prep_span_days / max(1, num_sessions)
                for i in range(num_sessions):
                    day = span_start + timedelta(days=int(round(i * delta)))
                    days.append(day.date())
                # Try to schedule each session
                for session_day in days:
                    day_start = datetime.datetime.combine(session_day, datetime.time(hour=window_start_hour, minute=0, tzinfo=TZ))
                    day_end = datetime.datetime.combine(session_day, datetime.time(hour=window_end_hour, minute=0, tzinfo=TZ))
                    slot = self._find_free_slot(day_start, day_end, duration, existing_intervals)
                    if not slot:
                        results[aid]["errors"].append(f"No free slot found on {session_day.isoformat()}")
                        continue
                    start_dt, end_dt = slot
                    description = f"Study Session for {a.get('title')}\nResource Folder: {a.get('folder_link','[FOLDER_LINK]')}\nMaterials: {a.get('materials','[]')}"
                    created = self.create_event(calendar_id, f"Study: {a.get('title')}", start_dt, end_dt, description)
                    if created.get("status") == "ok":
                        results[aid]["scheduled"].append(created["event"])
                        # add this interval to existing_intervals to avoid overlapping future slots
                        existing_intervals.append((start_dt, end_dt))
                    else:
                        results[aid]["errors"].append(created.get("error"))
            else:
                # default single session scheduled 2 days before due date at default duration
                preferred_day = (due - timedelta(days=2)).date()
                # find any free slot between 09:00 and 22:00 on preferred_day
                day_start = datetime.datetime.combine(preferred_day, datetime.time(hour=window_start_hour, minute=0, tzinfo=TZ))
                day_end = datetime.datetime.combine(preferred_day, datetime.time(hour=window_end_hour, minute=0, tzinfo=TZ))

                slot = self._find_free_slot(day_start, day_end, duration, existing_intervals)
                # If preferred day full, search backwards up to 7 days, then forwards up to 7 days
                if not slot:
                    found = False
                    for offset in range(1, 8):
                        # earlier day
                        day = preferred_day - timedelta(days=offset)
                        ds = datetime.datetime.combine(day, datetime.time(hour=window_start_hour, minute=0, tzinfo=TZ))
                        de = datetime.datetime.combine(day, datetime.time(hour=window_end_hour, minute=0, tzinfo=TZ))
                        slot = self._find_free_slot(ds, de, duration, existing_intervals)
                        if slot:
                            found = True
                            break
                        # later day
                        day = preferred_day + timedelta(days=offset)
                        ds = datetime.datetime.combine(day, datetime.time(hour=window_start_hour, minute=0, tzinfo=TZ))
                        de = datetime.datetime.combine(day, datetime.time(hour=window_end_hour, minute=0, tzinfo=TZ))
                        slot = self._find_free_slot(ds, de, duration, existing_intervals)
                        if slot:
                            found = True
                            break
                    if not found:
                        results[aid]["errors"].append("No free slot found within +/-7 days of preferred scheduling day.")
                        continue

                start_dt, end_dt = slot
                description = f"Study: {a.get('title')}\nResource Folder: {a.get('folder_link','[FOLDER_LINK]')}\nMaterials: {a.get('materials','[]')}"
                created = self.create_event(calendar_id, f"Study: {a.get('title')}", start_dt, end_dt, description)
                if created.get("status") == "ok":
                    results[aid]["scheduled"].append(created["event"])
                    existing_intervals.append((start_dt, end_dt))
                else:
                    results[aid]["errors"].append(created.get("error"))

        return {"status": "ok", "results": results}

# -------------------------
# Tools (exposed to agent)
# -------------------------
@tool
def tool_list_calendars():
    """
    List the user's Google Calendars.

    Calls the Google Calendar API (via GoogleCalendarManager) to return the calendars
    visible to the authorized account.

    Returns:
        list[dict]: On success, a list of calendar resource dictionaries. Each calendar
            dict typically contains keys such as:
                - "id" (str): calendar identifier
                - "summary" (str): calendar name
                - "timeZone" (str): calendar time zone (if present)
                - "accessRole" (str): the authorized role for the authenticated user
                - other fields returned by the API (primary, selected, etc.)
        dict: On failure, returns a structured error dict with:
            {"status": "error", "error": "<error message>"}

    Notes:
        - Requires valid credentials/token accessible to GoogleCalendarManager.
        - This tool is agent-facing (decorated with @tool) and returns raw API items
          so the orchestrator can choose which fields to use.
    """
    try:
        mgr = GoogleCalendarManager()
        return mgr.service.calendarList().list().execute().get("items", [])
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def tool_list_events(calendar_id: str = "primary", start_iso: Optional[str] = None, end_iso: Optional[str] = None):
    """
    Lists events between start_iso and end_iso (ISO strings). If omitted, defaults
    to now -> now+30d.
    Returns structured dict: {"status":"ok","events":[...]} or error.
    """
    try:
        mgr = GoogleCalendarManager()
        time_min = datetime.datetime.fromisoformat(start_iso) if start_iso else None
        time_max = datetime.datetime.fromisoformat(end_iso) if end_iso else None
        if time_min and time_min.tzinfo is None:
            time_min = time_min.replace(tzinfo=TZ)
        if time_max and time_max.tzinfo is None:
            time_max = time_max.replace(tzinfo=TZ)
        return mgr.list_events(calendar_id=calendar_id, time_min=time_min, time_max=time_max)
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def tool_create_event(calendar_id: str, event_summary: str, start_time_iso: str, end_time_iso: str, description: str = ""):
    """
    Creates calendar event using ISO datetimes (strings). Returns structured dict.
    Example start_time_iso: '2025-11-05T14:00:00-04:00'
    """
    try:
        mgr = GoogleCalendarManager()
        start_dt = datetime.datetime.fromisoformat(start_time_iso)
        end_dt = datetime.datetime.fromisoformat(end_time_iso)
        # Ensure tz-aware in case string omitted tz
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=TZ)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=TZ)
        return mgr.create_event(calendar_id, event_summary, start_dt, end_dt, description)
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def tool_schedule_assignments_batch(assignments: List[Dict[str, Any]], calendar_id: str = "primary"):
    """
    Batch scheduler tool.
    Input: list of assignment dicts; each should include:
      - id (optional), title (required), due_date (ISO string, required)
      - type: 'exam' or 'homework' (optional)
      - folder_link (optional): url to attach in description
      - estimated_hours (optional)
      - prep_sessions (optional for exams)
    Output: { status: 'ok', results: {assignment_id: {scheduled: [...], errors: [...]}}}
    """
    try:
        mgr = GoogleCalendarManager()
        return mgr.schedule_assignments_batch(assignments, calendar_id=calendar_id)
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def tool_create_calendar(calendar_summary: str, time_zone: str = "America/New_York"):
    """
    Creates a new Google Calendar.
    Use only when a distinct, isolated calendar is explicitly needed.
    """
    try:
        manager = GoogleCalendarManager()
        return manager.create_calendar(calendar_summary, time_zone)
    except Exception as e:
        return {"error": f"Error creating calendar '{calendar_summary}': {e}"}


if __name__ == "__main__":
    # Example usage (requires credentials/token)
    try:
        cal_mgr = GoogleCalendarManager()
        print("Calendar service initialized.")
        # list next 10 events
        now = datetime.datetime.now(TZ)
        later = now + timedelta(days=14)
        print(json.dumps(cal_mgr.list_events(time_min=now, time_max=later), indent=2, default=str))
    except Exception as e:
        print(f"Calendar initialization error: {e}")
