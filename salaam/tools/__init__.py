"""
Tool registry — imports and registers all tool modules with the MCP server.
Add new tool modules here as you build them.
"""

from salaam.tools import life, memory, musa, news, system, utils, verify, web


def register_all_tools(mcp):
    """Register all tool groups onto the MCP server instance."""
    news.register(mcp)
    verify.register(mcp)
    web.register(mcp)
    life.register(mcp)
    memory.register(mcp)
    system.register(mcp)
    utils.register(mcp)
    musa.register(mcp)
