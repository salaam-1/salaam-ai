"""
Salaam MCP Server — Entry Point
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


# ---------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------

mcp = FastMCP(
    name=config.SERVER_NAME,
    instructions=SERVER_INSTRUCTIONS,
)


# ---------------------------------------------------------
# REGISTER SALAAM COMPONENTS
# ---------------------------------------------------------

register_all_tools(mcp)
register_all_prompts(mcp)
register_all_resources(mcp)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Salaam MCP server"
    )

    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "http"),
        choices=[
            "http",
            "streamable-http",
            "sse",
            "stdio",
        ],
    )

    args = parser.parse_args(argv)

    # Keep noisy HTTP logs under control in production.
    if not config.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    # -----------------------------------------------------
    # RENDER / HTTP DEPLOYMENT
    # -----------------------------------------------------

    if args.transport in ("http", "streamable-http", "sse"):
        host = "0.0.0.0"
        port = int(os.getenv("PORT", "10000"))

        print(
            f"Salaam MCP server starting on "
            f"{host}:{port}",
            flush=True,
        )

        if args.transport == "sse":
            mcp.run(
                transport="sse",
                host=host,
                port=port,
            )

        else:
            mcp.run(
                transport="http",
                host=host,
                port=port,
            )

    # -----------------------------------------------------
    # LOCAL / CLAUDE DESKTOP
    # -----------------------------------------------------

    else:
        mcp.run(
            transport="stdio",
        )


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    main()