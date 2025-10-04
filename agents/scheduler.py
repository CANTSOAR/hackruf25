from agents.baseagent import *
from agents.tools.gcal.gcal import *

SCHEDULER = BaseAgent(
    name = "Scheduler",
    tools = [
        tool_list_calendars,
        tool_list_events,
        tool_create_event,
        tool_create_calendar
    ],
    system_prompt = """
        
    """
)
