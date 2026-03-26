"""
mcp_servers/mcp_registry.py — Singleton MCP registry.

Holds one instance of each MCP server.
Agents call: registry.call_tool(server, tool, **kwargs)

The registry is wired up in main.py after Supabase client initialisation
and injected into FastAPI app.state for access inside routes and graph nodes.
"""

from typing import Any

from supabase._async.client import AsyncClient as AsyncSupabase

from backend.core.logger import get_logger
from backend.mcp_servers.ats_mcp import AtsMCP
from backend.mcp_servers.docgen_mcp import DocgenMCP
from backend.mcp_servers.log_mcp import LogMCP
from backend.mcp_servers.profile_mcp import ProfileMCP
from backend.mcp_servers.storage_mcp import StorageMCP

logger = get_logger(__name__)


class MCPRegistry:
    """Central router for all MCP tool calls."""

    def __init__(self, supabase: AsyncSupabase) -> None:
        self.profile = ProfileMCP(supabase)
        self.ats = AtsMCP()
        self.storage = StorageMCP(supabase)
        self.docgen = DocgenMCP(supabase)
        self.log = LogMCP(supabase)

        self._server_map = {
            "profile-mcp": self.profile,
            "ats-mcp": self.ats,
            "storage-mcp": self.storage,
            "docgen-mcp": self.docgen,
            "log-mcp": self.log,
        }

    async def call_tool(
        self, server: str, tool: str, **kwargs: Any
    ) -> Any:
        """
        Dispatch a tool call to the correct MCP server.

        Usage:
            result = await registry.call_tool(
                server="profile-mcp",
                tool="get_profile",
                user_id=user_id,
            )
        """
        srv = self._server_map.get(server)
        if srv is None:
            logger.error("Unknown MCP server", server=server)
            return {"error": f"Unknown MCP server: {server}", "code": "UNKNOWN_SERVER"}

        method = getattr(srv, tool, None)
        if method is None:
            logger.error("Unknown MCP tool", server=server, tool=tool)
            return {"error": f"Unknown tool '{tool}' on server '{server}'", "code": "UNKNOWN_TOOL"}

        logger.info("MCP tool call", server=server, tool=tool)
        try:
            return await method(**kwargs)
        except Exception as exc:
            logger.error(
                "MCP tool call failed",
                server=server,
                tool=tool,
                error=str(exc),
            )
            return {"error": str(exc), "code": "TOOL_CALL_ERROR"}
