"""
Verification and watchlist tools.

`verify_claim` answers "is this true?" honestly — with corroboration evidence
rather than a verdict. `watch_topic` / `whats_new` turn Salaam from something
you interrogate into something that keeps track for you.
"""

from __future__ import annotations

from datetime import datetime, timezone

from salaam import news, store, verify

WATCHES = "watches"


def register(mcp):

    @mcp.tool()
    async def verify_claim(claim: str, region: str = "NG", within_days: int = 14) -> str:
        """
        Check how well a claim or rumour is corroborated by the news.

        Use this whenever the user asks "is it true that...", "I heard...",
        "someone sent me...", "is this real?", or repeats something from
        WhatsApp, Twitter/X or Facebook.

        Reports which outlets are carrying the story, whether they are
        reporting independently or all republishing one source, and how strong
        the corroboration is. It deliberately does NOT rule a claim true or
        false — report the evidence to the user and let them judge.

        Args:
            claim: the claim in the user's own words.
            region: NG, US, GB, ZA, KE, GH or IN.
            within_days: how far back to search. Widen it for older claims.
        """
        text = claim.strip()
        if not text:
            return "Tell me the claim you want me to check."

        articles = await verify.gather_evidence(text, region, within_days)
        result = verify.assess(text, articles)
        return verify.render(result, within_days)

    # -- Watchlist --------------------------------------------------------

    @mcp.tool()
    def watch_topic(topic: str) -> str:
        """
        Start following a topic. Salaam remembers it and `whats_new` will
        report only stories it hasn't shown you before.

        Use for anything the user says they want to keep up with — a company,
        a person, the naira, their industry, a running story.
        """
        text = topic.strip()
        if not text:
            return "What should I keep an eye on?"

        existing = store.load(WATCHES)
        if any(row["topic"].lower() == text.lower() for row in existing):
            return f'I\'m already watching "{text}".'

        row = store.append(
            WATCHES,
            {"topic": text, "last_checked": None, "seen": []},
        )
        return f'Now watching "{text}" (#{row["id"]}). Ask "what\'s new?" any time.'

    @mcp.tool()
    def list_watches() -> str:
        """Show the topics Salaam is currently following."""
        rows = store.load(WATCHES)
        if not rows:
            return "You aren't watching any topics yet."

        lines = ["### Watching"]
        for row in rows:
            checked = row.get("last_checked")
            when = f" — last checked {checked[:16].replace('T', ' ')}" if checked else " — not checked yet"
            lines.append(f"- (#{row['id']}) {row['topic']}{when}")
        return "\n".join(lines)

    @mcp.tool()
    def unwatch(watch_id: int) -> str:
        """Stop following a topic, by the id shown in list_watches."""
        removed = store.remove(WATCHES, watch_id)
        if not removed:
            return f"No watched topic with id {watch_id}."
        return f'Stopped watching "{removed["topic"]}".'

    @mcp.tool()
    async def whats_new(watch_id: int = 0, limit_per_topic: int = 4) -> str:
        """
        Report what's happened on the user's watched topics since last time —
        showing only stories they haven't already been told about.

        Use for "what's new?", "anything on my topics?", "any updates?".

        Args:
            watch_id: check one specific topic, or 0 for all of them.
            limit_per_topic: most stories to report per topic.
        """
        rows = store.load(WATCHES)
        if watch_id:
            rows = [row for row in rows if row["id"] == watch_id]
            if not rows:
                return f"No watched topic with id {watch_id}."
        if not rows:
            return (
                "You aren't watching anything yet. Say \"watch the naira\" or "
                "\"follow Dangote\" and I'll track it for you."
            )

        sections: list[str] = []
        for row in rows:
            url = news.google_news_search_url(row["topic"], "NG", 7)
            articles = await news.fetch_feed("Google News", url, per_feed=25)

            seen = set(row.get("seen") or [])
            fresh = []
            for article in news.curate(articles, limit_per_topic * 3):
                key = news._fingerprint(article["title"])
                if key and key not in seen:
                    fresh.append(article)
                    seen.add(key)
                if len(fresh) >= limit_per_topic:
                    break

            # Cap the seen-set so the store can't grow without bound.
            store.update(
                WATCHES,
                row["id"],
                last_checked=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                seen=list(seen)[-300:],
            )

            if not fresh:
                sections.append(f"### {row['topic']}\nNothing new since last check.")
                continue

            lines = [f"### {row['topic']}"]
            for article in fresh:
                lines.append(f"- **{article['title']}** — {article['source']}")
                if article["summary"]:
                    lines.append(f"  {article['summary']}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections)
