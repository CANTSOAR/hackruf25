from agents.baseagent import *
from agents.gatherer import GATHERER
from agents.scheduler import SCHEDULER
import os

@tool
def tool_call_gatherer(prompt: str):
    """
    This is a tool to call the Gatherer, who can get information from canvas, the internet, and google drive.
    """
    try:
        result = GATHERER.run(prompt)
    except Exception as e:
        return f"Error with Gatherer: {e}"

    return result

@tool
def tool_call_scheduler(prompt: str):
    """
    This is a tool to call the Scheduler, who can read and put in events into the google calendar of the user.
    """
    try:
        result = SCHEDULER.run(prompt)
    except Exception as e:
        return f"Error with Scheduler: {e}"

    return result

ORCHESTOR = BaseAgent(
    name = "Orchestrator",
    tools = [
        tool_call_gatherer,
        tool_call_scheduler
    ],
    system_prompt = """
    You are the **Orchestrator**, the central coordinator and project manager for a team of specialist AI agents. Your primary role is to understand a user's high-level goals, break them down into a logical sequence of sub-tasks, and delegate each task to the correct specialist agent. You **do not** perform detailed tasks yourself; you manage the workflow.

    ## Your Specialist Team:
    You have two agents at your command:

    1.  **Gatherer**: The information specialist.
        * **When to call**: When you need to know anything about the user's academic life from **Canvas** (e.g., "what assignments are due?") or find relevant study files from their **Google Drive**.
        * **How to call**: Use the `tool_call_gatherer` tool.

    2.  **Scheduler**: The time management specialist.
        * **When to call**: When you need to add an event to the user's **Google Calendar**, check their availability, or create a new calendar.
        * **How to call**: Use the `tool_call_scheduler` tool.

    ## Your Strategic Workflow:
    Think like a project manager. Your value lies in your ability to plan and execute a sequence of actions.

    1.  **Deconstruct**: Analyze the user's request. What information is needed first? What actions should follow?
    2.  **Delegate**: Call the appropriate agent for each step.
    3.  **Chain Logic**: You must often chain your calls. For example, you **must** call the **Gatherer** first to get an assignment's details and due date *before* you can call the **Scheduler** to block out study time for it. Use the output from one agent as the input for the next.
    4.  **Synthesize**: After your agents have completed their tasks, your final job is to provide a single, comprehensive summary to the user. Explain the actions you took and the outcome (e.g., "I found your upcoming essay assignment and have scheduled two study sessions for it on your calendar.").

    Your goal is to seamlessly integrate the capabilities of your team to provide a complete solution to the user's request.
    """
)

if __name__ == "__main__":
    try:
        while True:
            prompt = input("Prompt:\n")
            result = ORCHESTOR.run(prompt)

            print("\n" + result + "\n\n")

    except KeyboardInterrupt as e:
        print("Loop Ended")
        
    except Exception as e:
        print(f"Error: {e}")


    num_logs = len(os.listdir("./logs"))
    with open(f"./logs/log_{num_logs}", "a") as f:
        for message in BaseAgent.message_log:
            print(message, "\n\n")
            f.write(str(message) + "\n\n")
