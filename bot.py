"""Freebie Finder: lightweight, no external Python dependencies."""
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

STATE = Path(__file__).parent / 'seen.json'
UA = 'FreebieFinder/1.0 (personal RSS reader; contact: repo owner)'
NOW = dt.datetime.now(dt.timezone.utc)
FEEDS = [
    ('Games', 'FreeGameFindings', 'https://www.reddit.com/r/FreeGameFindings/new/.rss'),
    ('Software', 'FreeSoftware', 'https://www.reddit.com/r/FreeSoftware/new/.rss'),
    ('Promos', 'PH deals', 'https://www.reddit.com/r/awesamrecosph/new/.rss'),
    ('Shopee Deals', 'r/AtinAtinLang', 'https://www.reddit.com/r/AtinAtinLang/new/.rss'),
    ('Shopee Deals', 'r/ShopeePH', 'https://www.reddit.com/r/ShopeePH/new/.rss'),
    ('Shopee Deals', 'r/awesamrecosph', 'https://www.reddit.com/r/awesamrecosph/new/.rss'),
]
KEYWORDS = {
    'Games': ('[steam]', '[epic', '[gog]', '[itch', '[ubisoft]', '[pc', '[origin]', '[xbox]', '[playstation]', '[ios', '[android]', 'game', 'dlc'),
    'Software': ('free', 'giveaway', 'license', 'open source', 'open-source', 'lifetime', '100% off'),
    'Promos': ('free', 'freebie', 'voucher', 'cashback', 'promo', 'discount', 'credit', 'giveaway', 'coupon', '₱0', 'php 0'),
    'Shopee Deals': ('shopee', 'shapi', 'spaylater', 'voucher', 'discount', 'flash sale', 'price drop', 'price error', 'sale', 'deal', 'steal', 'budol', 'cashback', '₱', 'php ', 'off'),
}
SHOPEE_STRONG = ('shopee', 'shapi', 'spaylater', 'voucher', 'discount', 'flash sale', 'price drop', 'price error', 'sale', 'deal', 'steal', 'budol', 'cashback', '₱', 'php ', ' off', '8.8', '9.9', '10.10', '11.11', '12.12')
SHOPEE_NOISE = ('scam', 'fake', 'refund', 'return', 'courier', 'delivery', 'lost parcel', 'seller issue', 'help', 'question', 'rant', 'review', 'cancelled', 'canceled', 'shipping issue')
EXCLUDE = ('giveaway ended', 'expired', 'ended giveaway', 'scam alert', 'upcoming', 'coming soon', 'amazon prime required', 'prime gaming', 'free trial', 'trial only', 'subscription required', 'with purchase', 'minimum spend')


def request_json(url, method='GET', payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'User-Agent': UA, 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=18) as res:
        return json.load(res)


def request_xml(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/atom+xml, application/rss+xml'})
    with urllib.request.urlopen(req, timeout=18) as res:
        return ET.fromstring(res.read(2_000_000))


def parse_date(value):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        return None


def epic_offers():
    url = 'https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=PH&allowCountries=PH'
    data = request_json(url)
    elements = data['data']['Catalog']['searchStore']['elements']
    results = []
    for item in elements:
        prices = (item.get('price') or {}).get('totalPrice') or {}
        if prices.get('discountPrice') != 0 or not (prices.get('originalPrice') or 0) > 0:
            continue
        promotions = (item.get('promotions') or {}).get('promotionalOffers') or []
        active = False
        expiry = None
        for group in promotions:
            for offer in group.get('promotionalOffers') or []:
                start = parse_date(offer.get('startDate'))
                end = parse_date(offer.get('endDate'))
                if start and end and start <= NOW < end:
                    active = True
                    expiry = end.isoformat()
        if not active:
            continue
        slug = item.get('productSlug') or item.get('urlSlug') or ''
        mappings = item.get('catalogNs') or {}
        if isinstance(mappings, dict):
            mm = mappings.get('mappings') or []
            if mm and isinstance(mm[0], dict):
                slug = mm[0].get('pageSlug') or slug
        link = 'https://store.epicgames.com/en-US/free-games'
        if slug and not slug.startswith('http') and '/' not in slug:
            link = 'https://store.epicgames.com/en-US/p/' + urllib.parse.quote(slug)
        results.append({'category': 'Games', 'source': 'Epic Games (PH)', 'title': item.get('title','Free Epic game'), 'url': link, 'end': expiry, 'verified': 'Official promotional listing'})
    return results


def promising_shopee_title(title):
    low = title.lower()
    # Candidate discovery only: no claim of a verified price or genuine bargain.
    if any(term in low for term in SHOPEE_NOISE):
        return False
    return any(term in low for term in SHOPEE_STRONG)


def feed_offers(category, source, url):
    root = request_xml(url)
    atom = '{http://www.w3.org/2005/Atom}'
    output = []
    for entry in root.findall(f'{atom}entry'):
        title = html.unescape(''.join(entry.findtext(f'{atom}title', default='')).strip())
        low = title.lower()
        if category == 'Shopee Deals':
            if not promising_shopee_title(title):
                continue
        elif not any(word in low for word in KEYWORDS[category]) or any(term in low for term in EXCLUDE):
            continue
        published = parse_date(entry.findtext(f'{atom}published') or entry.findtext(f'{atom}updated'))
        if published and (NOW - published).total_seconds() > 4 * 86400:
            continue
        link = next((e.attrib.get('href','') for e in entry.findall(f'{atom}link') if e.attrib.get('rel') == 'alternate'), '')
        if not link.startswith('https://www.reddit.com/'):
            continue
        status = 'Community deal lead — price, seller, voucher, shipping and stock NOT verified' if category == 'Shopee Deals' else 'Unverified community post'
        output.append({'category': category, 'source': source + ' (community)', 'title': title[:240], 'url': link, 'verified': status})
    return output


def key_for(item):
    return hashlib.sha256((item['source'] + '\x00' + item['url']).encode()).hexdigest()[:24]


def send_telegram(token, chat_id, item):
    note = ('Ends: ' + item['end'][:10] + ' UTC\n') if item.get('end') else ''
    message = f"{item['category']} | {item['source']}\n{item['title']}\n{note}{item['verified']} — check PH eligibility and terms before redeeming.\n{item['url']}"
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    reply = request_json(url, method='POST', payload={'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True})
    if not reply.get('ok'):
        raise RuntimeError('Telegram declined the message')


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        raise SystemExit('Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as repository secrets.')
    seen = json.loads(STATE.read_text()) if STATE.exists() else {}
    offers = []
    successful = 0
    feeds = list(FEEDS)
    # Optional exact Reddit thread RSS feed, e.g. https://www.reddit.com/r/ShopeePH/comments/POST_ID/title/.rss
    custom_thread = os.environ.get('REDDIT_DEALS_THREAD_URL', '').strip()
    if custom_thread:
        parsed = urllib.parse.urlparse(custom_thread)
        if parsed.scheme != 'https' or parsed.hostname not in ('www.reddit.com', 'reddit.com') or not re.match(r'^/r/[A-Za-z0-9_]+/comments/[A-Za-z0-9]+/', parsed.path):
            raise SystemExit('Invalid REDDIT_DEALS_THREAD_URL: use a reddit.com subreddit comments thread URL')
        feeds.append(('Shopee Deals', 'Custom deal thread', 'https://www.reddit.com' + parsed.path.rstrip('/') + '/.rss'))
    for category, source, feed in feeds:
        try:
            found = feed_offers(category, source, feed)
            print(f'{source}: {len(found)} candidate offers')
            offers.extend(found)
            successful += 1
        except Exception as exc:
            print(f'WARNING {source}: {exc}', file=sys.stderr)
    try:
        found = epic_offers()
        offers.extend(found)
        successful += 1
        print(f'Epic Games: {len(found)} live promotions')
    except Exception as exc:
        print(f'WARNING Epic Games: {exc}', file=sys.stderr)
    source_total = len(feeds) + 1
    if not successful:
        raise SystemExit('Every source failed; refusing to update state')
    fresh = []
    for offer in offers:
        k = key_for(offer)
        if k not in seen:
            fresh.append((k, offer))
    # First successful run seeds current entries; no initial message flood.
    first_run = not STATE.exists()
    max_per_run = int(os.environ.get('MAX_ALERTS', '15'))
    sent = 0
    for key, offer in fresh:
        if first_run:
            seen[key] = NOW.isoformat()
        elif sent < max_per_run:
            send_telegram(token, chat, offer)
            seen[key] = NOW.isoformat()
            sent += 1
    # Keep 45 days of history.
    cutoff = NOW - dt.timedelta(days=45)
    seen = {k: v for k,v in seen.items() if (parse_date(v) or NOW) > cutoff}
    STATE.write_text(json.dumps(seen, indent=2, sort_keys=True) + '\n')
    print(f'Sources responding: {successful}/{source_total}; new candidates: {len(fresh)}; alerts sent: {sent}; initial seed: {first_run}')
    if first_run:
        request_json(f'https://api.telegram.org/bot{token}/sendMessage', method='POST', payload={'chat_id': chat, 'text': f'Freebie Finder is active. Monitoring {successful}/{source_total} sources every 3 hours. Existing posts were marked as seen; future discoveries will be sent here.'})

if __name__ == '__main__':
    main()
