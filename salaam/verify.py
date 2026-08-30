"""
Claim verification — the "is this actually true?" engine.

Nigeria runs on WhatsApp forwards, and a rumour reaches a million phones long
before a correction does. This module takes a claim, searches the news for it,
and reports **how well it is corroborated** — not whether it is true.

The distinction matters and is deliberately preserved everywhere below. We can
observe who reported something; we cannot observe reality. So the output is
always evidence plus a corroboration level, never a verdict of true or false.

The one genuinely useful signal we *can* compute: whether outlets are reporting
independently, or all republishing a single wire story. Twenty papers running
identical headlines is one source wearing twenty hats — which reads as
overwhelming confirmation to a human, and is the exact shape a viral falsehood
takes. We detect that by clustering near-identical headlines.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from salaam import news

# Words that carry no search value. Kept small on purpose: over-stripping a
# claim loses the very terms that make it findable.
NOISE = {
    "a", "about", "after", "all", "an", "and", "any", "are", "as", "at", "be",
    "been", "but", "by", "can", "did", "do", "does", "for", "from", "had",
    "has", "have", "he", "her", "his", "how", "i", "if", "in", "is", "it",
    "its", "just", "me", "my", "no", "not", "now", "of", "on", "or", "our",
    "out", "said", "say", "says", "she", "so", "some", "than", "that", "the",
    "their", "them", "then", "there", "they", "this", "to", "true", "up",
    "was", "we", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your", "heard", "really", "actually",
}


def search_terms(claim: str, limit: int = 8) -> str:
    """Reduce a spoken claim to the terms worth searching for.

    "Is it true that the government is banning cryptocurrency in Nigeria?"
    becomes "government banning cryptocurrency Nigeria".
    """
    words = re.findall(r"[A-Za-z0-9'’-]+", claim)
    kept: list[str] = []
    for word in words:
        if word.lower() in NOISE or len(word) < 3:
            continue
        if word.lower() not in {k.lower() for k in kept}:
            kept.append(word)

    # Proper nouns and long words carry the most signal — keep them first, but
    # preserve original order so the phrase still reads naturally to the engine.
    if len(kept) > limit:
        ranked = sorted(kept, key=lambda w: (w[:1].isupper(), len(w)), reverse=True)
        keep = set(ranked[:limit])
        kept = [w for w in kept if w in keep]
    return " ".join(kept)


async def gather_evidence(
    claim: str, region: str = "NG", within_days: int = 14
) -> list[dict[str, Any]]:
    """Search the news for a claim, from both a local and a global angle."""
    query = search_terms(claim)
    if not query:
        return []

    local_url = news.google_news_search_url(query, region, within_days)
    world_url = news.google_news_search_url(query, "US", within_days)

    batches = await news.net.gather(
        news.fetch_feed("Google News", local_url, per_feed=25),
        news.fetch_feed("Google News", world_url, per_feed=25),
    )

    articles: list[dict[str, Any]] = []
    for batch in batches:
        if batch:
            articles.extend(batch)
    return articles


def assess(claim: str, articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn raw coverage into a corroboration assessment."""
    unique = news.dedupe(articles)
    outlets = sorted({article["source"] for article in unique if article["source"]})

    # Cluster by headline fingerprint across the *undeduped* set: if every
    # outlet's headline collapses to one fingerprint, they're all running the
    # same copy rather than reporting it out independently.
    clusters: dict[str, set[str]] = {}
    for article in articles:
        key = news._fingerprint(article["title"])
        if key:
            clusters.setdefault(key, set()).add(article["source"])

    distinct_angles = len(clusters)
    biggest = max((len(sources) for sources in clusters.values()), default=0)
    syndicated = bool(outlets) and distinct_angles <= 2 and biggest >= 3

    dated = [a["published_at"] for a in unique if a["published_at"]]
    newest = max(dated) if dated else None
    oldest = min(dated) if dated else None

    return {
        "claim": claim,
        "query": search_terms(claim),
        "articles": news.sort_recent(unique)[:8],
        "outlet_count": len(outlets),
        "outlets": outlets,
        "distinct_angles": distinct_angles,
        "syndicated": syndicated,
        "newest": newest,
        "oldest": oldest,
        "level": _level(len(outlets), distinct_angles, syndicated),
    }


def _level(outlet_count: int, distinct_angles: int, syndicated: bool) -> str:
    if outlet_count == 0:
        return "NO_COVERAGE"
    if syndicated:
        return "SINGLE_SOURCE"
    if outlet_count >= 4 and distinct_angles >= 3:
        return "WIDELY_REPORTED"
    if outlet_count >= 2:
        return "SOME_COVERAGE"
    return "SINGLE_SOURCE"


# What each level means, written to be read aloud and to keep the model honest
# about the difference between corroboration and truth.
VERDICTS = {
    "WIDELY_REPORTED": (
        "Widely reported",
        "Several independent outlets are covering this with their own angles. "
        "That is strong corroboration — though it still reflects what the press "
        "is reporting, not verified fact.",
    ),
    "SOME_COVERAGE": (
        "Reported by a few outlets",
        "A small number of outlets carry this. Worth treating as probably real "
        "but not yet well established.",
    ),
    "SINGLE_SOURCE": (
        "Thinly sourced — be careful",
        "This traces back to essentially one source, with other outlets "
        "republishing the same copy rather than confirming it independently. "
        "This is the shape a rumour takes when it spreads. Treat with caution.",
    ),
    "NO_COVERAGE": (
        "No coverage found",
        "No news outlet appears to have reported this in the period searched. "
        "That does NOT make it false — it may be too recent, too local, too "
        "small, or simply worded differently than I searched. It does mean "
        "there is no press corroboration for it right now.",
    ),
}


def render(result: dict[str, Any], within_days: int) -> str:
    headline, meaning = VERDICTS[result["level"]]

    lines = [
        f"### Verification — “{result['claim']}”",
        f"**{headline}**",
        "",
        meaning,
        "",
        f"_Searched: {result['query']} · last {within_days} days_",
    ]

    if result["outlet_count"]:
        lines.append(
            f"_{result['outlet_count']} outlet(s), "
            f"{result['distinct_angles']} distinct framing(s)._"
        )
        if result["newest"]:
            age = (datetime.now(timezone.utc) - result["newest"]).days
            when = "today" if age == 0 else f"{age} day(s) ago"
            lines.append(f"_Most recent coverage: {when}._")

        lines.append("")
        lines.append("**Outlets:** " + ", ".join(result["outlets"][:12]))
        lines.append("")
        lines.append("**What they're reporting:**")
        for index, article in enumerate(result["articles"], start=1):
            lines.append(f"{index}. **{article['title']}** — {article['source']}")
            if article["summary"]:
                lines.append(f"   {article['summary']}")
            if article["link"]:
                lines.append(f"   {article['link']}")

    lines.append("")
    lines.append(
        "_Report this as corroboration, not proof. Never tell the user a claim "
        "is true or false on this basis — tell them who is reporting it and how "
        "strongly, and let them judge._"
    )
    return "\n".join(lines)
