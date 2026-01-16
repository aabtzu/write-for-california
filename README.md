# Write For California - DBD Admin Tools

Tools for managing and analyzing DBD (Daily Discussion Board) posts on [Write For California](https://writeforcalifornia.com).

## Features

- **Monitor** - Real-time notifications when new comments appear on the daily DBD post
- **Scraper** - Collect historical data from DBD posts (comments, unique commenters, poll IDs)
- **Charts** - Generate visualizations of DBD activity over time

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
    ├── config.py      # Shared configuration
    ├── utils.py       # Shared utilities
    ├── monitor.py     # Comment monitor
    ├── scraper.py     # Historical data scraper
    └── charts.py      # Data visualization
```

## State Files

All state and data files are stored in `~/.wfc/`:
- `monitor_state` - Current monitored URL and comment count
- `dbd_history.db` - SQLite database with historical data
- `charts/` - Generated chart images
- `monitor.log` - Monitor service logs
