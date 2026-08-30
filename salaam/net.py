"""
Shared networking helpers.

Every outbound call in Salaam goes through here so that timeouts, the
user-agent and failure handling behave the same everywhere. Nothing raises:
callers get ``None`` on failure and decide what to tell the user.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from typing import Any, Iterable

import httpx

from salaam.config import config

DEFAULT_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def client(timeout: float | None = None) -> httpx.AsyncClient:
    """An AsyncClient preconfigured the way Salaam likes it."""
    return httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout or config.HTTP_TIMEOUT,
        headers=DEFAULT_HEADERS,
    )


async def get_text(url: str, **kwargs: Any) -> str | None:
    """GET a URL and return its body as text, or None if anything goes wrong."""
    try:
        async with client() as http:
            response = await http.get(url, **kwargs)
            response.raise_for_status()
            return response.text
    except Exception:
        return None


async def get_json(url: str, **kwargs: Any) -> Any | None:
    """GET a URL and return parsed JSON, or None if anything goes wrong."""
    try:
        async with client() as http:
            response = await http.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


async def gather(*coros: Any) -> list[Any]:
    """Run coroutines concurrently, turning any exception into None."""
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [None if isinstance(item, BaseException) else item for item in results]


def parse_xml(payload: str | bytes) -> ET.Element | None:
    """Parse XML defensively — feeds are frequently malformed."""
    if not payload:
        return None
    if isinstance(payload, str):
        # Strip a leading BOM/whitespace, which ElementTree refuses outright.
        payload = payload.lstrip("﻿ \t\r\n")
        payload = payload.encode("utf-8", errors="replace")
    try:
        return ET.fromstring(payload)
    except ET.ParseError:
        return None


def first_text(element: ET.Element, *paths: str) -> str:
    """Return the first non-empty text found at any of ``paths``."""
    for path in paths:
        value = element.findtext(path)
        if value and value.strip():
            return value.strip()
    return ""


def chunked(items: Iterable[Any], size: int) -> list[list[Any]]:
    """Split an iterable into lists of at most ``size`` items."""
    batch: list[Any] = []
    out: list[list[Any]] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            out.append(batch)
            batch = []
    if batch:
        out.append(batch)
    return out
