"""
Workflow 1: Ticket triage.

Given a ticket ID, the agent looks up the ticket, classifies its priority,
and drafts a first-touch response — a 3-step chain that would otherwise be
three separate manual steps for a human operator.
"""
from langchain_core.messages import HumanMessage

from app.agents.graph import build_workflow_graph
from app.agents.tools import lookup_ticket, classify_priority, draft_response

SYSTEM_PROMPT = (
    "You are a support-operations agent. Given a ticket ID, you must: "
    "1) look up the ticket, 2) classify its priority using the subject and "
    "customer tier, 3) draft a first-touch response. Call tools in that "
    "order and then summarize the outcome in one short sentence."
)

_graph = build_workflow_graph(SYSTEM_PROMPT, [lookup_ticket, classify_priority, draft_response])


def run(ticket_id: str) -> dict:
    result = _graph.invoke(
        {"messages": [HumanMessage(content=f"Triage ticket {ticket_id}")], "steps": 0}
    )
    final_message = result["messages"][-1]
    return {
        "workflow": "ticket_triage",
        "ticket_id": ticket_id,
        "result": final_message.content,
        "steps_taken": result["steps"],
    }
