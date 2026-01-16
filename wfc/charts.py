#!/usr/bin/env python3
"""
DBD Charts
Generate charts from historical DBD data.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .config import STATE_DIR

DB_PATH = STATE_DIR / "dbd_history.db"
CHARTS_DIR = STATE_DIR / "charts"


def get_daily_data(start_date=None):
    """Get comment counts and unique commenters by date."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if start_date:
        c.execute("""
            SELECT post_date, comment_count, unique_commenters
            FROM posts
            WHERE post_date >= ?
            ORDER BY post_date
        """, (start_date,))
    else:
        c.execute("""
            SELECT post_date, comment_count, unique_commenters
            FROM posts
            ORDER BY post_date
        """)

    rows = c.fetchall()
    conn.close()

    dates = []
    comments = []
    unique = []

    for post_date, comment_count, unique_commenters in rows:
        # Parse ISO date
        dt = datetime.fromisoformat(post_date.replace('Z', '+00:00'))
        dates.append(dt)
        comments.append(comment_count)
        unique.append(unique_commenters)

    return dates, comments, unique


def plot_comments_by_day(save_path=None, show=True, start_date=None):
    """Create a line chart of comments and unique commenters by day."""
    dates, comments, unique = get_daily_data(start_date=start_date)

    if not dates:
        print("No data to plot")
        return

    fig, ax1 = plt.subplots(figsize=(14, 6))

    # Plot comment count
    color1 = '#1f77b4'
    ax1.scatter(dates, comments, color=color1, s=20, label='Comments', alpha=0.6)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Comment Count', color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)

    # Plot unique commenters on same axis (different color)
    color2 = '#ff7f0e'
    ax1.scatter(dates, unique, color=color2, s=20, label='Unique Commenters', alpha=0.6)

    # Format x-axis
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    # Title and legend
    plt.title('DBD Daily Activity', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')

    # Grid
    ax1.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save if path provided
    if save_path:
        CHARTS_DIR.mkdir(exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"Chart saved to {save_path}")

    if show:
        plt.show()

    return fig


def plot_commenters_histogram(save_path=None, show=True):
    """Create a histogram of unique commenters per day."""
    dates, comments, unique = get_daily_data()

    # Filter out zeros (failed scrapes)
    unique_valid = [u for u in unique if u > 0]

    if not unique_valid:
        print("No valid data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create histogram
    max_commenters = max(unique_valid)
    bins = range(0, max_commenters + 2)

    ax.hist(unique_valid, bins=bins, edgecolor='black', alpha=0.7, color='#2ecc71', align='left')

    ax.set_xlabel('Number of Unique Commenters', fontsize=12)
    ax.set_ylabel('Number of Days', fontsize=12)
    ax.set_title('Distribution of Unique Commenters per DBD', fontsize=14, fontweight='bold')

    ax.set_xticks(range(0, max_commenters + 1, 2))
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()

    if save_path:
        CHARTS_DIR.mkdir(exist_ok=True)
        plt.savefig(save_path, dpi=150)
        print(f"Chart saved to {save_path}")

    if show:
        plt.show()

    return fig


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate DBD charts")
    parser.add_argument("--type", choices=["line", "histogram"], default="line",
                        help="Chart type: line (comments by day) or histogram (commenters distribution)")
    parser.add_argument("--save", type=str, help="Save chart to file (e.g., chart.png)")
    parser.add_argument("--no-show", action="store_true", help="Don't display the chart")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.type == "line":
        save_path = Path(args.save) if args.save else CHARTS_DIR / "comments_by_day.png"
        plot_comments_by_day(save_path=save_path, show=not args.no_show, start_date=args.start)
    elif args.type == "histogram":
        save_path = Path(args.save) if args.save else CHARTS_DIR / "commenters_histogram.png"
        plot_commenters_histogram(save_path=save_path, show=not args.no_show)


if __name__ == "__main__":
    main()
