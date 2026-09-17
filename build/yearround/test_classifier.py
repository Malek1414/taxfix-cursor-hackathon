"""Tests for the Tap n' tax classifier: python3 -m unittest build.yearround.test_classifier"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from classifier import decide, learn, AUTO_LIMIT_EUR

SOFT = {"merchant": "Adobe", "amount": 59.49, "card": "Business Visa 4821"}
SHOP = {"merchant": "REWE", "amount": 38.40, "card": "Business Visa 4821"}


class Classifier(unittest.TestCase):
    def test_first_time_on_a_clear_trade_asks_once(self):
        self.assertEqual(decide(SOFT, {})["action"], "ask")

    def test_repeat_on_a_clear_trade_stops_asking(self):
        mem = {}
        learn(SOFT, "business", mem); learn(SOFT, "business", mem)
        d = decide(SOFT, mem)
        self.assertEqual(d["action"], "auto")
        self.assertEqual(d["category"], "software")

    def test_an_ambiguous_merchant_never_goes_auto(self):
        mem = {}
        for _ in range(5):
            learn(SHOP, "business", mem)
        self.assertEqual(decide(SHOP, mem)["action"], "ask")

    def test_big_amounts_always_ask(self):
        mem = {}
        learn(SOFT, "business", mem); learn(SOFT, "business", mem)
        self.assertEqual(decide({**SOFT, "amount": AUTO_LIMIT_EUR + 1}, mem)["action"], "ask")

    def test_an_outlier_asks_again(self):
        mem = {}
        learn(SOFT, "business", mem); learn(SOFT, "business", mem)
        self.assertEqual(decide({**SOFT, "amount": 59.49 * 3}, mem)["action"], "ask")

    def test_private_card_at_an_ambiguous_merchant_never_interrupts(self):
        self.assertEqual(decide({"merchant": "REWE", "amount": 21.0, "card": "Visa 1111"}, {})["action"], "skip")

    def test_changing_the_answer_resets_the_count(self):
        mem = {}
        learn(SOFT, "business", mem); learn(SOFT, "business", mem)
        learn(SOFT, "private", mem)
        self.assertEqual(mem["merchants"][list(mem["merchants"])[0]]["count"], 1)

    def test_every_decision_explains_itself(self):
        for d in (decide(SOFT, {}), decide(SHOP, {})):
            self.assertTrue(d["reason"])


if __name__ == "__main__":
    unittest.main()
