"""
Salaam MCP Server — Entry Point

Local:
    python server.py

Render:
    python server.py --transport streamable-http
"""

import argparse
import logging
import os

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

from salaam.config import config
from salaam.persona import SERVER_INSTRUCTIONS
from salaam.prompts import register_all_prompts
from salaam.resources import register_all_resources
from salaam.tools import register_all_tools


# ---------------------------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=SERVER_INSTRUCTIONS,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "10000")),
)


# ---------------------------------------------------------------------------
# REGISTER TOOLS, PROMPTS, AND RESOURCES
# ---------------------------------------------------------------------------

register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Run the Salaam MCP server."""

    parser = argparse.ArgumentParser(
        description="Salaam MCP server"
    )

    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
        choices=[
            "streamable-http",
            "http",
            "sse",
            "stdio",
        ],
        help=(
            "Transport to use. "
            "'streamable-http' is recommended for Render/network deployment. "
            "'sse' is supported for legacy clients. "
            "'stdio' is for local MCP clients."
        ),
    )

    args = parser.parse_args(argv)

    # Keep HTTP client logs quiet in production.
    if not config.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    # -----------------------------------------------------------------------
    # RENDER / STREAMABLE HTTP
    # -----------------------------------------------------------------------

    if args.transport in ("streamable-http", "http"):

        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "10000"))

        # FastMCP reads host/port from mcp.settings / constructor.
        mcp.settings.host = host
        mcp.settings.port = port

        print(
            f"Salaam MCP server starting on "
            f"http://{host}:{port}/mcp",
            flush=True,
        )

        mcp.run(
            transport="streamable-http",
        )

    # -----------------------------------------------------------------------
    # SSE
    # -----------------------------------------------------------------------

    elif args.transport == "sse":

        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "10000"))

        mcp.settings.host = host
        mcp.settings.port = port

        print(
            f"Salaam MCP SSE server starting on "
            f"http://{host}:{port}/sse",
            flush=True,
        )

        mcp.run(
            transport="sse",
        )

    # -----------------------------------------------------------------------
    # LOCAL / CLAUDE DESKTOP
    # -----------------------------------------------------------------------

    else:

        mcp.run(
            transport="stdio",
        )


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()