"""
Try Salaam from the terminal — no LiveKit, no API keys, no MCP client.

    python try_salaam.py                 # interactive
    python try_salaam.py brief           # run one thing and exit
    python try_salaam.py weather Kano

Type `help` inside the prompt to see everything available.
"""

from __future__ import annotations

import asyncio
import io
import logging
import shlex
import sys

# The briefing prints °C, ▲ and — which crash the default Windows codepage.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.getLogger("httpx").setLevel(logging.WARNING)

from server import mcp  # noqa: E402  (must follow the stdout fix)

# Short names → the tool behind them, so you can type `ng` not
# `get_nigeria_news`. Anything not listed here still works by its real name.
SHORTCUTS: dict[str, tuple[str, dict]] = {
    "brief": ("get_daily_briefing", {}),
    "ng": ("get_nigeria_news", {"limit": 8}),
    "world": ("get_world_news", {"limit": 8}),
    "trending": ("get_trending", {"region": "NG"}),
    "markets": ("get_markets", {}),
    "time": ("get_current_time", {}),
    "status": ("get_system_status", {}),
    "prayer": ("get_prayer_times", {}),
    "notes": ("list_notes", {}),
    "reminders": ("list_reminders", {}),
    "memory": ("recall", {}),
}

# Shortcuts that take one free-text argument.
ARG_SHORTCUTS: dict[str, tuple[str, str]] = {
    "weather": ("get_weather", "city"),
    "news": ("get_news_about", "topic"),
    "search": ("search_web", "query"),
    "wiki": ("wikipedia_summary", "topic"),
    "read": ("fetch_url", "url"),
    "calc": ("calculate", "expression"),
    "remember": ("remember", "fact"),
    "note": ("save_note", "content"),
    "remind": ("add_reminder", "text"),
    "open": ("open_app", "name"),
    "category": ("get_headlines_by_category", "category"),
}

BANNER = """
╭──────────────────────────────────────────────────────────────╮
│  SALAAM — interactive test console                           │
│  Type a command, or `help` for the full list. `quit` exits.  │
╰──────────────────────────────────────────────────────────────╯

  Try:   brief          the full morning briefing
         ng             Nigerian headlines
         trending       what Nigeria is searching right now
         weather Kano   forecast for any city
         news dangote   news about anything
         markets        crypto + naira rates
"""


def help_text() -> str:
    lines = ["\nShortcuts (no arguments):"]
    lines.append("  " + ", ".join(sorted(SHORTCUTS)))
    lines.append("\nShortcuts (take one argument):")
    lines.append("  " + ", ".join(f"{name} <{arg}>" for name, (_, arg) in sorted(ARG_SHORTCUTS.items())))
    lines.append("\nAny tool by its real name, with key=value arguments:")
    lines.append('  get_news_about topic="fuel subsidy" within_days=1 limit=5')
    lines.append("  convert_currency amount=500 from_currency=USD to_currency=NGN")
    lines.append("\n  tools        list all 35 tool names")
    lines.append("  quit         exit")
    return "\n".join(lines)


def coerce(value: str):
    """Turn a command-line token into the type the tool expects."""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def parse(line: str) -> tuple[str, dict] | None:
    """Map a typed line onto (tool_name, arguments)."""
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = line.split()
    if not parts:
        return None

    head, rest = parts[0], parts[1:]

    if head in SHORTCUTS and not rest:
        return SHORTCUTS[head]

    if head in ARG_SHORTCUTS and rest:
        tool, arg = ARG_SHORTCUTS[head]
        return tool, {arg: " ".join(rest)}

    if head in SHORTCUTS:
        return SHORTCUTS[head]

    # Fall through to a real tool name with key=value pairs.
    arguments = {}
    for token in rest:
        if "=" in token:
            key, _, value = token.partition("=")
            arguments[key] = coerce(value)
    return head, arguments


async def run(tool: str, arguments: dict) -> None:
    try:
        result = await mcp.call_tool(tool, arguments)
    except Exception as error:
        print(f"\n  ✗ {type(error).__name__}: {error}\n")
        return

    # FastMCP returns either a list of content blocks or a (content, meta) pair.
    blocks = result[0] if isinstance(result, tuple) else result
    for block in blocks:
        print("\n" + (getattr(block, "text", None) or str(block)) + "\n")


async def main() -> None:
    argv = sys.argv[1:]

    if argv:
        parsed = parse(" ".join(argv))
        if parsed:
            await run(*parsed)
        return

    print(BANNER)
    while True:
        try:
            line = input("salaam> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in ("quit", "exit", "q"):
            return
        if line == "help":
            print(help_text())
            continue
        if line == "tools":
            names = sorted(tool.name for tool in await mcp.list_tools())
            print("\n  " + "\n  ".join(names) + "\n")
            continue

        parsed = parse(line)
        if parsed:
            print("  …working")
            await run(*parsed)


if __name__ == "__main__":
    asyncio.run(main())
