#!/usr/bin/env python3
"""
WFC Web App
Simple web interface to view DBD data and charts.
"""

import io
import base64
import sqlite3
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .config import STATE_DIR

DB_PATH = STATE_DIR / "dbd_history.db"
PORT = 8080


def get_daily_data(start_date=None):
    """Get comment counts and unique commenters by date."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if start_date:
        c.execute("""
            SELECT post_date, comment_count, unique_commenters, slug, title
            FROM posts
            WHERE post_date >= ?
            ORDER BY post_date
        """, (start_date,))
    else:
        c.execute("""
            SELECT post_date, comment_count, unique_commenters, slug, title
            FROM posts
            ORDER BY post_date
        """)

    rows = c.fetchall()
    conn.close()
    return rows


def get_top_commenters(limit=20):
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


def get_stats():
    """Get overall statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM posts")
    total_posts = c.fetchone()[0]

    c.execute("SELECT SUM(comment_count) FROM posts")
    total_comments = c.fetchone()[0] or 0

    c.execute("SELECT AVG(comment_count) FROM posts")
    avg_comments = c.fetchone()[0] or 0

    c.execute("SELECT AVG(unique_commenters) FROM posts WHERE unique_commenters > 0")
    avg_unique = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(DISTINCT username) FROM commenter_activity")
    total_unique_commenters = c.fetchone()[0]

    conn.close()
    return {
        'total_posts': total_posts,
        'total_comments': total_comments,
        'avg_comments': round(avg_comments, 1),
        'avg_unique': round(avg_unique, 1),
        'total_unique_commenters': total_unique_commenters
    }


def generate_chart(chart_type='scatter', start_date='2025-01-01'):
    """Generate chart and return as base64 PNG."""
    rows = get_daily_data(start_date)

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


def generate_histogram():
    """Generate histogram of unique commenters."""
    rows = get_daily_data()
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


def render_html(chart_type='scatter', start_date='2025-01-01'):
    """Render the main HTML page."""
    stats = get_stats()
    top_commenters = get_top_commenters(15)
    chart_b64 = generate_chart(chart_type, start_date)
    histogram_b64 = generate_histogram()

    top_commenters_html = ""
    for i, (username, total, posts) in enumerate(top_commenters, 1):
        top_commenters_html += f"""
        <tr>
            <td class="rank">{i}</td>
            <td class="username">{username}</td>
            <td class="num">{total}</td>
            <td class="num">{posts}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WFC DBD Dashboard</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #fbbf24;
            margin-bottom: 20px;
            font-size: 2rem;
        }}
        h2 {{
            color: #60a5fa;
            margin: 30px 0 15px;
            font-size: 1.3rem;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #fbbf24;
        }}
        .stat-card .label {{
            color: #888;
            font-size: 0.9rem;
            margin-top: 5px;
        }}
        .controls {{
            background: #16213e;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .controls label {{
            color: #888;
            margin-right: 8px;
        }}
        .controls select, .controls input {{
            background: #1a1a2e;
            color: #eee;
            border: 1px solid #333;
            padding: 8px 12px;
            border-radius: 5px;
        }}
        .controls button {{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 5px;
            cursor: pointer;
        }}
        .controls button:hover {{
            background: #2563eb;
        }}
        .chart-container {{
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .chart-container img {{
            width: 100%;
            height: auto;
            border-radius: 5px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 900px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{
            background: #0f3460;
            color: #fbbf24;
            font-weight: 600;
        }}
        tr:hover {{
            background: #1a1a2e;
        }}
        .rank {{
            width: 40px;
            color: #888;
        }}
        .username {{
            font-weight: 500;
        }}
        .num {{
            text-align: right;
            color: #60a5fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>WFC DBD Dashboard</h1>

        <div class="stats">
            <div class="stat-card">
                <div class="value">{stats['total_posts']}</div>
                <div class="label">Total Posts</div>
            </div>
            <div class="stat-card">
                <div class="value">{stats['total_comments']:,}</div>
                <div class="label">Total Comments</div>
            </div>
            <div class="stat-card">
                <div class="value">{stats['avg_comments']}</div>
                <div class="label">Avg Comments/Post</div>
            </div>
            <div class="stat-card">
                <div class="value">{stats['avg_unique']}</div>
                <div class="label">Avg Unique/Post</div>
            </div>
            <div class="stat-card">
                <div class="value">{stats['total_unique_commenters']}</div>
                <div class="label">Total Contributors</div>
            </div>
        </div>

        <h2>Daily Activity</h2>
        <form class="controls" method="GET">
            <div>
                <label>Chart Type:</label>
                <select name="chart_type">
                    <option value="scatter" {"selected" if chart_type == "scatter" else ""}>Scatter</option>
                    <option value="line" {"selected" if chart_type == "line" else ""}>Line</option>
                </select>
            </div>
            <div>
                <label>Start Date:</label>
                <input type="date" name="start_date" value="{start_date}">
            </div>
            <button type="submit">Update</button>
        </form>

        <div class="chart-container">
            <img src="data:image/png;base64,{chart_b64}" alt="Daily Activity Chart">
        </div>

        <div class="grid">
            <div>
                <h2>Top Commenters</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Username</th>
                            <th class="num">Comments</th>
                            <th class="num">Posts</th>
                        </tr>
                    </thead>
                    <tbody>
                        {top_commenters_html}
                    </tbody>
                </table>
            </div>
            <div>
                <h2>Commenters Distribution</h2>
                <div class="chart-container">
                    <img src="data:image/png;base64,{histogram_b64}" alt="Histogram">
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html


class WFCHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        chart_type = params.get('chart_type', ['scatter'])[0]
        start_date = params.get('start_date', ['2025-01-01'])[0]

        if parsed.path == '/' or parsed.path == '':
            html = render_html(chart_type, start_date)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    """Start the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="WFC Dashboard Web Server")
    parser.add_argument("--port", type=int, default=PORT, help="Port to run on")

    args = parser.parse_args()

    server = HTTPServer(('localhost', args.port), WFCHandler)
    print(f"WFC Dashboard running at http://localhost:{args.port}")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
