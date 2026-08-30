"""
News tools — world headlines, Nigerian headlines, topic search, what's
trending, and a single combined daily briefing.
"""

from __future__ import annotations

import re

from salaam import life, net, news
from salaam.config import config


def register(mcp):

    @mcp.tool()
    async def get_world_news(limit: int = 10) -> str:
        """
        Latest global headlines from BBC, Al Jazeera, NYT, CNBC and Google News.
        Use for "what's happening in the world?" or general world events.
        """
        articles = await news.fetch_many(news.WORLD_FEEDS)
        return news.render(
            "WORLD NEWS BRIEFING",
            news.curate(articles, limit),
            "The global news grid is unresponsive right now — I couldn't reach any outlet.",
        )

    @mcp.tool()
    async def get_nigeria_news(limit: int = 12) -> str:
        """
        Latest Nigerian headlines from Punch, Premium Times, Channels TV,
        Vanguard, The Cable, Daily Post, Legit, Nairametrics, BusinessDay and
        Arise. Use for "what's happening in Nigeria?" or Nigerian current affairs.
        """
        articles = await news.fetch_many(news.NIGERIA_FEEDS)
        return news.render(
            "NIGERIA NEWS BRIEFING",
            news.curate(articles, limit),
            "I couldn't reach the Nigerian news sources just now.",
        )

    @mcp.tool()
    async def get_news_about(topic: str, region: str = "NG", within_days: int = 3, limit: int = 10) -> str:
        """
        Search the news for a specific topic, person, company or event.

        Use this for anything specific: "news about Dangote", "latest on the
        naira", "what happened with the CBN", "Super Eagles results".

        Args:
            topic: what to search for.
            region: NG, US, GB, ZA, KE, GH or IN. Defaults to Nigeria.
            within_days: how far back to look. Use 1 for breaking news, 7 for a weekly view.
            limit: how many stories to return.
        """
        url = news.google_news_search_url(topic, region, within_days)
        articles = await news.fetch_feed("Google News", url, per_feed=limit * 3)
        return news.render(
            f'NEWS: "{topic.upper()}" (last {within_days}d, {region.upper()})',
            news.curate(articles, limit),
            f'No recent coverage found for "{topic}" in the last {within_days} days.',
        )

    @mcp.tool()
    async def get_headlines_by_category(category: str, region: str = "NG", limit: int = 10) -> str:
        """
        Headlines for one subject area.

        Args:
            category: world, nigeria, business, technology, entertainment,
                      sports, science or health.
            region: NG, US, GB, ZA, KE, GH or IN.
            limit: how many stories to return.
        """
        key = (category or "").strip().lower()
        topic = news.CATEGORIES.get(key)
        if not topic:
            options = ", ".join(sorted(set(news.CATEGORIES)))
            return f'"{category}" isn\'t a category I cover. Try one of: {options}.'

        feeds = {"Google News": news.google_news_section_url(topic, region)}
        feeds.update(news.CATEGORY_EXTRAS.get(key, {}))
        articles = await news.fetch_many(feeds)
        return news.render(
            f"{key.upper()} HEADLINES ({region.upper()})",
            news.curate(articles, limit),
            f"I couldn't pull {key} headlines just now.",
        )

    @mcp.tool()
    async def get_top_stories(scope: str = "nigeria", limit: int = 8, within_hours: int = 24) -> str:
        """
        The genuinely BIG news — not merely the newest.

        Use when the user asks what actually matters, what the big story is,
        what they should know about, or "anything important?". Prefer this over
        get_nigeria_news / get_world_news when they want significance rather
        than a raw feed.

        Ranks by how many independent outlets are carrying each story, because
        newsrooms converge on things that matter. A story on eight front pages
        outranks a fresher one on a single site.

        Args:
            scope: "nigeria", "world", or "both".
            limit: how many stories.
            within_hours: how far back counts as current. 24 by default.
        """
        key = (scope or "nigeria").strip().lower()
        feeds: dict[str, str] = {}
        if key in ("nigeria", "ng", "both", "all"):
            feeds.update(news.NIGERIA_FEEDS)
        if key in ("world", "global", "both", "all"):
            feeds.update(news.WORLD_FEEDS)
        if not feeds:
            return 'Use "nigeria", "world" or "both".'

        # Pull deeply: significance needs to see every outlet's take, not a
        # handful of headlines per feed.
        articles = await news.fetch_many(feeds, per_feed=25)
        ranked = news.rank_by_significance(articles, limit, within_hours)
        return news.render_significant(
            f"TOP STORIES — {key.upper()} (last {within_hours}h)",
            ranked,
            f"Nothing significant found in the last {within_hours} hours.",
        )

    @mcp.tool()
    async def get_tech_news(focus: str = "ai", limit: int = 10) -> str:
        """
        AI and technology industry news from TechCrunch, The Verge, Ars
        Technica, MIT Tech Review, VentureBeat, Hacker News and Techpoint
        Africa.

        Use for "what's new in AI", "tech news", "anything happening with
        OpenAI", or anything about the technology industry.

        Args:
            focus: "ai" for artificial intelligence specifically, "all" for
                   the whole industry, or any topic to search within tech.
            limit: how many stories.
        """
        key = (focus or "ai").strip().lower()
        feeds = dict(news.TECH_FEEDS)

        if key not in ("ai", "all", "tech", "technology"):
            feeds = {
                "Google News": news.google_news_search_url(f"{focus} technology", "US", 3)
            }

        articles = await news.fetch_many(feeds, per_feed=12)

        if key == "ai":
            # Keep only genuinely AI-related items — these outlets cover
            # gadgets and policy too, and a mixed list buries the answer.
            terms = (
                "ai", "a.i.", "artificial intelligence", "llm", "gpt", "openai",
                "anthropic", "claude", "gemini", "llama", "machine learning",
                "neural", "chatbot", "deepmind", "nvidia", "model", "agent",
                "copilot", "mistral", "hugging face", "transformer",
            )
            filtered = []
            for article in articles:
                haystack = f"{article['title']} {article['summary']}".lower()
                if any(
                    re.search(rf"\b{re.escape(term)}\b", haystack) for term in terms
                ):
                    filtered.append(article)
            articles = filtered or articles

        label = "AI NEWS" if key == "ai" else f"TECH NEWS — {focus.upper()}"
        return news.render(
            label,
            news.curate(articles, limit),
            "I couldn't reach the technology sources just now.",
        )

    @mcp.tool()
    async def get_trending(region: str = "NG", limit: int = 10) -> str:
        """
        What people are actually searching for and talking about right now,
        from Google Trends, plus the current top stories.

        Use for "what's trending?", "what's everyone talking about?".

        Args:
            region: NG, US, GB, ZA, KE, GH or IN.
        """
        trends_body, stories = await net.gather(
            net.get_text(news.google_trends_url(region)),
            news.fetch_feed(
                "Google News", news.google_news_top_url(region), per_feed=limit * 2
            ),
        )

        lines = [f"### TRENDING NOW — {region.upper()}", ""]

        trends = news.parse_trends(trends_body)
        if trends:
            lines.append("**What people are searching, and why**")
            lines.append("")
            for index, trend in enumerate(trends[:limit], start=1):
                volume = f" — {trend['traffic']} searches" if trend["traffic"] else ""
                lines.append(f"{index}. **{trend['term']}**{volume}")
                # The headlines behind the spike ARE the explanation. Without
                # them a trend list is just words with numbers next to them.
                for story in trend["stories"][:2]:
                    source = f" ({story['source']})" if story["source"] else ""
                    lines.append(f"   - {story['title']}{source}")
                if not trend["stories"]:
                    lines.append("   - _no coverage attached to this spike yet_")
            lines.append("")

        if stories:
            lines.append("**Top stories right now**")
            for article in news.curate(stories, limit):
                lines.append(f"- {article['title']} ({article['source']})")

        if len(lines) <= 2:
            return f"I couldn't reach the trending data for {region.upper()} right now."
        return "\n".join(lines)

    @mcp.tool()
    async def get_daily_briefing(limit_per_section: int = 5) -> str:
        """
        The full morning briefing in one call: Nigerian headlines, world
        headlines, what's trending, markets and the local weather.

        Use this when the user says "brief me", "what did I miss?",
        "catch me up", or "good morning".
        """
        nigeria, world, trends_body, crypto, fx, forecast = await net.gather(
            news.fetch_many(news.NIGERIA_FEEDS, per_feed=5),
            news.fetch_many(news.WORLD_FEEDS, per_feed=5),
            net.get_text(news.google_trends_url("NG")),
            life.crypto_prices(),
            life.fx_rates(),
            life.weather(config.HOME_CITY),
        )

        sections: list[str] = [f"# SALAAM DAILY BRIEFING — {config.HOME_CITY}"]

        if nigeria:
            sections.append(
                news.render("NIGERIA", news.curate(nigeria, limit_per_section), "")
            )
        if world:
            sections.append(news.render("WORLD", news.curate(world, limit_per_section), ""))

        root = net.parse_xml(trends_body) if trends_body else None
        items = root.findall(".//item") if root is not None else []
        if items:
            trending = [net.first_text(item, "title") for item in items[:6]]
            sections.append("### TRENDING IN NIGERIA\n" + ", ".join(t for t in trending if t))

        if crypto or fx:
            sections.append(life.describe_markets(crypto, fx))
        if forecast:
            sections.append(life.describe_weather(forecast))

        if len(sections) == 1:
            return "I couldn't reach any of my sources for the briefing — check the connection."
        return "\n\n".join(sections)
