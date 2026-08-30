"""
Configuration — load environment variables and app-wide settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def env(name: str, default: str) -> str:
    """Read an env var, treating blank as absent.

    `os.getenv(name, default)` returns "" when the key exists but is empty —
    which is how every commented-out line in .env behaves. That silently beat
    the defaults: a blank SALAAM_DATA_DIR became Path(""), pointing the memory
    store at the working directory instead of the user's home.
    """
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


class Config:
    # Server identity
    SERVER_NAME: str = env("SERVER_NAME", "Salaam")
    DEBUG: bool = env("DEBUG", "false").lower() == "true"

    # Who Salaam is talking to, and where they are. This gives news, weather,
    # markets and prayer times a sensible default so the user doesn't have to
    # repeat "in Nigeria" on every single turn.
    OWNER_NAME: str = env("OWNER_NAME", "boss")
    HOME_CITY: str = env("HOME_CITY", "Lagos")
    HOME_COUNTRY: str = env("HOME_COUNTRY", "Nigeria")
    TIMEZONE: str = env("TIMEZONE", "Africa/Lagos")

    # Where the persistent brain lives (notes, reminders, remembered facts).
    DATA_DIR: Path = Path(env("SALAAM_DATA_DIR", str(Path.home() / ".salaam")))

    # External API keys — all OPTIONAL. Salaam falls back to keyless public
    # sources when they are missing, so it works out of the box.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    # Optional but recommended: free tier at https://brave.com/search/api/.
    # Scraped search engines throw captchas under load; this doesn't.
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")

    # Network behaviour
    HTTP_TIMEOUT: float = float(env("HTTP_TIMEOUT", "12"))
    # Feeds are fetched concurrently, so the batch takes as long as its SLOWEST
    # source. A tight cap here keeps a briefing snappy over voice: a sluggish
    # outlet is dropped rather than making the user wait in silence. With a
    # dozen sources, losing one costs nothing.
    FEED_TIMEOUT: float = float(env("FEED_TIMEOUT", "5"))
    # A real browser UA, not a custom one. Several Nigerian outlets and the
    # DuckDuckGo endpoint serve a 403 or an anti-bot challenge to anything
    # that self-identifies as a script.
    USER_AGENT: str = env(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )


config = Config()
