"""Musa MCP tools — the small-business sales assistant."""

from salaam.musa import draft_reply, get_business_profile, search_listings


def register(mcp):

    @mcp.tool()
    def musa_get_business_profile(business_id: str = "demo") -> dict:
        """Return a Musa business profile from local JSON data."""
        return get_business_profile(business_id=business_id)

    @mcp.tool()
    def musa_search_listings(query: str, business_id: str = "demo") -> dict:
        """Search Musa listings for a business."""
        return search_listings(query=query, business_id=business_id)

    @mcp.tool()
    def musa_draft_reply(
        customer_message: str,
        business_id: str = "demo",
        conversation_history: list | None = None,
    ) -> dict:
        """Draft a guarded Musa reply, follow-up, or escalation decision."""
        return draft_reply(
            customer_message=customer_message,
            business_id=business_id,
            conversation_history=conversation_history,
        )
