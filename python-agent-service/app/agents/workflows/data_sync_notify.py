"""
Workflow 3: Data sync + notification.

Given a source and target system, the agent syncs records between them and
then notifies a channel with the outcome — collapsing "run the sync job,
check it worked, then post an update" into one automated pass.
"""
from langchain_core.messages import HumanMessage

from app.agents.graph import build_workflow_graph
from app.agents.tools import sync_records, send_notification

SYSTEM_PROMPT = (
    "You are a data-ops agent. Given a source and target system, sync "
    "records between them, then send a notification to the '#ops-updates' "
    "channel summarizing how many records were synced."
)

_graph = build_workflow_graph(SYSTEM_PROMPT, [sync_records, send_notification])


def run(source: str, target: str) -> dict:
    result = _graph.invoke(
        {
            "messages": [HumanMessage(content=f"Sync records from {source} to {target}")],
            "steps": 0,
        }
    )
    final_message = result["messages"][-1]
    return {
        "workflow": "data_sync_notify",
        "source": source,
        "target": target,
        "result": final_message.content,
        "steps_taken": result["steps"],
    }
