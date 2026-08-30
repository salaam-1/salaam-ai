"""Deterministic Musa sales-assistant core.

The MVP deliberately avoids live model calls. It only replies with facts that
exist in the editable JSON data files beside this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).with_name("data")

PRICE_KEYWORDS = {
    "amount",
    "cost",
    "fee",
    "how much",
    "hw much",
    "hw mch",
    "last price",
    "price",
}
AVAILABILITY_KEYWORDS = {
    "available",
    "availability",
    "do you have",
    "in stock",
    "still available",
    "still dey",
    "u get",
    "u get am",
    "you get",
}
ORDER_KEYWORDS = {
    "book",
    "buy",
    "i want it",
    "make payment",
    "order",
    "pay",
    "reserve",
}
LOCATION_DELIVERY_KEYWORDS = {
    "address",
    "deliver",
    "delivery",
    "location",
    "where",
}
COMPLAINT_KEYWORDS = {
    "bad",
    "broken",
    "complain",
    "complaint",
    "fake",
    "not working",
    "refund",
    "return",
    "wrong",
}
PRODUCT_KEYWORDS = {
    "looking for",
    "need",
    "send me",
    "show me",
    "want",
}
STOPWORDS = {
    "a",
    "abeg",
    "am",
    "and",
    "any",
    "available",
    "be",
    "buy",
    "can",
    "cost",
    "dey",
    "do",
    "for",
    "get",
    "have",
    "how",
    "hw",
    "i",
    "in",
    "is",
    "it",
    "last",
    "looking",
    "me",
    "mch",
    "much",
    "need",
    "of",
    "order",
    "price",
    "send",
    "show",
    "stock",
    "the",
    "to",
    "u",
    "want",
    "you",
}


def get_business_profile(business_id: str = "demo") -> dict[str, Any]:
    """Return one business profile from JSON data."""

    business = _business_by_id(business_id)
    if business is None:
        return {
            "error": "business_not_found",
            "business_id": business_id,
            "message": f"No business profile exists for '{business_id}'.",
        }
    return dict(business)


def search_listings(query: str, business_id: str = "demo") -> dict[str, Any]:
    """Search active listings for a business using deterministic token matching."""

    business = _business_by_id(business_id)
    if business is None:
        return {
            "error": "business_not_found",
            "business_id": business_id,
            "query": query,
            "matches": [],
            "count": 0,
        }

    matches = _rank_listings(query, business_id)
    return {
        "business_id": business_id,
        "business_name": business["name"],
        "query": query,
        "count": len(matches),
        "matches": [_public_listing(match["listing"], match["score"]) for match in matches],
    }


def draft_reply(
    customer_message: str,
    business_id: str = "demo",
    conversation_history: list[Any] | None = None,
) -> dict[str, Any]:
    """Draft a guarded Musa reply for one customer message."""

    business = _business_by_id(business_id)
    if business is None:
        return _escalation_result(
            business={},
            business_id=business_id,
            customer_message=customer_message,
            intent="UNKNOWN",
            reason="business_not_found",
            matched_context=[],
            message="I need the business owner to confirm this because the shop profile is missing.",
        )

    history_text = _history_to_text(conversation_history)
    intent = classify_intent(customer_message)
    search_text = _combined_search_text(customer_message, history_text)
    matches = _rank_listings(search_text, business_id)
    matched_context = [_public_listing(match["listing"], match["score"]) for match in matches[:3]]
    top_listing = matches[0]["listing"] if matches else None

    if intent == "COMPLAINT":
        return _escalation_result(
            business,
            business_id,
            customer_message,
            intent,
            "complaint",
            matched_context,
            "Sorry about that. I will have the owner check this and respond to you directly.",
        )

    if intent == "LOCATION_OR_DELIVERY":
        return _reply_result(
            business,
            business_id,
            customer_message,
            intent,
            _location_delivery_reply(business),
            matched_context,
        )

    if intent == "ORDER_INTENT":
        if top_listing is None:
            return _follow_or_escalate(
                business,
                business_id,
                customer_message,
                intent,
                history_text,
                matched_context,
                "Which product would you like to order? Please send the name or model.",
                "order_without_product_match",
            )
        return _escalation_result(
            business,
            business_id,
            customer_message,
            intent,
            "order_intent",
            matched_context,
            f"Thanks. I will have the owner confirm the order for {top_listing['title']} with you.",
        )

    if intent == "PRICE_INQUIRY":
        if top_listing is None:
            return _follow_or_escalate(
                business,
                business_id,
                customer_message,
                intent,
                history_text,
                matched_context,
                "Which product do you want the price for? Please send the name or model.",
                "price_without_product_match",
            )
        return _reply_result(
            business,
            business_id,
            customer_message,
            intent,
            _price_reply(top_listing),
            matched_context,
        )

    if intent == "AVAILABILITY_INQUIRY":
        if top_listing is None:
            return _follow_or_escalate(
                business,
                business_id,
                customer_message,
                intent,
                history_text,
                matched_context,
                "Which product should I check for you? Please send the name or model.",
                "availability_without_product_match",
            )
        return _reply_result(
            business,
            business_id,
            customer_message,
            intent,
            _availability_reply(top_listing),
            matched_context,
        )

    if intent == "PRODUCT_REQUEST":
        if not matches:
            return _follow_or_escalate(
                business,
                business_id,
                customer_message,
                intent,
                history_text,
                matched_context,
                "Which product are you looking for? You can mention the model, size, or category.",
                "product_request_without_match",
            )
        return _reply_result(
            business,
            business_id,
            customer_message,
            intent,
            _product_options_reply([match["listing"] for match in matches[:3]]),
            matched_context,
        )

    if top_listing is not None:
        return _reply_result(
            business,
            business_id,
            customer_message,
            "PRODUCT_REQUEST",
            _product_options_reply([match["listing"] for match in matches[:3]]),
            matched_context,
        )

    return _follow_or_escalate(
        business,
        business_id,
        customer_message,
        intent,
        history_text,
        matched_context,
        "Please send the product name or what you want to know, and I will check it for you.",
        "unknown_without_match",
    )


def classify_intent(message: str) -> str:
    """Classify a customer message into one deterministic Musa intent."""

    text = _normalize(message)
    if _has_phrase(text, COMPLAINT_KEYWORDS):
        return "COMPLAINT"
    if _has_phrase(text, LOCATION_DELIVERY_KEYWORDS):
        return "LOCATION_OR_DELIVERY"
    if _has_phrase(text, PRICE_KEYWORDS):
        return "PRICE_INQUIRY"
    if _has_phrase(text, AVAILABILITY_KEYWORDS):
        return "AVAILABILITY_INQUIRY"
    if _has_phrase(text, ORDER_KEYWORDS):
        return "ORDER_INTENT"
    if _has_phrase(text, PRODUCT_KEYWORDS):
        return "PRODUCT_REQUEST"
    return "UNKNOWN"


def _business_by_id(business_id: str) -> dict[str, Any] | None:
    for business in _read_json("businesses.json"):
        if business.get("id") == business_id:
            return business
    return None


def _read_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _active_listings(business_id: str) -> list[dict[str, Any]]:
    return [
        listing
        for listing in _read_json("listings.json")
        if listing.get("business_id") == business_id and listing.get("is_active", True)
    ]


def _rank_listings(query: str, business_id: str) -> list[dict[str, Any]]:
    query_tokens = _meaningful_tokens(query)
    if not query_tokens:
        return []

    ranked = []
    normalized_query = _normalize(query)
    for listing in _active_listings(business_id):
        candidate_text = _listing_text(listing)
        candidate_tokens = set(_tokens(candidate_text))
        token_overlap = query_tokens & candidate_tokens
        if len(query_tokens) > 1 and len(token_overlap) < 2:
            continue

        score = len(token_overlap) * 3

        title = _normalize(str(listing.get("title", "")))
        category = _normalize(str(listing.get("category", "")))
        if title and title in normalized_query:
            score += 10
        if category and category in normalized_query:
            score += 4
        for token in query_tokens:
            if token in title:
                score += 2

        if score > 0:
            ranked.append({"listing": listing, "score": score})

    return sorted(ranked, key=lambda item: (-item["score"], item["listing"].get("title", "")))


def _public_listing(listing: dict[str, Any], score: int | None = None) -> dict[str, Any]:
    public = {
        "id": listing.get("id"),
        "title": listing.get("title"),
        "category": listing.get("category"),
        "price": listing.get("price"),
        "price_currency": listing.get("price_currency", "NGN"),
        "availability": listing.get("availability"),
        "description": listing.get("description"),
        "attributes": listing.get("attributes", {}),
        "media_urls": listing.get("media_urls", []),
    }
    if score is not None:
        public["match_score"] = score
    return public


def _listing_text(listing: dict[str, Any]) -> str:
    parts = [
        listing.get("title", ""),
        listing.get("category", ""),
        listing.get("description", ""),
        listing.get("availability", ""),
    ]
    attributes = listing.get("attributes", {})
    if isinstance(attributes, dict):
        parts.extend(str(value) for value in attributes.values())
    return " ".join(str(part) for part in parts if part)


def _reply_result(
    business: dict[str, Any],
    business_id: str,
    customer_message: str,
    intent: str,
    message: str,
    matched_context: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "business_id": business_id,
        "business_name": business.get("name"),
        "intent": intent,
        "decision": "reply",
        "message": message,
        "customer_message": customer_message,
        "matched_context": matched_context,
        "escalation": None,
    }


def _follow_or_escalate(
    business: dict[str, Any],
    business_id: str,
    customer_message: str,
    intent: str,
    history_text: str,
    matched_context: list[dict[str, Any]],
    follow_up_message: str,
    escalation_reason: str,
) -> dict[str, Any]:
    if _already_asked_follow_up(history_text):
        return _escalation_result(
            business,
            business_id,
            customer_message,
            intent,
            escalation_reason,
            matched_context,
            "I will have the owner confirm this for you directly.",
        )
    return {
        "business_id": business_id,
        "business_name": business.get("name"),
        "intent": intent,
        "decision": "follow_up",
        "message": follow_up_message,
        "customer_message": customer_message,
        "matched_context": matched_context,
        "escalation": None,
    }


def _escalation_result(
    business: dict[str, Any],
    business_id: str,
    customer_message: str,
    intent: str,
    reason: str,
    matched_context: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    owner = business.get("owner_whatsapp")
    owner_alert = (
        f"Customer needs attention.\n"
        f"Reason: {reason}\n"
        f"Message: {customer_message}"
    )
    if matched_context:
        owner_alert += f"\nMatched: {matched_context[0].get('title')}"

    return {
        "business_id": business_id,
        "business_name": business.get("name"),
        "intent": intent,
        "decision": "escalate",
        "message": message,
        "customer_message": customer_message,
        "matched_context": matched_context,
        "escalation": {
            "reason": reason,
            "customer_message": customer_message,
            "owner_whatsapp": owner,
            "owner_alert_text": owner_alert,
            "matched_context": matched_context,
        },
    }


def _price_reply(listing: dict[str, Any]) -> str:
    return (
        f"{listing['title']} is {_format_price(listing)}. "
        f"It is {_availability_text(listing)}. "
        "Would you like photos or delivery details?"
    )


def _availability_reply(listing: dict[str, Any]) -> str:
    return (
        f"{listing['title']} is {_availability_text(listing)}. "
        f"The price is {_format_price(listing)}. "
        "Would you like the owner to confirm it for you?"
    )


def _product_options_reply(listings: list[dict[str, Any]]) -> str:
    options = [
        f"{listing['title']} at {_format_price(listing)} ({_availability_text(listing)})"
        for listing in listings
    ]
    return "Available options: " + "; ".join(options) + ". Which one should I help with?"


def _location_delivery_reply(business: dict[str, Any]) -> str:
    return (
        f"{business['name']} is at {business['location']}. "
        f"Delivery: {business['delivery_rules']}"
    )


def _format_price(listing: dict[str, Any]) -> str:
    amount = listing.get("price")
    currency = listing.get("price_currency", "NGN")
    if amount is None:
        return "price unavailable"
    return f"{currency} {amount:,.0f}"


def _availability_text(listing: dict[str, Any]) -> str:
    availability = listing.get("availability")
    if availability == "in_stock":
        return "in stock"
    if availability == "out_of_stock":
        return "out of stock"
    if availability == "limited":
        return "limited in stock"
    return "availability unknown"


def _combined_search_text(customer_message: str, history_text: str) -> str:
    message_tokens = _meaningful_tokens(customer_message)
    if message_tokens:
        return customer_message
    return f"{customer_message} {history_text}"


def _history_to_text(conversation_history: list[Any] | None) -> str:
    if not conversation_history:
        return ""

    parts = []
    for item in conversation_history[-6:]:
        if isinstance(item, dict):
            parts.append(str(item.get("message") or item.get("content") or item.get("text") or ""))
        else:
            parts.append(str(item))
    return " ".join(part for part in parts if part)


def _already_asked_follow_up(history_text: str) -> bool:
    text = _normalize(history_text)
    return any(
        phrase in text
        for phrase in (
            "which product",
            "which item",
            "send the product name",
            "send the name or model",
        )
    )


def _has_phrase(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in STOPWORDS and len(token) > 1}


def _tokens(text: str) -> list[str]:
    normalized = _normalize(text)
    raw_tokens = re.findall(r"[a-z0-9]+", normalized)
    tokens = []
    for token in raw_tokens:
        tokens.append(token)
        if len(token) > 3 and token.endswith("s"):
            tokens.append(token[:-1])
    return tokens


def _normalize(text: str) -> str:
    normalized = text.lower()
    replacements = {
        "hw": "how",
        "mch": "much",
        "u ": "you ",
        " u": " you",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return re.sub(r"\s+", " ", normalized).strip()
