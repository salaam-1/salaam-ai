"""
Reusable prompt templates registered with the MCP server.
"""


def register(mcp):

    @mcp.prompt()
    def summarize(text: str) -> str:
        """Prompt to summarize a block of text."""
        return f"Summarize the following text concisely:\n\n{text}"

    @mcp.prompt()
    def explain_code(code: str, language: str = "Python") -> str:
        """Prompt to explain a block of code."""
        return (
            f"Explain the following {language} code in plain English, "
            f"step by step:\n\n```{language.lower()}\n{code}\n```"
        )

    @mcp.prompt()
    def news_digest(articles: str, focus: str = "Nigeria and the world") -> str:
        """Turn a raw pile of headlines into a spoken briefing."""
        return (
            f"You are briefing a busy person on {focus}. From the headlines below, "
            "pick the five that genuinely matter and explain each in one sentence, "
            "saying why it matters. Group related stories. Skip celebrity filler "
            "and clickbait. Write it to be read aloud — no markdown, no lists of "
            f"links.\n\n{articles}"
        )

    @mcp.prompt()
    def explain_simply(topic: str) -> str:
        """Explain something twice: properly, then in plain language."""
        return (
            f"Explain {topic} in two passes. First, an accurate explanation for "
            "an intelligent adult. Then, 'put simply:' followed by a version a "
            "twelve-year-old would understand. Keep both short."
        )
