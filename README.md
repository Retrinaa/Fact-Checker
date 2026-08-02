# Fact Checker Bot 🔎

A Telegram bot that fact-checks forwarded news messages and viral claims.
Forward any post to the bot (or paste the text) and it replies with a verdict:

- ✅ **LIKELY TRUE**
- ❌ **FALSE**
- ⚠️ **MISLEADING**
- ❓ **UNVERIFIABLE**

…plus a confidence level and a short plain-language explanation, in the
language of the original message.

Powered by [Groq](https://groq.com) running `llama-3.1-8b-instant` —
thousands of checks cost pennies.

## How it works

1. You forward a message (or type a claim) to the bot in Telegram.
2. The bot sends the text to Groq with a strict fact-checking prompt that
   forces a JSON verdict (`verdict` / `confidence` / `explanation`).
3. The bot renders a verdict card and replies. Unparseable answers become
   UNVERIFIABLE rather than a made-up verdict.

The bot uses **long polling**, so it needs no public URL, domain, or webhook.

> ⚠️ This is an automated AI first pass, not a substitute for real
> verification. Always confirm important claims with primary sources.

## Setup

### 1. Create the bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`,
and copy the bot token.

### 2. Get a Groq API key

Sign up at <https://console.groq.com> and create an API key. The free tier
(30 requests/minute) is plenty for light use.

### 3. Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="123456:ABC..."
export GROQ_API_KEY="your-groq-api-key"

python bot.py
```

### 4. Deploy on Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** and pick this repo.
3. It builds from the included `Dockerfile` (a worker, no port needed).
4. Add the environment variables below to the service.
5. Deploy — the bot starts polling and is live immediately.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Token from @BotFather |
| `GROQ_API_KEY` | ✅ | — | API key from console.groq.com |
| `GROQ_MODEL` | ❌ | `llama-3.1-8b-instant` | Groq model to use (e.g. `llama-3.3-70b-versatile` for better accuracy at higher cost) |
| `MAX_CLAIM_CHARS` | ❌ | `4000` | Max characters of a message sent to the model |
| `RATE_LIMIT_CHECKS` | ❌ | `10` | Max checks per user per window |
| `RATE_LIMIT_WINDOW_SECONDS` | ❌ | `3600` | Rate-limit window in seconds |

## Cost

With the default model, a typical check is well under a tenth of a cent
(≈ $0.05 per million input tokens). The per-user rate limit plus
`MAX_CLAIM_CHARS` cap keep the bill tiny even if the bot gets busy.

## Project layout

| File | Purpose |
|---|---|
| `bot.py` | Telegram handlers, rate limiting, verdict rendering |
| `factcheck.py` | Groq call + strict verdict parsing |
| `config.py` | Environment-based config (no secrets in code) |
| `Dockerfile` | Railway worker image |
