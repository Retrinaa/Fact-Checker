"""Telegram Fact Checker bot.

Forward any news message (or just type/paste a claim) and the bot replies
with a verdict card: LIKELY TRUE / FALSE / MISLEADING / UNVERIFIABLE,
confidence, and a short plain-language explanation.

Runs with long polling, so it needs no public URL or webhook — perfect for
a Railway worker service.
"""

import logging
import time
from collections import defaultdict, deque

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from factcheck import check_claim

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("fact-checker")

# In-memory per-user rate limiting: user_id -> deque of timestamps.
_usage: dict[int, deque] = defaultdict(deque)

DISCLAIMER = (
    "\n\n<i>Automated check by an AI model — treat as a first pass, "
    "not gospel. For important claims, verify with primary sources.</i>"
)

HELP_TEXT = (
    "🔎 <b>Fact Checker bot</b>\n\n"
    "Forward me any news post, rumor, or viral claim — or just paste the text — "
    "and I'll tell you whether it looks true, false, misleading, or unverifiable.\n\n"
    "• Works best with clear factual claims.\n"
    "• Opinions, jokes, and personal messages can't be checked.\n"
    "• I answer in the language of the message.\n\n"
    "Commands: /start /help"
)


def _rate_limited(user_id: int) -> bool:
    """True if the user has exceeded their allowance in the current window."""
    now = time.time()
    window = _usage[user_id]
    while window and now - window[0] > config.RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= config.RATE_LIMIT_CHECKS:
        return True
    window.append(now)
    return False


def _extract_claim(update: Update) -> str | None:
    """Get the text to check from a message (plain text or media caption)."""
    msg = update.effective_message
    if msg is None:
        return None
    text = (msg.text or msg.caption or "").strip()
    return text or None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(HELP_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_html(HELP_TEXT)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    claim = _extract_claim(update)
    if not claim:
        await msg.reply_html(
            "I can only check text (or a caption on a photo/video). "
            "Forward me a text post or add a caption describing the claim."
        )
        return

    if _rate_limited(user.id):
        await msg.reply_html(
            f"⏳ You've hit the limit of {config.RATE_LIMIT_CHECKS} checks per hour. "
            "Try again a bit later."
        )
        return

    await context.bot.send_chat_action(chat_id=msg.chat_id, action=ChatAction.TYPING)
    status = await msg.reply_html("🔎 Checking…")

    # The Groq call is blocking; run it in a thread so the bot stays responsive.
    import asyncio

    verdict = await asyncio.to_thread(check_claim, claim)

    searched_line = " <i>(with live web search)</i>" if verdict.searched else ""
    reply = (
        f"{verdict.emoji} <b>{verdict.verdict}</b> "
        f"<i>(confidence: {verdict.confidence})</i>{searched_line}\n\n"
        f"{verdict.explanation}"
    )
    if verdict.sources:
        links = "\n".join(
            f'• <a href="{u}">{u.split("//", 1)[-1].split("/", 1)[0]}</a>' for u in verdict.sources
        )
        reply += f"\n\n<b>Sources:</b>\n{links}"
    reply += DISCLAIMER

    try:
        await status.edit_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        # Fallback if HTML in the explanation breaks formatting.
        plain = (
            f"{verdict.emoji} {verdict.verdict} (confidence: {verdict.confidence})"
            f"{' (with live web search)' if verdict.searched else ''}\n\n"
            f"{verdict.explanation}\n\n"
        )
        if verdict.sources:
            plain += "Sources:\n" + "\n".join(verdict.sources) + "\n\n"
        plain += "Automated AI check — verify important claims with primary sources."
        await status.edit_text(plain, disable_web_page_preview=True)


def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("Fact Checker bot starting (long polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
