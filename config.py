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
LLM_API_KEY = _required("LLM_API_KEY")

# --- LLM provider: any OpenAI-compatible endpoint ---
# Default: CodeCraft (https://codecraftapi.com/v1) serving qwen3.8-max.
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://codecraftapi.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.8-max")

# You.com live web search (optional but recommended for news/current events).
# When set, the model may call web_search for claims it can't verify from
# training knowledge alone. Leave empty to disable live search.
YDC_API_KEY = os.environ.get("YDC_API_KEY", "").strip()

# Max characters of a forwarded message sent to the model (cost control).
MAX_CLAIM_CHARS = int(os.environ.get("MAX_CLAIM_CHARS", "4000"))

# Per-user rate limit: max fact-checks per window (cost control).
RATE_LIMIT_CHECKS = int(os.environ.get("RATE_LIMIT_CHECKS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "3600"))
