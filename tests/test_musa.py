import unittest

from salaam.musa import draft_reply, get_business_profile, search_listings


class MusaCoreTests(unittest.TestCase):
    def test_business_profile_loads_demo_store(self):
        profile = get_business_profile()

        self.assertEqual(profile["id"], "demo")
        self.assertEqual(profile["name"], "Musa Demo Gadgets")
        self.assertIn("delivery_rules", profile)

    def test_search_listings_matches_active_product(self):
        result = search_listings("iphone 14 pro")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["id"], "iphone-14-pro-256")

    def test_price_reply_uses_listing_price(self):
        result = draft_reply("hw mch iphone 14 pro")

        self.assertEqual(result["decision"], "reply")
        self.assertEqual(result["intent"], "PRICE_INQUIRY")
        self.assertIn("NGN 980,000", result["message"])
        self.assertIn("iPhone 14 Pro 256GB", result["message"])

    def test_availability_reply_handles_informal_message(self):
        result = draft_reply("u get samsung s23?")

        self.assertEqual(result["decision"], "reply")
        self.assertEqual(result["intent"], "AVAILABILITY_INQUIRY")
        self.assertIn("limited in stock", result["message"])

    def test_unclear_price_gets_follow_up_before_escalation(self):
        result = draft_reply("how much?")

        self.assertEqual(result["decision"], "follow_up")
        self.assertIn("Which product", result["message"])

    def test_repeated_unclear_request_escalates(self):
        result = draft_reply(
            "still how much?",
            conversation_history=[
                {"role": "assistant", "message": "Which product do you want the price for?"}
            ],
        )

        self.assertEqual(result["decision"], "escalate")
        self.assertEqual(result["escalation"]["reason"], "price_without_product_match")
        self.assertIn("owner_alert_text", result["escalation"])

    def test_missing_business_escalates(self):
        result = draft_reply("how much iphone?", business_id="missing")

        self.assertEqual(result["decision"], "escalate")
        self.assertEqual(result["escalation"]["reason"], "business_not_found")

    def test_history_can_disambiguate_short_availability_question(self):
        result = draft_reply(
            "u get am?",
            conversation_history=[
                {"role": "customer", "message": "I want iPhone 14 Pro 256GB"}
            ],
        )

        self.assertEqual(result["decision"], "reply")
        self.assertEqual(result["intent"], "AVAILABILITY_INQUIRY")
        self.assertIn("iPhone 14 Pro 256GB", result["message"])

    def test_location_delivery_reply_uses_business_profile(self):
        result = draft_reply("where is your shop and delivery?")

        self.assertEqual(result["decision"], "reply")
        self.assertEqual(result["intent"], "LOCATION_OR_DELIVERY")
        self.assertIn("Admiralty Way", result["message"])
        self.assertIn("Same-day delivery", result["message"])


if __name__ == "__main__":
    unittest.main()
