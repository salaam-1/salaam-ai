"""
Salaam MCP Server — Entry Point
Run with: python server.py
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


# Create the MCP server instance
mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=SERVER_INSTRUCTIONS,
)


# Register tools, prompts, and resources
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


def main(argv: list[str] | None = None) -> None:
    """Run the Salaam MCP server."""

    parser = argparse.ArgumentParser(
        description="Salaam MCP server"
    )

    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "sse"),
        choices=[
            "sse",
            "stdio",
            "streamable-http",
        ],
        help=(
            "Transport to use. "
            "'sse' for the existing voice agent, "
            "'stdio' for local desktop clients, "
            "'streamable-http' for modern HTTP deployments."
        ),
    )

    args = parser.parse_args(argv)

    # Reduce noisy httpx logs in production.
    if not config.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    # ---------------------------------------------------------
    # WEB / RENDER DEPLOYMENT
    # ---------------------------------------------------------
    if args.transport == "sse":
        host = os.getenv("MCP_HOST", "0.0.0.0")

        # Render provides PORT automatically.
        port = int(os.getenv("PORT", "8000"))

        print(
            f"Salaam MCP server starting on "
            f"http://{host}:{port}/sse",
            flush=True,
        )

        mcp.run(
            transport="sse",
            host=host,
            port=port,
        )

    # ---------------------------------------------------------
    # MODERN HTTP DEPLOYMENT
    # ---------------------------------------------------------
    elif args.transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))

        print(
            f"Salaam MCP server starting on "
            f"http://{host}:{port}/mcp",
            flush=True,
        )

        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
        )

    # ---------------------------------------------------------
    # LOCAL / CLAUDE DESKTOP
    # ---------------------------------------------------------
    else:
        mcp.run(
            transport="stdio",
        )


if __name__ == "__main__":
    main()