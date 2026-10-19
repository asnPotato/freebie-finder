import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot

class Tests(unittest.TestCase):
    def test_key_stability(self):
        x = {'source':'site', 'url':'https://example.com/test'}
        self.assertEqual(bot.key_for(x), bot.key_for(x))
        self.assertNotEqual(bot.key_for(x), bot.key_for({'source':'other', 'url':x['url']}))
    def test_date(self):
        self.assertIsNotNone(bot.parse_date('2026-10-18T00:00:00Z'))
        self.assertIsNone(bot.parse_date(None))

if __name__ == '__main__':
    unittest.main()


def test_shopee_title_filter():
    from bot import promising_shopee_title
    assert promising_shopee_title('Shopee 10.10 50% off voucher')
    assert promising_shopee_title('Laptop at ₱25000 price drop')
    assert not promising_shopee_title('My Shopee delivery was lost')
    assert not promising_shopee_title('How do I get a refund?')
