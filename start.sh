#!/bin/sh

# Validate required environment variables
if [ -z "$BOT_USER" ]; then
    echo "ERROR: BOT_USER environment variable is not set" >&2
    exit 1
fi

if [ -z "$BOT_PASSWORD" ]; then
    echo "ERROR: BOT_PASSWORD environment variable is not set" >&2
    exit 1
fi

# Generate settings.json from environment variables
cat > settings.json << EOF
{
  "site": "${SITE:-en.wikipedia.org}",
  "path": "${API_PATH:-/w/}",
  "user": "${BOT_USER}",
  "bot_password": "${BOT_PASSWORD}",
  "ua": "${USER_AGENT:-KevinClerkBot‑t2/0.1 (+https://github.com/L235/WordcountClerkBot)}",
  "cookie_path": "${COOKIE_PATH:-/app/cookies/cookies.txt}",
  "proceedings_page": "${PROCEEDINGS_PAGE:-User:KevinClerkBot/Ongoing proceedings}",
  "target_page": "${TARGET_PAGE:-User:KevinClerkBot/ArbCom activity}",
  "run_interval": ${RUN_INTERVAL:-600}
}
EOF

# Run the bot
exec python PendingMattersBot.py "$@" 