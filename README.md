# Fact Checker Bot 🔎

A Telegram bot that fact-checks forwarded news messages and viral claims.
Forward any post to the bot (or paste the text) and it replies with a verdict:

- ✅ **LIKELY TRUE**
- ❌ **FALSE**
- ⚠️ **MISLEADING**
- ❓ **UNVERIFIABLE**

…plus a confidence level and a short plain-language explanation, in the
language of the original message.

Powered by any OpenAI-compatible chat API (default: **CodeCraft**
`https://codecraftapi.com/v1` running `qwen3.8-max`), with **You.com**
live web search for current-events claims.

## How it works

1. You forward a message (or type a claim) to the bot in Telegram.
2. The bot sends the text to the LLM with a strict fact-checking prompt that
   forces a JSON verdict (`verdict` / `confidence` / `explanation`).
3. If the claim depends on recent events, the model calls the `web_search`
   tool; the bot queries the You.com Web Search API and feeds the snippets
   back for a grounded verdict with sources.
4. The bot renders a verdict card and replies. Unparseable answers become
   UNVERIFIABLE rather than a made-up verdict.

The bot uses **long polling**, so it needs no public URL, domain, or webhook.

> ⚠️ This is an automated AI first pass, not a substitute for real
> verification. Always confirm important claims with primary sources.

## Setup

### 1. Create the bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`,
and copy the bot token.

### 2. Get an LLM API key

You need a key for an OpenAI-compatible provider. The default is
CodeCraft (<https://codecraftapi.com>) — create an API key there and use
it as `LLM_API_KEY`. Any other OpenAI-compatible endpoint works too:
set `LLM_BASE_URL` and `LLM_MODEL` accordingly.

### 3. (Optional) Get a You.com API key for live web search

Sign up at <https://you.com> (Platform → API Keys) and set `YDC_API_KEY`.
Without it the bot still works, but current-events claims are answered
without live web grounding.

### 4. Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="123456:ABC..."
export LLM_API_KEY="your-llm-api-key"
export YDC_API_KEY="your-youcom-key"   # optional

python bot.py
```

### 5. Deploy on Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** and pick this repo.
3. It builds from the included `Dockerfile` (a worker, no port needed).
4. Add the environment variables below to the service.
5. Deploy — the bot starts polling and is live immediately.

### 5b. Deploy on a Linux VPS

One command on a fresh Ubuntu/Debian/RHEL-like server (run from an SSH
session or your provider's web console):

```bash
curl -fsSL https://raw.githubusercontent.com/Retrinaa/Fact-Checker/main/vps-setup.sh | sudo bash
```

The script installs Docker + git, clones this repo into `/opt/fact-checker`,
asks for your tokens (stored in `/etc/fact-checker.env`, mode 600), builds
the image, and starts the bot with `--restart unless-stopped` so it survives
reboots. Re-run it any time to pull the latest code and redeploy.

⚠️ Run only one copy at a time: if Railway is still polling the same bot
token, stop that deployment — two pollers steal each other's updates.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Token from @BotFather |
| `LLM_API_KEY` | ✅ | — | API key for the chat provider (default: CodeCraft) |
| `LLM_BASE_URL` | ❌ | `https://codecraftapi.com/v1` | OpenAI-compatible base URL |
| `LLM_MODEL` | ❌ | `qwen3.8-max` | Model name at the provider |
| `YDC_API_KEY` | ❌ | — | You.com API key — enables live web search |
| `MAX_CLAIM_CHARS` | ❌ | `4000` | Max characters of a message sent to the model |
| `RATE_LIMIT_CHECKS` | ❌ | `10` | Max checks per user per window |
| `RATE_LIMIT_WINDOW_SECONDS` | ❌ | `3600` | Rate-limit window in seconds |

## Project layout

| File | Purpose |
|---|---|
| `bot.py` | Telegram handlers, rate limiting, verdict rendering |
| `factcheck.py` | Tool-calling loop + strict verdict parsing |
| `you_search.py` | Minimal You.com /search REST client (live web search) |
| `config.py` | Environment-based config (no secrets in code) |
| `Dockerfile` | Railway worker image |
worker image |

|---|---|
| `bot.py` | Telegram handlers, rate limiting, verdict rendering |
| `factcheck.py` | Groq call + strict verdict parsing |
| `config.py` | Environment-based config (no secrets in code) |
| `Dockerfile` | Railway worker image |
 parsing |
| `config.py` | Environment-based config (no secrets in code) |
| `Dockerfile` | Railway worker image |
