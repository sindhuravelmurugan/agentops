"""
Workflow 2: Service status report.

Given a list of service names, the agent fetches operational metrics for
each and produces a short health summary — replacing a manual "check the
dashboards and write an update" step.
"""
from langchain_core.messages import HumanMessage

from app.agents.graph import build_workflow_graph
from app.agents.tools import fetch_service_metrics, summarize_status

SYSTEM_PROMPT = (
    "You are an operations reporting agent. Given a list of service names, "
    "fetch each service's metrics and produce a one-paragraph status "
    "summary for each, then a final one-line overall rollup."
)

_graph = build_workflow_graph(SYSTEM_PROMPT, [fetch_service_metrics, summarize_status])


def run(service_names: list[str]) -> dict:
    result = _graph.invoke(
        {
            "messages": [
                HumanMessage(content=f"Produce a status report for: {', '.join(service_names)}")
            ],
            "steps": 0,
        }
    )
    final_message = result["messages"][-1]
    return {
        "workflow": "status_report",
        "services": service_names,
        "result": final_message.content,
        "steps_taken": result["steps"],
    }
