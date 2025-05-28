# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

PendingMattersBot is a Python MediaWiki bot that tracks Arbitration Committee member activity in ongoing proceedings and publishes summary reports. The bot analyzes Wikipedia talk pages to extract comment timestamps and generates activity statistics.

## Development Commands

### Setup
```bash
# Create conda environment
conda create -n PendingMattersBot python=3.11
conda activate PendingMattersBot
pip install -r requirements.txt

# Configure settings
cp settings.json.example settings.json
# Edit settings.json with your credentials
```

### Running the Bot
```bash
# Single run (development/testing)
python PendingMattersBot.py --once

# Continuous mode (production)
python PendingMattersBot.py
```

### Docker Development
```bash
# Build image
docker build -t pendingmattersbot .

# Run single execution
docker run -e BOT_USER=username -e BOT_PASSWORD=password pendingmattersbot

# Run continuous mode
docker run -e BOT_USER=username -e BOT_PASSWORD=password pendingmattersbot ""
```

## Architecture

### Core Components

**Main Bot Logic** (`PendingMattersBot.py`):
- `get_arbs()`: Fetches arbitrator list from Wikipedia:Arbitration Committee/Members
- `get_procs()`: Parses proceedings list from configurable page
- `scan()`: Analyzes page sections for user comments and timestamps
- `assemble_report()`: Generates human-readable wikitable reports
- `assemble_data()`: Creates machine-readable template data using MediaWiki switch statements

### Data Flow
1. Fetch current arbitrator list (active/inactive status)
2. Parse list of ongoing proceedings from source page
3. For each proceeding, extract section text and scan for comments
4. Track first comment, last comment, and total count per arbitrator
5. Generate both human-readable report and machine-readable data template
6. Update target pages if content changed

### Configuration
- Settings loaded from `settings.json` with environment variable override support
- Environment variables processed by `start.sh` for containerized deployment
- Configuration includes MediaWiki site, credentials, target pages, and run interval

### Deployment Modes
- **Local Development**: Direct Python execution with settings.json
- **Docker**: Containerized with environment variable configuration
- **Railway**: Scheduled cron execution (every 5 minutes) with restart policy NEVER

### Key Dependencies
- `mwclient`: MediaWiki API interaction
- `mwparserfromhell`: Wikitext parsing
- `requests`: HTTP session management for mwclient

### Output Format
Generates two types of output:
1. **Report page**: Human-readable wikitables with activity status, timestamps, and comment counts
2. **Data page**: MediaWiki template with nested switch statements for programmatic access