"""
Core LangGraph orchestration: a tool-calling loop shared by all three
workflows. Each workflow (ticket_triage, status_report, data_sync_notify)
builds its own graph from this same pattern but with a different system
prompt and a different subset of tools — this is the "chaining LangGraph
tool-calling loops across MCP-registered tools" from the resume bullet.

Graph shape:

    START -> agent -> (tool_calls?) -> tools -> agent -> ... -> END

The agent node calls the LLM; if the LLM responds with tool calls, we
route to the tools node, execute them (through the cached tool wrappers),
feed results back to the agent, and loop until the LLM stops requesting
tools or MAX_AGENT_STEPS is hit.
"""
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.config import settings


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    steps: int


def build_workflow_graph(system_prompt: str, tools: list):
    """Builds a compiled LangGraph app for one workflow, given its system
    prompt and the tools it's allowed to call."""

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    ).bind_tools(tools)

    tools_by_name = {t.name: t for t in tools}

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        # Prepend the system prompt on the first turn only.
        if not any(getattr(m, "type", "") == "system" for m in messages):
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=system_prompt), *messages]
        response = llm.invoke(messages)
        return {"messages": [response], "steps": state.get("steps", 0) + 1}

    def tools_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        outputs = []
        for call in getattr(last, "tool_calls", []):
            tool_fn = tools_by_name[call["name"]]
            result = tool_fn.invoke(call["args"])
            outputs.append(
                ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"])
            )
        return {"messages": outputs}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if state.get("steps", 0) >= settings.MAX_AGENT_STEPS:
            return "end"
        if getattr(last, "tool_calls", None):
            return "tools"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()
