"""
Salaam's news engine.

Pulls headlines from a registry of RSS/Atom feeds concurrently, normalises
them into one shape, de-duplicates near-identical stories, and sorts by
recency. Every source is keyless and public, so this works out of the box.

A dead feed never breaks a briefing — it is silently dropped and the rest
still come through.
"""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

from salaam import net
from salaam.config import config

ATOM = "{http://www.w3.org/2005/Atom}"

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

WORLD_FEEDS: dict[str, str] = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "CNBC": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "Google News": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
}

NIGERIA_FEEDS: dict[str, str] = {
    "Punch": "https://punchng.com/feed/",
    "Premium Times": "https://www.premiumtimesng.com/feed",
    "Channels TV": "https://www.channelstv.com/feed/",
    "Vanguard": "https://www.vanguardngr.com/feed/",
    "The Cable": "https://www.thecable.ng/feed/",
    "Daily Post": "https://dailypost.ng/feed/",
    "Legit NG": "https://www.legit.ng/rss/all.rss",
    "Nairametrics": "https://nairametrics.com/feed/",
    "BusinessDay": "https://businessday.ng/feed/",
    "Arise News": "https://www.arise.tv/feed/",
    "Google News NG": "https://news.google.com/rss?hl=en-NG&gl=NG&ceid=NG:en",
}

# AI and technology, deliberately separate from the generic "technology"
# category — that one fills with phone-deal listicles. These are the outlets
# that actually cover the industry.
TECH_FEEDS: dict[str, str] = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "Techpoint Africa": "https://techpoint.africa/feed/",
}

# Deliberately NOT included above: a Google News "artificial intelligence"
# search. It returns mostly stock-picking listicles and vendor marketing, and
# because sources are weighted evenly that noise crowds out MIT Tech Review.
# Real reporting comes from named outlets.

# Extra specialist feeds layered on top of the Google News section feed.
CATEGORY_EXTRAS: dict[str, dict[str, str]] = {
    "technology": {
        "Hacker News": "https://hnrss.org/frontpage",
        "Techpoint Africa": "https://techpoint.africa/feed/",
    },
    "business": {
        "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
        "Nairametrics": "https://nairametrics.com/feed/",
    },
}

CATEGORIES = {
    "world": "WORLD",
    "nigeria": "NATION",
    "nation": "NATION",
    "business": "BUSINESS",
    "technology": "TECHNOLOGY",
    "tech": "TECHNOLOGY",
    "entertainment": "ENTERTAINMENT",
    "sports": "SPORTS",
    "science": "SCIENCE",
    "health": "HEALTH",
}

REGIONS = {
    "NG": ("en-NG", "NG", "NG:en"),
    "NIGERIA": ("en-NG", "NG", "NG:en"),
    "US": ("en-US", "US", "US:en"),
    "WORLD": ("en-US", "US", "US:en"),
    "GB": ("en-GB", "GB", "GB:en"),
    "UK": ("en-GB", "GB", "GB:en"),
    "ZA": ("en-ZA", "ZA", "ZA:en"),
    "KE": ("en-KE", "KE", "KE:en"),
    "GH": ("en-GH", "GH", "GH:en"),
    "IN": ("en-IN", "IN", "IN:en"),
}


def _region(code: str) -> tuple[str, str, str]:
    return REGIONS.get((code or "NG").upper(), REGIONS["NG"])


def google_news_search_url(query: str, region: str = "NG", within_days: int = 3) -> str:
    from urllib.parse import quote_plus

    hl, gl, ceid = _region(region)
    window = f"+when:{within_days}d" if within_days else ""
    return (
        f"https://news.google.com/rss/search?q={quote_plus(query)}{window}"
        f"&hl={hl}&gl={gl}&ceid={ceid}"
    )


def google_news_section_url(topic: str, region: str = "NG") -> str:
    hl, gl, ceid = _region(region)
    return (
        f"https://news.google.com/rss/headlines/section/topic/{topic}"
        f"?hl={hl}&gl={gl}&ceid={ceid}"
    )


def google_news_top_url(region: str = "NG") -> str:
    """Google News front page for a region — the genuine top stories.

    Note this is NOT the same as the WORLD section, which for smaller regions
    redirects to a syndication topic full of press releases.
    """
    hl, gl, ceid = _region(region)
    return f"https://news.google.com/rss?hl={hl}&gl={gl}&ceid={ceid}"


def google_trends_url(region: str = "NG") -> str:
    return f"https://trends.google.com/trending/rss?geo={(region or 'NG').upper()}"


# ---------------------------------------------------------------------------
# Fetching + parsing
# ---------------------------------------------------------------------------


# Parsed feeds, cached briefly. Conversations overlap heavily — "brief me"
# then "what's the Nigerian news" hits the same eleven feeds seconds apart, and
# over voice every one of those seconds is dead air. News does not change in
# ninety seconds, so this is free speed with no staleness worth worrying about.
_FEED_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_FEED_TTL = 90.0
_FEED_CACHE_MAX = 80


def _cache_read(url: str) -> list[dict[str, Any]] | None:
    hit = _FEED_CACHE.get(url)
    if not hit:
        return None
    stored, articles = hit
    if time.monotonic() - stored > _FEED_TTL:
        _FEED_CACHE.pop(url, None)
        return None
    return articles


def _cache_write(url: str, articles: list[dict[str, Any]]) -> None:
    if len(_FEED_CACHE) >= _FEED_CACHE_MAX:
        _FEED_CACHE.pop(min(_FEED_CACHE, key=lambda k: _FEED_CACHE[k][0]), None)
    _FEED_CACHE[url] = (time.monotonic(), articles)


async def fetch_feed(source: str, url: str, per_feed: int = 8) -> list[dict[str, Any]]:
    """Fetch one feed and return normalised articles. Never raises."""
    cached = _cache_read(url)
    if cached is not None:
        return cached[:per_feed]

    body = await net.get_text(url, timeout=config.FEED_TIMEOUT)
    if not body:
        return []
    root = net.parse_xml(body)
    if root is None:
        return []

    entries = root.findall(".//item") or root.findall(f".//{ATOM}entry")
    articles = []
    # Parse generously, serve the slice asked for — a later call wanting more
    # items then still gets a cache hit instead of refetching.
    for entry in entries[:max(per_feed, 25)]:
        article = _normalise(entry, source)
        if article:
            articles.append(article)

    _cache_write(url, articles)
    return articles[:per_feed]


async def fetch_many(feeds: dict[str, str], per_feed: int = 8) -> list[dict[str, Any]]:
    """Fetch a whole registry of feeds concurrently and flatten the results."""
    results = await net.gather(
        *(fetch_feed(source, url, per_feed) for source, url in feeds.items())
    )
    articles: list[dict[str, Any]] = []
    for batch in results:
        if batch:
            articles.extend(batch)
    return articles


def _normalise(entry: ET.Element, source: str) -> dict[str, Any] | None:
    title = net.first_text(entry, "title", f"{ATOM}title")
    if not title:
        return None

    link = net.first_text(entry, "link", f"{ATOM}id")
    if not link:
        atom_link = entry.find(f"{ATOM}link")
        if atom_link is not None:
            link = atom_link.get("href", "")

    summary = net.first_text(
        entry,
        "description",
        f"{ATOM}summary",
        f"{ATOM}content",
        "{http://purl.org/rss/1.0/modules/content/}encoded",
    )

    published = net.first_text(
        entry, "pubDate", f"{ATOM}updated", f"{ATOM}published", "{http://purl.org/dc/elements/1.1/}date"
    )

    # Google News titles arrive as "Headline - Publisher"; split the credit out
    # so the briefing can attribute the real outlet rather than "Google News".
    clean_title = _clean(title)
    attributed = source
    if source.startswith("Google News") and " - " in clean_title:
        head, _, publisher = clean_title.rpartition(" - ")
        if head and len(publisher) < 45:
            clean_title, attributed = head.strip(), publisher.strip()

    clean_summary = _clean_summary(summary)

    # Google News search results set the description to a link whose text is
    # just the headline again. Repeating it wastes space and reads terribly
    # aloud, so drop a summary that adds nothing to the title.
    if clean_summary and _restates(clean_summary, clean_title):
        clean_summary = ""

    return {
        "source": attributed,
        "title": clean_title,
        "summary": clean_summary,
        "link": link.strip(),
        "published": published,
        "published_at": _parse_date(published),
    }


def _restates(summary: str, title: str) -> bool:
    """True when the summary is essentially the headline repeated back."""
    normalise = lambda text: _TITLE_NOISE.sub(" ", text.lower()).split()
    summary_words, title_words = normalise(summary), normalise(title)
    if not summary_words or not title_words:
        return False
    # A real summary carries meaningfully more than the headline.
    if len(summary_words) > len(title_words) + 6:
        return False
    return set(title_words).issubset(set(summary_words))


def _clean(text: str) -> str:
    """Strip HTML tags and entities, collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# Boilerplate publishers bolt onto the end of every RSS description. Left in,
# it eats the summary budget and gets read aloud verbatim.
_BOILERPLATE = (
    re.compile(r"\bread more\s*:?\s*https?://\S*", re.I),
    re.compile(r"\bcontinue reading\b.*$", re.I),
    re.compile(r"\bthe post\b.*?\bappeared first on\b.*$", re.I),
    re.compile(r"\bthis (?:post|article) (?:first )?appeared\b.*$", re.I),
    re.compile(r"https?://\S+"),
    # Hacker News descriptions are pure metadata; once the URLs are stripped
    # only bare labels remain ("Article URL: Comments URL: Points: 10").
    re.compile(r"\b(?:article|comments)\s+url\s*:", re.I),
    re.compile(r"\bpoints\s*:\s*\d+", re.I),
    re.compile(r"#\s*comments\s*:\s*\d+", re.I),
)


def _clean_summary(text: str, limit: int = 280) -> str:
    summary = _clean(text)
    for pattern in _BOILERPLATE:
        summary = pattern.sub(" ", summary)
    summary = re.sub(r"\s+", " ", summary).strip(" -–—|·,;")

    if len(summary) <= limit:
        return summary
    # Cut on a word boundary rather than mid-syllable.
    clipped = summary[:limit].rsplit(" ", 1)[0]
    return clipped.rstrip(",;:-") + "…"


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

_TITLE_NOISE = re.compile(r"[^a-z0-9 ]+")


def _fingerprint(title: str) -> str:
    """A loose key so the same story from three outlets collapses to one."""
    words = _TITLE_NOISE.sub(" ", title.lower()).split()
    meaningful = [word for word in words if len(word) > 3][:6]
    return " ".join(sorted(meaningful))


# Words too common in headlines to say anything about which story this is.
_HEADLINE_NOISE = {
    "after", "again", "against", "amid", "another", "are", "as", "at", "back",
    "been", "before", "but", "call", "calls", "can", "for", "from", "government",
    "has", "have", "his", "her", "how", "into", "its", "may", "more", "new",
    "news", "not", "now", "off", "one", "onto", "our", "out", "over", "said",
    "say", "says", "set", "she", "should", "some", "still", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "top", "two", "under", "until", "upon", "was", "were", "what", "when",
    "who", "why", "will", "with", "would", "you", "your", "latest", "report",
    "reports", "update", "updates", "video", "photos", "full", "list",
}


def _content_words(title: str) -> set[str]:
    """The words that actually identify a story."""
    return {
        word
        for word in _TITLE_NOISE.sub(" ", title.lower()).split()
        if len(word) > 3 and word not in _HEADLINE_NOISE
    }


def _same_story(a: set[str], b: set[str]) -> bool:
    """Do two headlines describe the same event?

    Overlap is measured against the SMALLER headline, not the union. Outlets
    write wildly different lengths for one event — a five-word wire headline
    and a twenty-word explainer — and plain Jaccard would call those unrelated
    purely because one is longer.
    """
    if not a or not b:
        return False
    shared = len(a & b)
    return shared >= 2 and shared / min(len(a), len(b)) >= 0.5


def dedupe(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique = []
    for article in articles:
        key = _fingerprint(article["title"])
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(article)
    return unique


def sort_recent(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest first; undated stories sink to the bottom rather than vanish."""
    floor = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return sorted(articles, key=lambda a: a["published_at"] or floor, reverse=True)


def diversify(articles: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Pick a spread of outlets rather than whoever published most recently.

    Punch alone posts often enough to fill a whole briefing on recency, which
    buries the other ten sources. Round-robin across outlets to select, then
    re-sort so the result still reads newest-first.
    """
    by_source: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        by_source.setdefault(article["source"], []).append(article)

    picked: list[dict[str, Any]] = []
    while len(picked) < limit and any(by_source.values()):
        for queue in by_source.values():
            if queue:
                picked.append(queue.pop(0))
                if len(picked) >= limit:
                    break
    return picked


def curate(articles: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = sort_recent(dedupe(articles))
    return sort_recent(diversify(ranked, limit))


def rank_by_significance(
    articles: list[dict[str, Any]], limit: int, within_hours: int = 24
) -> list[dict[str, Any]]:
    """Rank by how BIG a story is, not how recent.

    "Latest" and "important" are different questions. A newsroom publishing a
    transfer rumour thirty seconds ago outranks a coup attempt from this
    morning on recency alone — which is exactly the wrong answer.

    The usable signal is independent corroboration: when a story genuinely
    matters, unrelated newsrooms all drop what they're doing and cover it. So
    cluster near-identical headlines and rank clusters by how many DISTINCT
    outlets carried them. Five newspapers on one story in an hour is a bigger
    deal than any single outlet's newest post.

    Recency still acts as a tiebreaker, and anything older than `within_hours`
    is dropped so yesterday's consensus can't crowd out today's news.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)

    # Exact-fingerprint matching is too strict here: two papers covering one
    # event rarely choose the same six words, so a big story fragments into
    # singletons and looks unimportant. Group on word overlap instead.
    clusters: list[dict[str, Any]] = []
    for article in articles:
        words = _content_words(article["title"])
        if len(words) < 3:
            continue
        published = article["published_at"]
        if published and published < cutoff:
            continue

        match = None
        for cluster in clusters:
            if _same_story(words, cluster["words"]):
                match = cluster
                break

        if match is None:
            clusters.append(
                {
                    "article": article,
                    "words": words,
                    "sources": {article["source"]},
                    "newest": published,
                }
            )
            continue

        match["sources"].add(article["source"])
        # Keep the best-written version: prefer one that carries a summary.
        if article["summary"] and not match["article"]["summary"]:
            match["article"] = article
        if published and (match["newest"] is None or published > match["newest"]):
            match["newest"] = published

    floor = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ordered = sorted(
        clusters,
        key=lambda c: (len(c["sources"]), c["newest"] or floor),
        reverse=True,
    )

    out = []
    for cluster in ordered[:limit]:
        article = dict(cluster["article"])
        article["outlet_count"] = len(cluster["sources"])
        article["outlets"] = sorted(cluster["sources"])
        out.append(article)
    return out


def render_significant(headline: str, articles: list[dict[str, Any]], empty: str) -> str:
    """Like render(), but leads with how widely each story is being carried."""
    if not articles:
        return empty

    lines = [f"### {headline}", f"_As of {datetime.now().strftime('%d %b %Y, %H:%M')}_", ""]
    for index, article in enumerate(articles, start=1):
        count = article.get("outlet_count", 1)
        weight = (
            f"{count} outlets covering" if count > 1 else f"{article['source']} only"
        )
        age = _ago(article["published_at"])
        stamp = f" · {age}" if age else ""
        lines.append(f"{index}. **{article['title']}**")
        lines.append(f"   _{weight}{stamp}_")
        if article["summary"]:
            lines.append(f"   {article['summary']}")
        if count > 1:
            lines.append(f"   Reported by: {', '.join(article['outlets'][:6])}")
        if article["link"]:
            lines.append(f"   {article['link']}")
    return "\n".join(lines)


def parse_trends(body: str | None) -> list[dict[str, Any]]:
    """Google Trends RSS, including the headlines that explain each term.

    A bare search term with a volume count is close to useless — "army,
    200,000+ searches" tells you nothing. The feed carries the news items
    driving the spike, which is the actual answer to "what's trending".
    """
    root = net.parse_xml(body) if body else None
    if root is None:
        return []

    HT = "{https://trends.google.com/trending/rss}"
    trends = []
    for item in root.findall(".//item"):
        term = net.first_text(item, "title")
        if not term:
            continue
        stories = []
        for entry in item.findall(f"{HT}news_item"):
            title = net.first_text(entry, f"{HT}news_item_title")
            if title:
                stories.append(
                    {
                        "title": _clean(title),
                        "source": net.first_text(entry, f"{HT}news_item_source"),
                        "link": net.first_text(entry, f"{HT}news_item_url"),
                    }
                )
        trends.append(
            {
                "term": term,
                "traffic": net.first_text(item, f"{HT}approx_traffic"),
                "stories": stories,
            }
        )
    return trends


# ---------------------------------------------------------------------------
# Formatting (tuned to be read aloud by a voice agent)
# ---------------------------------------------------------------------------


def _ago(published: datetime | None) -> str:
    if not published:
        return ""
    delta = datetime.now(timezone.utc) - published
    if delta < timedelta(0):
        return "just now"
    if delta < timedelta(hours=1):
        return f"{int(delta.total_seconds() // 60)}m ago"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)}h ago"
    return f"{delta.days}d ago"


def render(headline: str, articles: list[dict[str, Any]], empty: str) -> str:
    if not articles:
        return empty

    lines = [f"### {headline}", f"_As of {datetime.now().strftime('%d %b %Y, %H:%M')}_", ""]
    for index, article in enumerate(articles, start=1):
        age = _ago(article["published_at"])
        stamp = f" · {age}" if age else ""
        lines.append(f"{index}. **{article['title']}** — {article['source']}{stamp}")
        if article["summary"]:
            lines.append(f"   {article['summary']}")
        if article["link"]:
            lines.append(f"   {article['link']}")
    return "\n".join(lines)
