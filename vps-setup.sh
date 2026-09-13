#!/usr/bin/env bash
# Fact Checker bot — one-command setup for a fresh Linux VPS.
#
# Works on Ubuntu / Debian (apt) and RHEL-likes (dnf/yum). Needs a real
# terminal for the first-run prompts (SSH session or provider web console).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Retrinaa/Fact-Checker/main/vps-setup.sh | sudo bash
#   — or, from a checkout of this repo —
#   sudo bash vps-setup.sh
#
# Re-running the script updates the code and restarts the bot.

set -euo pipefail

REPO_URL="https://github.com/Retrinaa/Fact-Checker.git"
APP_DIR="/opt/fact-checker"
ENV_FILE="/etc/fact-checker.env"
CONTAINER="fact-checker"
IMAGE="fact-checker"

log() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root, e.g.: sudo bash $0" >&2
  exit 1
fi

# --- 1. Docker -------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker…"
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker || true
else
  log "Docker already installed."
fi

# --- 2. Git ----------------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  log "Installing git…"
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y -qq git
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y git
  elif command -v yum >/dev/null 2>&1; then
    yum install -y git
  else
    echo "No supported package manager found to install git." >&2
    exit 1
  fi
fi

# --- 3. Code ---------------------------------------------------------------
if [ -d "$APP_DIR/.git" ]; then
  log "Updating code in $APP_DIR…"
  git -C "$APP_DIR" pull --ff-only
else
  log "Cloning $REPO_URL into $APP_DIR…"
  git clone "$REPO_URL" "$APP_DIR"
fi

# --- 4. Secrets ------------------------------------------------------------
read_var() { # $1=var name  $2=prompt text  $3=allow empty (optional)
  local value=""
  while true; do
    printf '%s: ' "$2" > /dev/tty
    read -r value < /dev/tty
    if [ -n "$value" ] || [ "${3:-}" = "allow-empty" ]; then break; fi
  done
  echo "$value"
}

if [ ! -f "$ENV_FILE" ]; then
  log "First-time setup — enter your secrets (stored only in $ENV_FILE, mode 600):"
  TELEGRAM_BOT_TOKEN="$(read_var TELEGRAM_BOT_TOKEN 'Telegram bot token (from @BotFather)')"
  LLM_API_KEY="$(read_var LLM_API_KEY 'LLM provider API key (default provider: codecraftapi.com)')"
  LLM_BASE_URL="$(read_var LLM_BASE_URL 'LLM base URL [Enter = https://codecraftapi.com/v1]' allow-empty)"
  LLM_BASE_URL="${LLM_BASE_URL:-https://codecraftapi.com/v1}"
  LLM_MODEL="$(read_var LLM_MODEL 'LLM model [Enter = qwen3.8-max]' allow-empty)"
  LLM_MODEL="${LLM_MODEL:-qwen3.8-max}"
  YDC_API_KEY="$(read_var YDC_API_KEY 'You.com API key for web search (optional, Enter to skip)' allow-empty)"
  umask 077
  {
    echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
    echo "LLM_API_KEY=$LLM_API_KEY"
    echo "LLM_BASE_URL=$LLM_BASE_URL"
    echo "LLM_MODEL=$LLM_MODEL"
    if [ -n "$YDC_API_KEY" ]; then
      echo "YDC_API_KEY=$YDC_API_KEY"
    fi
  } > "$ENV_FILE"
  log "Secrets saved to $ENV_FILE."
else
  log "Using existing secrets from $ENV_FILE (delete it to re-enter)."
fi

# --- 5. Build & run --------------------------------------------------------
log "Building image…"
docker build -q -t "$IMAGE" "$APP_DIR"

log "(Re)starting container…"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  --env-file "$ENV_FILE" \
  "$IMAGE" >/dev/null

sleep 3
log "Container status:"
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Status}}'
echo
log "Last log lines:"
docker logs --tail 10 "$CONTAINER" 2>&1 || true

cat <<'MSG'

✅ Fact Checker bot is deployed and running.
   It restarts automatically on crash and on server reboot.

Handy commands:
  docker logs -f fact-checker     # watch live logs
  docker restart fact-checker     # restart the bot
  sudo bash vps-setup.sh          # re-run to pull latest code + redeploy

⚠️  Run only ONE copy of the bot at a time: if the Railway deployment is
   still active, stop it — two pollers on the same bot token steal each
   other's updates and replies become random.
MSG
