# PendingMattersBot

A MediaWiki bot that tracks Arbitration Committee member activity in ongoing proceedings and publishes summary reports.

## Features

- Pulls the authoritative list of ArbCom members (active & inactive) from `Wikipedia:Arbitration Committee/Members`
- Reads a bullet-list of ongoing matters from a configurable page
- Tracks first comment time, last comment time, and comment count per arbitrator
- Publishes wiki-tables per proceeding with activity statistics

## Setup

### Local Development

1. Create a conda environment:
   ```bash
   conda create -n PendingMattersBot python=3.11
   conda activate PendingMattersBot
   pip install -r requirements.txt
   ```

2. Copy `settings.json.example` to `settings.json` and configure:
   ```bash
   cp settings.json.example settings.json
   # Edit settings.json with your credentials
   ```

### Docker Deployment

1. Build the image:
   ```bash
   docker build -t pendingmattersbot .
   ```

2. Run the bot:
   ```bash
   docker run -e BOT_USER=your_username \
             -e BOT_PASSWORD=your_password \
             pendingmattersbot
   ```

### Railway Deployment

The bot is configured to run on Railway with a cron schedule. Required environment variables:

- `BOT_USER`: Bot username
- `BOT_PASSWORD`: Bot password
- `PROCEEDINGS_PAGE`: Page containing the list of ongoing matters
- `TARGET_PAGE`: Where to publish the report

Optional environment variables:
- `SITE`: MediaWiki site (default: en.wikipedia.org)
- `API_PATH`: API path (default: /w/)
- `USER_AGENT`: Bot user agent
- `COOKIE_PATH`: Path for cookies
- `RUN_INTERVAL`: Run interval in seconds (default: 600)

## License

MIT License 