# Write For California - DBD Admin Tools

Tools for managing and analyzing DBD (Daily Bear Dump) posts on [Write For California](https://writeforcalifornia.com).

## Features

- **Monitor** - Real-time notifications when new comments appear on the daily DBD post
- **Scraper** - Collect historical data from DBD posts (comments, unique commenters, poll IDs)
- **Charts** - Generate visualizations of DBD activity over time
- **DBD Automation** - Create and schedule DBD posts with polls via Substack API

## Installation

```bash
cd /path/to/write_for_california
pip install -e .
```

## Usage

### Monitor

Watches the latest DBD post and sends macOS alerts when new comments appear.

```bash
# Run manually
python3 -m wfc.monitor

# Or use the installed command
wfc-monitor
```

Active hours: 6am - 6pm (configurable in `wfc/config.py`)

#### Persistent Background Service (macOS)

The monitor can run as a launchd service that starts automatically on login:

```bash
# Start the service
launchctl load ~/Library/LaunchAgents/com.wfc.monitor.plist

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.wfc.monitor.plist

# Check status
launchctl list | grep wfc

# View logs
tail -f ~/.wfc/monitor.log
```

### Scraper

Collect historical DBD data for analysis.

```bash
# Scrape all posts from a year
python3 -m wfc.scraper --year 2025

# With longer delay to avoid rate limiting
python3 -m wfc.scraper --year 2025 --delay 2.0

# Export to CSV
python3 -m wfc.scraper --year 2025 --export

# Show top commenters
python3 -m wfc.scraper --top-commenters 20
```

Data is stored in `~/.wfc/dbd_history.db` (SQLite).

### Charts

Generate visualizations from scraped data.

```bash
# Scatter plot of daily activity (comments + unique commenters)
python3 -m wfc.charts --type line --start 2025-01-01

# Histogram of unique commenters distribution
python3 -m wfc.charts --type histogram

# Save without displaying
python3 -m wfc.charts --type line --no-show --save my_chart.png
```

Charts are saved to `~/.wfc/charts/`.

### DBD Automation

Create and schedule DBD posts with polls via Substack's API.

**Note:** The `wfc-dbd` command is installed when you run `pip install -e .` - it's defined as an entry point in `pyproject.toml`, not as a standalone script file.

#### Create New Post

Generates step-by-step instructions for creating a DBD post via browser automation:

```bash
# Generate automation instructions for a new post
wfc-dbd post --date 2026-01-26 --subject "Topic of the day"

# With lede photo and poll
wfc-dbd post --date 2026-01-26 --subject "Topic" \
    --lede-photo "https://example.com/photo.jpg" \
    --poll-question "Today's question" \
    --poll-option "Option 1" --poll-option "Option 2"

# Output as JSON (for programmatic use)
wfc-dbd post --date 2026-01-26 --subject "Topic" --json
```

This outputs detailed instructions for each step: navigating to editor, setting content via API, configuring scheduling, and publishing.

#### Add Poll to Existing Post

Once you have a post (and its post ID), generate JavaScript to add a poll:

```bash
# Generate poll creation script for a specific post
wfc-dbd poll --post-id 185679050 \
    --question "What's your favorite?" \
    --option "Option A" \
    --option "Option B" \
    --option "Option C"

# With custom expiry time (default is 24 hours)
wfc-dbd poll --post-id 185679050 \
    --question "Quick poll" \
    --option "Yes" --option "No" \
    --expiry 12
```

This outputs JavaScript that:
1. Creates a new poll via the Substack API
2. Fetches the current draft content
3. Inserts the poll before the subscribe widget
4. Updates the draft with the new content

To use: Copy the output, open the post in Substack editor, open browser DevTools (Cmd+Option+I), paste in Console, press Enter.

## Data Collected

For each DBD post:
- Post date and title
- Total comment count
- Unique commenters count
- Cover image URL (if present)
- Poll ID (if present)
- Per-user comment counts

## Project Structure

```
write_for_california/
├── pyproject.toml
├── README.md
└── wfc/
    ├── __init__.py
    ├── config.py           # Shared configuration
    ├── utils.py            # Shared utilities
    ├── monitor.py          # Comment monitor
    ├── scraper.py          # Historical data scraper
    ├── charts.py           # Data visualization
    ├── dbd_automation.py   # DBD post creation & poll scripts
    └── dbd_browser_steps.py # Browser automation helpers
```

## Browser Extension

A Chrome extension that monitors DBD pages for "new reply" badges and sends desktop notifications.

### Installation

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `extension/` folder from this repo

The extension will:
- Monitor any open DBD page for "new reply" indicators
- Send desktop notifications when new replies appear
- Play a sound alert

## State Files

All state and data files are stored in `~/.wfc/`:
- `monitor_state` - Current monitored URL and comment count
- `dbd_history.db` - SQLite database with historical data
- `charts/` - Generated chart images
- `monitor.log` - Monitor service logs
