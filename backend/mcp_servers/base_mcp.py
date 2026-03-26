"""
mcp_servers/base_mcp.py — BaseMCP with standard error envelope and user_id guard.

All MCP servers inherit from BaseMCP. Every tool method must:
  1. Call self._assert_owner(user_id, claimed_user_id) to verify ownership.
  2. Wrap DB/external calls in try/except and return the standard error envelope
     on failure: {"error": str, "code": str}
"""

from typing import Any

from backend.core.exceptions import ResourceOwnershipError
from backend.core.logger import get_logger


class BaseMCP:
    """Base class for all MCP servers."""

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def _assert_owner(self, requesting_user_id: str, resource_user_id: str) -> None:
        """Raise if the requesting user does not own the resource."""
        if requesting_user_id != resource_user_id:
            raise ResourceOwnershipError(
                "You do not have permission to access this resource.",
                detail=f"requesting={requesting_user_id} resource_owner={resource_user_id}",
            )

    def _error(self, message: str, code: str = "MCP_ERROR") -> dict[str, Any]:
        """Return the standard MCP error envelope."""
        self.logger.error("MCP tool error", code=code, message=message)
        return {"error": message, "code": code}

    def _is_error(self, result: Any) -> bool:
        return isinstance(result, dict) and "error" in result
