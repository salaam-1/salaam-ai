"""
Data resources — expose static content or dynamic data via MCP resources.
"""

from salaam import news
from salaam.config import config


def register(mcp):

    @mcp.resource("salaam://info")
    def server_info() -> str:
        """Basic info about this MCP server."""
        return (
            f"{config.SERVER_NAME} MCP Server\n"
            "A personal AI assistant: news, web, weather, markets, memory "
            "and system control.\n"
            f"Home: {config.HOME_CITY}, {config.HOME_COUNTRY} ({config.TIMEZONE})\n"
            "Built with FastMCP."
        )

    @mcp.resource("salaam://sources")
    def news_sources() -> str:
        """The news outlets Salaam pulls from."""
        lines = ["Nigerian sources:"]
        lines += [f"- {name}" for name in news.NIGERIA_FEEDS]
        lines.append("")
        lines.append("World sources:")
        lines += [f"- {name}" for name in news.WORLD_FEEDS]
        lines.append("")
        lines.append(
            "Topic search and trending come from Google News and Google Trends."
        )
        return "\n".join(lines)
