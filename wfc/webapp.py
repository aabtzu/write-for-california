#!/usr/bin/env python3
"""
WFC Web App
Simple web interface to view DBD data and charts.
Uses Flask with Jinja2 templates for hot-reload during development.
"""

import io
import base64
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from flask import Flask, render_template, request

from .config import STATE_DIR
from . import queries as Q

DB_PATH = STATE_DIR / "dbd_history.db"
PORT = 8080

# Flask app setup
app = Flask(__name__)


def get_daily_data(start_date=None, end_date=None):
    """Get comment counts and unique commenters by date."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if start_date and end_date:
        c.execute(Q.DAILY_DATA_WITH_RANGE, (start_date, end_date))
    elif start_date:
        c.execute(Q.DAILY_DATA_WITH_START, (start_date,))
    else:
        c.execute(Q.DAILY_DATA_ALL)

    rows = c.fetchall()
    conn.close()
    return rows


def get_top_commenters(limit=20, start_date=None, end_date=None):
    """Get top commenters across posts in date range."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if start_date and end_date:
        c.execute(Q.TOP_COMMENTERS_WITH_RANGE, (start_date, end_date, limit))
    elif start_date:
        c.execute(Q.TOP_COMMENTERS_WITH_START, (start_date, limit))
    else:
        c.execute(Q.TOP_COMMENTERS_ALL, (limit,))

    results = c.fetchall()
    conn.close()
    return [{'username': r[0], 'total': r[1], 'posts': r[2]} for r in results]


def get_stats(start_date=None, end_date=None):
    """Get overall statistics for date range."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if start_date and end_date:
        c.execute(Q.STATS_POST_COUNT_RANGE, (start_date, end_date))
        total_posts = c.fetchone()[0]

        c.execute(Q.STATS_TOTAL_COMMENTS_RANGE, (start_date, end_date))
        total_comments = c.fetchone()[0] or 0

        c.execute(Q.STATS_AVG_COMMENTS_RANGE, (start_date, end_date))
        avg_comments = c.fetchone()[0] or 0

        c.execute(Q.STATS_AVG_UNIQUE_RANGE, (start_date, end_date))
        avg_unique = c.fetchone()[0] or 0

        c.execute(Q.STATS_UNIQUE_COMMENTERS_RANGE, (start_date, end_date))
        total_unique_commenters = c.fetchone()[0]
    else:
        c.execute(Q.STATS_POST_COUNT_ALL)
        total_posts = c.fetchone()[0]

        c.execute(Q.STATS_TOTAL_COMMENTS_ALL)
        total_comments = c.fetchone()[0] or 0

        c.execute(Q.STATS_AVG_COMMENTS_ALL)
        avg_comments = c.fetchone()[0] or 0

        c.execute(Q.STATS_AVG_UNIQUE_ALL)
        avg_unique = c.fetchone()[0] or 0

        c.execute(Q.STATS_UNIQUE_COMMENTERS_ALL)
        total_unique_commenters = c.fetchone()[0]

    conn.close()
    return {
        'total_posts': total_posts,
        'total_comments': total_comments,
        'avg_comments': round(avg_comments, 1),
        'avg_unique': round(avg_unique, 1),
        'total_unique_commenters': total_unique_commenters
    }


def generate_chart(chart_type='scatter', start_date='2025-01-01', end_date=None):
    """Generate chart and return as base64 PNG."""
    rows = get_daily_data(start_date, end_date)

    if not rows:
        return None

    dates = []
    comments = []
    unique = []

    for post_date, comment_count, unique_commenters, slug, title in rows:
        dt = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
        dates.append(dt)
        comments.append(comment_count)
        unique.append(unique_commenters)

    fig, ax = plt.subplots(figsize=(12, 5))

    color1 = '#3b82f6'
    color2 = '#f59e0b'

    if chart_type == 'scatter':
        ax.scatter(dates, comments, color=color1, s=25, label='Comments', alpha=0.7)
        ax.scatter(dates, unique, color=color2, s=25, label='Unique Commenters', alpha=0.7)
    else:
        ax.plot(dates, comments, color=color1, linewidth=1.5, label='Comments', alpha=0.8)
        ax.plot(dates, unique, color=color2, linewidth=1.5, label='Unique Commenters', alpha=0.8)

    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.title('DBD Daily Activity', fontsize=14, fontweight='bold')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')


def generate_histogram(start_date=None, end_date=None):
    """Generate histogram of unique commenters."""
    rows = get_daily_data(start_date, end_date)
    unique = [r[2] for r in rows if r[2] > 0]

    if not unique:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    max_commenters = max(unique)
    bins = range(0, max_commenters + 2)

    ax.hist(unique, bins=bins, edgecolor='black', alpha=0.7, color='#10b981', align='left')
    ax.set_xlabel('Number of Unique Commenters')
    ax.set_ylabel('Number of Days')
    ax.set_title('Distribution of Unique Commenters per DBD', fontsize=14, fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('utf-8')


@app.route('/')
def index():
    """Main dashboard page."""
    chart_type = request.args.get('chart_type', 'scatter')
    start_date = request.args.get('start_date', '2025-01-01')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))

    stats = get_stats(start_date, end_date)
    top_commenters = get_top_commenters(15, start_date, end_date)
    chart_b64 = generate_chart(chart_type, start_date, end_date)
    histogram_b64 = generate_histogram(start_date, end_date)

    return render_template('index.html',
                           stats=stats,
                           top_commenters=top_commenters,
                           chart_b64=chart_b64,
                           histogram_b64=histogram_b64,
                           chart_type=chart_type,
                           start_date=start_date,
                           end_date=end_date)


def main():
    """Start the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="WFC Dashboard Web Server")
    parser.add_argument("--port", type=int, default=PORT, help="Port to run on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with hot-reload")

    args = parser.parse_args()

    print(f"WFC Dashboard running at http://localhost:{args.port}")
    if args.debug:
        print("Debug mode enabled - templates will auto-reload")
    print("Press Ctrl+C to stop\n")

    app.run(host='localhost', port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
