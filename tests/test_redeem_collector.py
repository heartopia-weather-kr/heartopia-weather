import unittest
from redeem_collector import parse

class RedeemParserTests(unittest.TestCase):
    def test_official_format(self):
        message = {
            "id": "123456789012345678",
            "guild_id": "1128257488375005215",
            "timestamp": "2026-11-09T04:09:00+00:00",
            "content": "🎁Rewards:Wishing star ×3,Mermaid Fish Attractor ×3,Fertilizer ×10\n🔑Gift Code: q8a2n7m5r3k9\n⏰Redemption Deadline:<t:1796313599:f>",
        }
        item = parse(message)
        self.assertEqual(item["code"], "q8a2n7m5r3k9")
        self.assertEqual(item["rewards"], "Wishing star ×3,Mermaid Fish Attractor ×3,Fertilizer ×10")
        self.assertIsNotNone(item["expiresAt"])

    def test_unrelated_message_is_ignored(self):
        self.assertIsNone(parse({"id": "1", "content": "Hello everyone!", "embeds": []}))

    def test_embed_description(self):
        item = parse({"id": "2", "content": "", "embeds": [{"description": "Gift Code: abcdef123\nRewards: Star ×3"}]})
        self.assertEqual(item["code"], "abcdef123")

if __name__ == "__main__":
    unittest.main()
