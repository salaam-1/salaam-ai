"""
Salaam MCP Server — Entry Point
Run with: python server.py
"""

import argparse
import logging
import os

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # fastmcp is also distributed standalone
    from fastmcp import FastMCP

from salaam.config import config
from salaam.persona import SERVER_INSTRUCTIONS
from salaam.prompts import register_all_prompts
from salaam.resources import register_all_resources
from salaam.tools import register_all_tools

# Create the MCP server instance
mcp = FastMCP(name=config.SERVER_NAME, instructions=SERVER_INSTRUCTIONS)

# Register tools, prompts, and resources
register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


def main(argv: list[str] | None = None) -> None:
    """Run the server.

    ``argv`` is passed explicitly by main.py, which has already consumed its
    own subcommand — parsing sys.argv again here would choke on it.
    """
    parser = argparse.ArgumentParser(description="Salaam MCP server")
    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "sse"),
        choices=["sse", "stdio", "streamable-http"],
        help="Transport to serve on. 'sse' for the voice agent, 'stdio' for "
        "desktop MCP clients like Claude Desktop.",
    )
    args = parser.parse_args(argv)

    # Salaam fans out to a dozen feeds per call; httpx logs every one at INFO
    # and buries anything that actually matters.
    if not config.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.transport == "sse":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = os.getenv("MCP_PORT", "8000")
        print(f"Salaam MCP server starting on http://{host}:{port}/sse")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
