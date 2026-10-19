# Freebie Finder (PH)

A small freebie watcher that checks Epic Games' PH promotional feed plus public Reddit Atom feeds for games, software and PH promos, sending **new** leads to Telegram. No Grok account, paid API or Python packages required. It is a lead finder, not a guarantee that a promotion is safe or eligible.

## Setup (phone or computer)

1. Create a Telegram bot: open https://t.me/BotFather, run `/newbot` and save the **token** privately. Start a chat with your new bot and send `/start`.
2. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser, replacing `<YOUR_TOKEN>`, and find `message.chat.id` from the JSON response. Use the numeric ID for your own private conversation; send another message if the result is empty. Don't share the token or this URL.
3. Create a **public** GitHub repository named `freebie-finder`. From this downloaded ZIP, upload `bot.py`, `README.md` and `.github/workflows/freebie-finder.yml`, retaining the folder structure. GitHub's web upload UI can miss nested hidden folders; using Git or the GitHub web editor's *Create new file* with the exact path `.github/workflows/freebie-finder.yml` works reliably.
4. Under repository **Settings → Secrets and variables → Actions → New repository secret**, create `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Never add your secrets to repository files.
5. Go to **Actions → Freebie Finder → Run workflow**. The first run seeds existing items and sends one welcome message. New eligible candidates are sent on later scans.
6. Runs are scheduled at `17 */3 * * *` UTC, corresponding to **01:17, 04:17, 07:17, 10:17, 13:17, 16:17, 19:17, 22:17 Manila time**. The platform may delay runs.

## Details and limitations

- Official Epic feed queries country `PH`. It requires an active promotion window and nonzero original price, so it excludes permanently free-to-play games.
- Reddit sources are community submissions, not verified merchant offers. The bot labels them unverified; always inspect the destination, date, region restrictions, terms, payment requirements and reviews.
- Software and PH deals feeds are best-effort discovery. One or more feeds may be blocked/rate limited. An isolated source failure does not stop the rest.
- A title keyword filter excludes obvious trials, expired posts and giveaways that require purchases, but it can produce false positives and miss some deals. It does **not** verify redemption or expiry for Reddit offers.
- No purchases, account registrations, or claims are performed automatically. Do not provide passwords, OTPs or card details to deal sites.
- Data state is committed to `seen.json`; after the first run it only alerts on unseen links, limited to 15 alerts per run. Excess alerts will be reconsidered in the next scan. This tracking file is public in a public repository, though it contains only item hashes and scan times.
- Public GitHub Actions runners are currently free; public-repo schedules can deactivate after 60 days of inactivity, but this bot's regular state updates often keep it active. Check Actions if messages stop.

## Test locally

With Python 3.12+, set environment variables `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then run `python bot.py`. The first execution creates `seen.json` and sends a welcome message.

## Privacy

Create and own the GitHub repository yourself. Store your Telegram bot token **only** as a GitHub Actions secret. If the token leaks, revoke it with BotFather. Keep `seen.json` but do not commit or expose credentials.

## Shopee deal alerts (new)

The bot now monitors the **new-post feeds** from `r/AtinAtinLang`, `r/ShopeePH` and
`r/awesamrecosph` for potential Shopee bargains, vouchers and flash sales.
It reports **community leads, not verified bargains**: it cannot calculate a
real historic discount, authenticate a seller, or check an account-specific
voucher, stock or checkout total. Always check product variations, original
price, Shopee Mall/authorized store status, shipping, voucher ceilings and
actual checkout price. Do not treat price-error posts as redeemable offers.

To watch an **exact Reddit discussion thread**, set the optional GitHub Actions
repository **variable** `REDDIT_DEALS_THREAD_URL` to a Reddit comments URL,
e.g. `https://www.reddit.com/r/ShopeePH/comments/POST_ID/title/`.
Then add `REDDIT_DEALS_THREAD_URL: ${{ vars.REDDIT_DEALS_THREAD_URL }}` to
the workflow step's `env:` section (already configured in the supplied workflow).
The thread's RSS comments are treated as community candidates. Reddit can
throttle or reject automated RSS requests; the bot warns and continues with
other sources. Avoid aggressive polling or bypassing access controls.
