"""
Registers AgentOps tools on an MCP (Model Context Protocol) server so they
are callable by any MCP-compatible client, not only by the LangGraph agents
in this repo. This is what the resume bullet means by "MCP-registered
tools" — the tools live behind a standard protocol boundary rather than
being hardcoded into one agent's prompt.

Run standalone with:
    python -m app.agents.mcp_server
"""
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
import json

from app.agents.tools import ALL_TOOLS

server = Server("agentops-tools")

# Build an MCP Tool schema entry for each LangChain tool we already defined,
# so we don't have to maintain two separate tool definitions.
_TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=t.name,
            description=t.description or "",
            inputSchema=t.args_schema.model_json_schema() if t.args_schema else {"type": "object"},
        )
        for t in ALL_TOOLS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name not in _TOOLS_BY_NAME:
        raise ValueError(f"Unknown tool: {name}")
    result = _TOOLS_BY_NAME[name].invoke(arguments)
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
