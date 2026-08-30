"""
Salaam in your browser.

    python webapp.py      →  http://127.0.0.1:8080

Two things in one page:

  * **Console** — click or type any of Salaam's 40 tools and read the result.
    Needs nothing but this process. No LiveKit, no keys.
  * **Voice** — talk to Salaam in the browser instead of the LiveKit playground.
    Needs your LiveKit credentials in .env and the voice agent running.

The tools are called in-process, so this does not need the MCP server on :8000
to be running as well. The voice tab does need the agent (`main.py voice-dev`).
"""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from salaam.config import config

logging.getLogger("httpx").setLevel(logging.WARNING)

# Importing server registers every tool onto its FastMCP instance, which we
# then borrow. One definition of the toolset, two front ends.
from server import mcp  # noqa: E402

PAGE = Path(__file__).with_name("webapp.html")


def _text(result) -> str:
    """FastMCP returns either a content list or a (content, meta) tuple."""
    blocks = result[0] if isinstance(result, tuple) else result
    if isinstance(blocks, (str, bytes)):
        return blocks if isinstance(blocks, str) else blocks.decode()
    parts = []
    for block in blocks or []:
        parts.append(getattr(block, "text", None) or str(block))
    return "\n".join(parts).strip()


async def home(request):
    return HTMLResponse(PAGE.read_text(encoding="utf-8"))


async def list_tools(request):
    tools = await mcp.list_tools()
    return JSONResponse(
        {
            "owner": config.OWNER_NAME,
            "city": config.HOME_CITY,
            "tools": sorted(
                (
                    {
                        "name": tool.name,
                        "description": (tool.description or "").strip().split("\n\n")[0],
                        "schema": tool.inputSchema or {},
                    }
                    for tool in tools
                ),
                key=lambda item: item["name"],
            ),
        }
    )


async def call_tool(request):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Body must be JSON."}, status_code=400)

    name = (payload.get("name") or "").strip()
    arguments = payload.get("args") or {}
    if not name:
        return JSONResponse({"error": "No tool name given."}, status_code=400)
    if not isinstance(arguments, dict):
        return JSONResponse({"error": "args must be an object."}, status_code=400)

    try:
        result = await mcp.call_tool(name, arguments)
    except Exception as error:
        return JSONResponse(
            {"error": f"{type(error).__name__}: {error}"}, status_code=400
        )
    return JSONResponse({"text": _text(result)})


async def voice_token(request):
    """Mint a LiveKit access token so the browser can join a room."""
    import os

    url = os.getenv("LIVEKIT_URL", "")
    key = os.getenv("LIVEKIT_API_KEY", "")
    secret = os.getenv("LIVEKIT_API_SECRET", "")

    if not (url and key and secret):
        return JSONResponse(
            {
                "error": "LiveKit isn't configured. Set LIVEKIT_URL, "
                "LIVEKIT_API_KEY and LIVEKIT_API_SECRET in .env."
            },
            status_code=400,
        )

    from livekit.api import AccessToken, VideoGrants

    # A fresh room each visit, so a stale session never blocks a new one.
    room = f"salaam-{secrets.token_hex(4)}"
    token = (
        AccessToken(key, secret)
        .with_identity(f"user-{secrets.token_hex(3)}")
        .with_name(config.OWNER_NAME)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )
    return JSONResponse({"url": url, "token": token.to_jwt(), "room": room})


app = Starlette(
    routes=[
        Route("/", home),
        Route("/api/tools", list_tools),
        Route("/api/call", call_tool, methods=["POST"]),
        Route("/api/voice-token", voice_token),
    ]
)


def main() -> None:
    host = "127.0.0.1"
    port = int(__import__("os").getenv("SALAAM_WEB_PORT", "8080"))
    print(f"\n  Salaam is on http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
