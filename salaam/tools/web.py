"""
Web tools — real search, page reading, Wikipedia lookups and opening links.
"""

from __future__ import annotations

import html
import re
import time
from urllib.parse import parse_qs, quote, unquote, urlparse

from salaam import net
from salaam.config import config

RESULT_LINK = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
RESULT_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
TAG = re.compile(r"<[^>]+>")
SCRIPT_STYLE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)


def _strip(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", markup))).strip()


def _unwrap(url: str) -> str:
    """DuckDuckGo sometimes wraps results in a /l/?uddg= redirect."""
    if "uddg=" in url:
        target = parse_qs(urlparse(url).query).get("uddg")
        if target:
            return unquote(target[0])
    return "https://" + url[2:] if url.startswith("//") else url


# DuckDuckGo throttles by IP, and a repeated question during one conversation
# ("search that again", a retried tool call) is exactly what trips it. A short
# in-memory cache keeps Salaam well under the limit.
_CACHE: dict[str, tuple[float, list[tuple[str, str, str]]]] = {}
_CACHE_TTL = 600.0
_CACHE_MAX = 64


def _cache_get(query: str) -> list[tuple[str, str, str]] | None:
    entry = _CACHE.get(query.strip().lower())
    if not entry:
        return None
    stored_at, results = entry
    if time.monotonic() - stored_at > _CACHE_TTL:
        _CACHE.pop(query.strip().lower(), None)
        return None
    return results


def _cache_put(query: str, results: list[tuple[str, str, str]]) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        oldest = min(_CACHE, key=lambda key: _CACHE[key][0])
        _CACHE.pop(oldest, None)
    _CACHE[query.strip().lower()] = (time.monotonic(), results)


async def _brave(query: str, limit: int) -> list[tuple[str, str, str]]:
    """Brave Search API — used only when a key is configured."""
    if not config.BRAVE_API_KEY:
        return []

    data = await net.get_json(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": min(limit, 20)},
        headers={
            "X-Subscription-Token": config.BRAVE_API_KEY,
            "Accept": "application/json",
        },
    )
    hits = ((data or {}).get("web") or {}).get("results") or []
    return [
        (_strip(hit.get("title", "")), hit.get("url", ""), _strip(hit.get("description", "")))
        for hit in hits
        if hit.get("url")
    ]


async def _duckduckgo(query: str, limit: int) -> list[tuple[str, str, str]]:
    """Scrape DuckDuckGo. Two endpoints — one often answers when the other
    serves an anti-bot challenge."""
    for endpoint in (
        "https://html.duckduckgo.com/html/",
        "https://lite.duckduckgo.com/lite/",
    ):
        try:
            async with net.client(timeout=20) as http:
                response = await http.post(endpoint, data={"q": query})
                response.raise_for_status()
                body = response.text
        except Exception:
            continue

        links = RESULT_LINK.findall(body)
        if not links:
            continue

        snippets = [_strip(s) for s in RESULT_SNIPPET.findall(body)]
        return [
            (
                _strip(title),
                _unwrap(url),
                snippets[index] if index < len(snippets) else "",
            )
            for index, (url, title) in enumerate(links[:limit])
        ]
    return []


async def _news_fallback(query: str, limit: int) -> str:
    """Structured Google News RSS — never captchas, so it always answers."""
    from salaam import news

    articles = await news.fetch_feed(
        "Google News", news.google_news_search_url(query, "NG", 7), per_feed=limit * 3
    )
    if not articles:
        return ""

    lines = []
    for index, article in enumerate(news.curate(articles, limit), start=1):
        lines.append(f"{index}. **{article['title']}** — {article['source']}")
        if article["summary"]:
            lines.append(f"   {article['summary']}")
        lines.append(f"   {article['link']}")
    return "\n".join(lines)


def register(mcp):

    @mcp.tool()
    async def search_web(query: str, limit: int = 6) -> str:
        """
        Search the live web and return the top results with titles, snippets
        and links. Use this for anything you don't already know, or to verify
        a current fact.
        """
        cached = _cache_get(query)
        if cached is not None:
            results = cached
        else:
            results = await _brave(query, limit) or await _duckduckgo(query, limit)
            if results:
                _cache_put(query, results)
        if results:
            lines = [f'### Web results — "{query}"', ""]
            for index, (title, url, snippet) in enumerate(results[:limit], start=1):
                lines.append(f"{index}. **{title}**")
                if snippet:
                    lines.append(f"   {snippet[:300]}")
                lines.append(f"   {url}")
            return "\n".join(lines)

        # Both general engines are unavailable — usually a captcha under load.
        # Google News RSS is a structured feed that never challenges, so it's a
        # genuine last resort rather than an error message.
        fallback = await _news_fallback(query, limit)
        if fallback:
            return (
                f'### Recent coverage — "{query}"\n'
                "_General web search was unavailable, so these are news results._\n\n"
                + fallback
            )

        # Worded for the model: it must not read this as "I have no internet".
        return (
            f'The search ran but returned nothing for "{query}". Either no page '
            "matches that term, or the search engine is throttling this "
            "connection right now. Tell the user you searched and found nothing, "
            "check you have the spelling right, and offer to try again. Do NOT "
            "say you lack internet access — you have it."
        )

    @mcp.tool()
    async def fetch_url(url: str, max_chars: int = 5000) -> str:
        """
        Fetch a web page and return its readable text with the HTML stripped
        out. Use after search_web to read a specific article in full.
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        body = await net.get_text(url)
        if body is None:
            return f"I couldn't fetch {url} — it may be down, blocked or too slow."

        title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        title = _strip(title_match.group(1)) if title_match else url

        text = _strip(SCRIPT_STYLE.sub(" ", body))
        if not text:
            return f"{title}\n\n(The page returned no readable text — it is probably JavaScript-rendered.)"

        clipped = text[:max_chars]
        suffix = "\n\n…(truncated)" if len(text) > max_chars else ""
        return f"# {title}\nSource: {url}\n\n{clipped}{suffix}"

    @mcp.tool()
    async def wikipedia_summary(topic: str) -> str:
        """
        Get a concise encyclopedic summary of a person, place, event or concept
        from Wikipedia. Faster and more reliable than a web search for
        background facts.
        """
        slug = quote(topic.strip().replace(" ", "_"), safe="")
        data = await net.get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")

        if not data or data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
            # Fall back to search when the exact title doesn't resolve.
            found = await net.get_json(
                "https://en.wikipedia.org/w/api.php?action=query&list=search"
                f"&srsearch={quote(topic)}&format=json&srlimit=1"
            )
            hits = (((found or {}).get("query") or {}).get("search")) or []
            if not hits:
                return f'Wikipedia has no article matching "{topic}".'
            slug = quote(hits[0]["title"].replace(" ", "_"), safe="")
            data = await net.get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")

        if not data or not data.get("extract"):
            return f'I couldn\'t retrieve a Wikipedia summary for "{topic}".'

        page_url = (data.get("content_urls", {}).get("desktop", {}) or {}).get("page", "")
        description = data.get("description", "")
        header = f"### {data.get('title', topic)}"
        if description:
            header += f"\n_{description}_"
        return f"{header}\n\n{data['extract']}\n\n{page_url}".strip()

    @mcp.tool()
    def open_url(url: str) -> str:
        """
        Open a URL in the default web browser on the user's machine.
        Use when the user wants to actually see a page, dashboard or video.
        """
        import webbrowser

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return f"Opening {url} on your screen now."
        except Exception as error:
            return f"I couldn't open the browser: {error}"

    @mcp.tool()
    def open_world_monitor() -> str:
        """
        Open the World Monitor dashboard — a live visual map of global events.
        Use when the user wants a visual overview rather than a text briefing.
        """
        import webbrowser

        try:
            webbrowser.open("https://worldmonitor.app/")
            return "Displaying the World Monitor on your primary screen now."
        except Exception as error:
            return f"I'm unable to initialise the visual monitor: {error}"
