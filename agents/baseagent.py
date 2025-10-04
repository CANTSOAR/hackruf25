import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import datetime as dt
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-lite"


class BaseAgent:

    message_log = []
    scheduler = BackgroundScheduler()
    scheduler.start()

    def __init__(self, name: str = "Basic Agent", llm = None, tools: list = [], system_prompt: str = None):
        self.name = name
        self.llm = llm or ChatGoogleGenerativeAI(model = GEMINI_MODEL, google_api_key = GEMINI_API_KEY)
        self.tools = tools
        self.tool_node = ToolNode(tools)

        class AgentState(TypedDict):
            messages: Annotated[list, lambda x, y: x + y]

        graph_builder = StateGraph(AgentState)
        graph_builder.add_node("llm", self.call_model)
        graph_builder.add_node("tools", self.call_tools)

        graph_builder.set_entry_point("llm")
        
        graph_builder.add_conditional_edges(
            "llm",
            self.should_continue,
            {
                "tool_call": "tools",
                "end": END
            }
        )

        graph_builder.add_edge("tools", "llm")

        self.graph = graph_builder.compile()
        self.system_prompt = system_prompt
        self.state = {"messages": []}

    def should_continue(self, state: dict) -> str:
        if state["messages"][-1].tool_calls:
            return "tool_call"
        
        return "end"

    def call_model(self, state: dict):
        messages = state["messages"]

        model_with_tools = self.llm.bind_tools(self.tools)
        response = model_with_tools.invoke(messages)
        BaseAgent.message_log.append(
            {
                "agent_name": self.name,
                "type": "agent",
                "content": response.content
            }
        )

        return {"messages": [response]}
    
    def call_tools(self, state: dict):
        response = self.tool_node.invoke(state)
        tools = state.get("messages")[-1].tool_calls

        for message in response.get("messages", []):
            tool_name = [tool.get("name") for tool in tools[::-1] if tool.get("id") == message.tool_call_id]
            tool_name = tool_name[0] if tool_name else "tool name not found"

            BaseAgent.message_log.append(
                {
                    "agent_name": self.name,
                    "type": "tool: " + tool_name,
                    "content": message.content
                }
            )

        return response

    def run(self, query: str):
        self.state["messages"] = self.state["messages"] + [HumanMessage(content = query)]

        if self.system_prompt and len(self.state["messages"]) == 1:
            self.state["messages"].insert(0, SystemMessage(content = self.system_prompt))
            BaseAgent.message_log.append(
            {
                "agent_name": self.name,
                "type": "system",
                "content": self.system_prompt
            }
        )
        
        BaseAgent.message_log.append(
            {
                "agent_name": self.name,
                "type": "human",
                "content": query
            }
        )
        
        self.state = self.graph.invoke(self.state)

        return self.state["messages"][-1].content
    
    @staticmethod
    @tool
    def take_notes(note: str, open_type: str = "a"):
        """
        Use this tool to take notes, and include the way to open the file, either 'w' or 'a'; the default is 'a' to append to the notes.txt file.
        This could be used to maintain your objective and then ground future responses.
        """
        with open("./agents/notes/notes.txt", open_type) as f:
            f.write(note + "\n")

        return "Note added"
    
    @staticmethod
    @tool
    def read_notes():
        """
        Use this tool to read the current notes file. This should be used to remind yourself of the key objectives and ground your responses.
        """
        with open("./agents/notes/notes.txt", "r") as f:
            notes = f.read()

        return "Current Notes:\n" + notes

class GoogleAgent():

    def __init__(self):
        name = "Google_Tool_Agent"

        google_tools = [
            GenAITool(google_search = {})
        ]

        self.system_prompt = """
        You are a helper agent with three tools that you are to use when told to use them. The three tools are the built-in google tools, and they are explained below:
            google_search: This tool is used to get information from the web based on the query. You will then summarize the search and supply information in a concise format.
      
        As a helper, your priorities are getting the right information and returning it in a dense, concise format, so that there is no bloat/fluff in your response.
        """

        """
            url_context: This tool is used to analyze the context provided. You will then summarize the content and supply information in a concise format.
            code_execution: This tool is used to execute the code provided, or generate and execute code based on the request. You will then summarize the result and supply information in a concise format.
        """

        llm = ChatGoogleGenerativeAI(model = GEMINI_MODEL, google_api_key = GEMINI_API_KEY)
        self.model_with_tools = llm.bind_tools(google_tools)

    def run(self, query: str):
        messages = [
            SystemMessage(content = self.system_prompt),
            HumanMessage(content = query)
        ]
        
        response = self.model_with_tools.invoke(messages)
        
        return response.content

    def make_google_search(self):
        def google_search(query: str):
            """
            Use this tool to make a google search and get back a concise summary of the results. Try to be specific with your query.
            """
            result = self.run(f"You have been called to use your google search tool. The query is {query}. Remember to be concise in your summary of the search response.")

            return result

        return google_search
    
GOOGLE_HELPER = GoogleAgent()