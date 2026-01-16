#!/usr/bin/env python3
"""
DBD Historical Data Scraper
Collects data from DBD posts: date, title, image, poll votes, comments, unique commenters.
"""

import csv
import json
import re
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .config import BASE_URL, STATE_DIR


@dataclass
class DBDPost:
    """Data for a single DBD post."""
    slug: str
    title: str
    post_date: str
    comment_count: int
    unique_commenters: int
    cover_image: Optional[str]
    poll_id: Optional[int]
    poll_total_votes: Optional[int]
    commenter_counts: Dict[str, int]  # username -> comment count


DB_PATH = STATE_DIR / "dbd_history.db"


def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            slug TEXT PRIMARY KEY,
            title TEXT,
            post_date TEXT,
            comment_count INTEGER,
            unique_commenters INTEGER,
            cover_image TEXT,
            poll_id INTEGER,
            poll_total_votes INTEGER,
            scraped_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS commenter_activity (
            slug TEXT,
            username TEXT,
            comment_count INTEGER,
            PRIMARY KEY (slug, username),
            FOREIGN KEY (slug) REFERENCES posts(slug)
        )
    """)

    conn.commit()
    conn.close()


def get_all_dbd_slugs() -> List[str]:
    """Get all DBD post slugs from the sitemap."""
    r = requests.get(f"{BASE_URL}/sitemap.xml", timeout=30)
    r.raise_for_status()

    slugs = re.findall(r'writeforcalifornia\.com/p/(dbd-\d{2}-\d{2}-\d{4}-[^<\s]+)', r.text)
    return sorted(set(slugs))


def get_dbd_slugs_for_year(year: int) -> List[str]:
    """Get DBD slugs for a specific year."""
    all_slugs = get_all_dbd_slugs()
    return [s for s in all_slugs if f"-{year}-" in s]


def scrape_post(slug: str) -> Optional[DBDPost]:
    """Scrape data from a single DBD post."""
    url = f"{BASE_URL}/p/{slug}"

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching {slug}: {e}")
        return None

    # Extract JSON data
    match = re.search(r'JSON\.parse\("(.+?)"\)', r.text)
    if not match:
        print(f"  No JSON data found for {slug}")
        return None

    try:
        raw = match.group(1)
        decoded = raw.encode('utf-8').decode('unicode_escape')
        data = json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  Error parsing JSON for {slug}: {e}")
        return None

    post = data.get('post', {})

    title = post.get('title', '')
    post_date = post.get('post_date', '')
    comment_count = post.get('comment_count', 0)
    cover_image = post.get('cover_image')

    # Find poll ID in raw HTML (more reliable)
    poll_match = re.search(r'poll-(\d{5,7})', r.text)
    poll_id = int(poll_match.group(1)) if poll_match else None
    poll_total_votes = None  # Would need authenticated API access

    # Get commenter data from comments page
    commenter_counts = {}
    unique_commenters = 0

    try:
        # Retry with backoff for rate limiting
        for attempt in range(3):
            comments_r = requests.get(f"{url}/comments", timeout=30)
            if comments_r.status_code == 429:
                wait_time = (attempt + 1) * 5
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            comments_r.raise_for_status()
            break
        else:
            raise requests.RequestException("Rate limited after 3 retries")

        comments_match = re.search(r'JSON\.parse\("(.+?)"\)', comments_r.text)
        if comments_match:
            comments_raw = comments_match.group(1)
            # Handle edge cases with trailing backslashes
            comments_raw = re.sub(r'\\+$', '', comments_raw)
            comments_decoded = comments_raw.encode('utf-8').decode('unicode_escape')
            comments_data = json.loads(comments_decoded)

            initial_comments = comments_data.get('initialComments', [])

            def count_comments(comment_list):
                for c in comment_list:
                    name = c.get('name', 'Unknown')
                    commenter_counts[name] = commenter_counts.get(name, 0) + 1
                    if 'children' in c:
                        count_comments(c['children'])

            count_comments(initial_comments)
            unique_commenters = len(commenter_counts)
    except Exception as e:
        print(f"  Error fetching comments for {slug}: {e}")

    return DBDPost(
        slug=slug,
        title=title,
        post_date=post_date,
        comment_count=comment_count,
        unique_commenters=unique_commenters,
        cover_image=cover_image,
        poll_id=poll_id,
        poll_total_votes=poll_total_votes,
        commenter_counts=commenter_counts,
    )


def save_post(post: DBDPost):
    """Save a post to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO posts
        (slug, title, post_date, comment_count, unique_commenters,
         cover_image, poll_id, poll_total_votes, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post.slug, post.title, post.post_date, post.comment_count,
        post.unique_commenters, post.cover_image, post.poll_id,
        post.poll_total_votes, datetime.now().isoformat()
    ))

    # Save commenter activity
    for username, count in post.commenter_counts.items():
        c.execute("""
            INSERT OR REPLACE INTO commenter_activity (slug, username, comment_count)
            VALUES (?, ?, ?)
        """, (post.slug, username, count))

    conn.commit()
    conn.close()


def is_post_scraped(slug: str) -> bool:
    """Check if a post has already been scraped."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM posts WHERE slug = ?", (slug,))
    result = c.fetchone()
    conn.close()
    return result is not None


def scrape_year(year: int, delay: float = 1.0, skip_existing: bool = True):
    """Scrape all DBD posts for a given year."""
    init_db()

    slugs = get_dbd_slugs_for_year(year)
    print(f"Found {len(slugs)} DBD posts for {year}")

    for i, slug in enumerate(slugs, 1):
        if skip_existing and is_post_scraped(slug):
            print(f"[{i}/{len(slugs)}] Skipping {slug} (already scraped)")
            continue

        print(f"[{i}/{len(slugs)}] Scraping {slug}...")
        post = scrape_post(slug)

        if post:
            save_post(post)
            print(f"  -> {post.comment_count} comments, {post.unique_commenters} unique")

        time.sleep(delay)

    print(f"\nDone! Data saved to {DB_PATH}")


def export_to_csv(output_path: Optional[Path] = None):
    """Export posts data to CSV."""
    if output_path is None:
        output_path = STATE_DIR / "dbd_history.csv"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM posts ORDER BY post_date DESC")
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()
    print(f"Exported {len(rows)} posts to {output_path}")


def get_top_commenters(limit: int = 20) -> List[tuple]:
    """Get top commenters across all posts."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT username,
               SUM(comment_count) as total_comments,
               COUNT(DISTINCT slug) as posts_participated
        FROM commenter_activity
        GROUP BY username
        ORDER BY total_comments DESC
        LIMIT ?
    """, (limit,))

    results = c.fetchall()
    conn.close()
    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape DBD post data")
    parser.add_argument("--year", type=int, help="Year to scrape (default: last year)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests")
    parser.add_argument("--export", action="store_true", help="Export to CSV after scraping")
    parser.add_argument("--top-commenters", type=int, help="Show top N commenters")

    args = parser.parse_args()

    if args.top_commenters:
        init_db()
        top = get_top_commenters(args.top_commenters)
        print(f"\nTop {args.top_commenters} commenters:")
        print("-" * 50)
        for username, total, posts in top:
            print(f"{username}: {total} comments across {posts} posts")
        return

    year = args.year or datetime.now().year - 1
    scrape_year(year, delay=args.delay)

    if args.export:
        export_to_csv()


if __name__ == "__main__":
    main()
