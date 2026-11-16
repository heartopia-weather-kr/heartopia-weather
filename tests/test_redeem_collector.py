import unittest
from redeem_collector import parse, merge_items, parse_expiry

class RedeemParserTests(unittest.TestCase):
    def message(self, content, id="123", **extra):
        return {"id": id, "guild_id": "999", "timestamp": "2026-11-16T05:12:34+00:00", "content": content, **extra}

    def test_official_format(self):
        item = parse(self.message("🎁Rewards:Wishing star ×3,Mermaid Fish Attractor ×3,Fertilizer ×10\n🔑Gift Code: q8a2n7m5r3k9\n⏰Redemption Deadline:<t:1796313599:f>"))
        self.assertEqual(item["code"], "q8a2n7m5r3k9")
        self.assertIn("소원별 ×3", item["rewards"])
        self.assertIsNotNone(item["expiresAt"])

    def test_unrelated_and_teaser_ignored(self):
        self.assertIsNone(parse(self.message("New patch notes and event gifts!")))
        self.assertIsNone(parse(self.message("Gift Code: coming soon!")))
        self.assertIsNone(parse(self.message("리딤 코드 공개 예정!")))

    def test_embed_description(self):
        item = parse(self.message("", embeds=[{"description": "Gift Code: abcdef123\nRewards: Star ×3"}]))
        self.assertEqual(item["code"], "abcdef123")

    def test_announcement_freebies(self):
        item = parse(self.message("Freebies are ready, don't forget to claim them:\n🌠 Wishing star ×3\n🎣 Mermaid Fish Attractor ×3\n🌱 Fertilizer ×10\n🎁 Gift Code: m3r9k6a4q2n7\nRedemption Deadline: 12/4/26, 00:59"))
        self.assertIn("소원별 ×3", item["rewards"])
        self.assertIn("인어 집어기 ×3", item["rewards"])
        self.assertEqual(item["expiresAt"], "2026-12-03T15:59:00+00:00")

    def test_korean_notice(self):
        item = parse(self.message("🎁 선물 목록\n🌠 소원별 x3\n🎣 인어 집어기 x3\n🌱 비료 x10\n🎁 리딤 코드: ab12cd34\n⏰ 사용 기한: 2026년 12월 4일 00:59까지 (KST)"))
        self.assertEqual(item["code"], "ab12cd34")
        self.assertIn("비료 x10", item["rewards"])
        self.assertEqual(item["expiresAt"], "2026-12-03T15:59:00+00:00")

    def test_duplicate_merge_preserves_information(self):
        a = parse(self.message("Gift Code: abc12345\nRedemption Deadline: 12/4/26, 00:59", "1"))
        b = parse(self.message("Rewards: Wishing star ×3\nGift Code: abc12345", "2"))
        merged = merge_items(a, b)
        self.assertIn("소원별", merged["rewards"])
        self.assertEqual(merged["expiresAt"], a["expiresAt"])
        self.assertEqual(merged["postedAt"], a["postedAt"])

    def test_unrecognized_deadline_not_invented(self):
        self.assertIsNone(parse_expiry("soon"))

if __name__ == "__main__":
    unittest.main()
