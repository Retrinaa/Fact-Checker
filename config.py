"""Configuration for the Fact Checker bot.

All secrets come from environment variables only. Nothing sensitive is
hard-coded here, so this file is safe to commit to a public repo.
"""

import os
import sys


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"FATAL: required environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


# --- Required secrets (set these in Railway / your shell, never in code) ---
TELEGRAM_BOT_TOKEN = _required("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = _required("GROQ_API_KEY")

# --- Optional knobs with sensible defaults ---
# Cheapest Groq model; good enough for classification + short explanations.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Exa live web search (optional but recommended for news/current events).
# When set, the model may call web_search for claims it can't verify from
# training knowledge alone. Leave empty to disable live search.
EXA_API_KEY = os.environ.get("EXA_API_KEY", "").strip()

# Max characters of a forwarded message sent to the model (cost control).
MAX_CLAIM_CHARS = int(os.environ.get("MAX_CLAIM_CHARS", "4000"))

# Per-user rate limit: max fact-checks per window (cost control).
RATE_LIMIT_CHECKS = int(os.environ.get("RATE_LIMIT_CHECKS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "3600"))
