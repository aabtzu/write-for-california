"""
SQL queries for WFC dashboard.
All queries are parameterized for date range filtering.
"""

# Daily data queries
DAILY_DATA_WITH_RANGE = """
    SELECT post_date, comment_count, unique_commenters, slug, title
    FROM posts
    WHERE post_date >= ? AND post_date <= ?
    ORDER BY post_date
"""

DAILY_DATA_WITH_START = """
    SELECT post_date, comment_count, unique_commenters, slug, title
    FROM posts
    WHERE post_date >= ?
    ORDER BY post_date
"""

DAILY_DATA_ALL = """
    SELECT post_date, comment_count, unique_commenters, slug, title
    FROM posts
    ORDER BY post_date
"""

# Top commenters queries
TOP_COMMENTERS_WITH_RANGE = """
    SELECT ca.username,
           SUM(ca.comment_count) as total_comments,
           COUNT(DISTINCT ca.slug) as posts_participated
    FROM commenter_activity ca
    JOIN posts p ON ca.slug = p.slug
    WHERE p.post_date >= ? AND p.post_date <= ?
    GROUP BY ca.username
    ORDER BY total_comments DESC
    LIMIT ?
"""

TOP_COMMENTERS_WITH_START = """
    SELECT ca.username,
           SUM(ca.comment_count) as total_comments,
           COUNT(DISTINCT ca.slug) as posts_participated
    FROM commenter_activity ca
    JOIN posts p ON ca.slug = p.slug
    WHERE p.post_date >= ?
    GROUP BY ca.username
    ORDER BY total_comments DESC
    LIMIT ?
"""

TOP_COMMENTERS_ALL = """
    SELECT username,
           SUM(comment_count) as total_comments,
           COUNT(DISTINCT slug) as posts_participated
    FROM commenter_activity
    GROUP BY username
    ORDER BY total_comments DESC
    LIMIT ?
"""

# Stats queries - with date range
STATS_POST_COUNT_RANGE = """
    SELECT COUNT(*) FROM posts
    WHERE post_date >= ? AND post_date <= ?
"""

STATS_TOTAL_COMMENTS_RANGE = """
    SELECT SUM(comment_count) FROM posts
    WHERE post_date >= ? AND post_date <= ?
"""

STATS_AVG_COMMENTS_RANGE = """
    SELECT AVG(comment_count) FROM posts
    WHERE post_date >= ? AND post_date <= ?
"""

STATS_AVG_UNIQUE_RANGE = """
    SELECT AVG(unique_commenters) FROM posts
    WHERE unique_commenters > 0 AND post_date >= ? AND post_date <= ?
"""

STATS_UNIQUE_COMMENTERS_RANGE = """
    SELECT COUNT(DISTINCT ca.username)
    FROM commenter_activity ca
    JOIN posts p ON ca.slug = p.slug
    WHERE p.post_date >= ? AND p.post_date <= ?
"""

# Stats queries - all data
STATS_POST_COUNT_ALL = "SELECT COUNT(*) FROM posts"
STATS_TOTAL_COMMENTS_ALL = "SELECT SUM(comment_count) FROM posts"
STATS_AVG_COMMENTS_ALL = "SELECT AVG(comment_count) FROM posts"
STATS_AVG_UNIQUE_ALL = "SELECT AVG(unique_commenters) FROM posts WHERE unique_commenters > 0"
STATS_UNIQUE_COMMENTERS_ALL = "SELECT COUNT(DISTINCT username) FROM commenter_activity"
