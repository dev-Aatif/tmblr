import sqlite3
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "analytics.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            followers INTEGER,
            total_posts INTEGER,
            queue_length INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS following_history (
            username TEXT PRIMARY KEY,
            followed_at INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS category_totals (
            category TEXT PRIMARY KEY,
            total_posts INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def save_stats(followers, total_posts, queue_length):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO stats (timestamp, followers, total_posts, queue_length) VALUES (?, ?, ?, ?)',
              (int(time.time()), followers, total_posts, queue_length))
    conn.commit()
    conn.close()

def get_latest_stats():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT followers, total_posts, queue_length FROM stats ORDER BY timestamp DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "followers": row[0],
            "total_posts": row[1],
            "queue_length": row[2]
        }
    return None

def log_follow(username):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO following_history (username, followed_at) VALUES (?, ?)',
              (username, int(time.time())))
    conn.commit()
    conn.close()

def get_old_follows(days=7):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff_time = int(time.time()) - (days * 24 * 60 * 60)
    c.execute('SELECT username FROM following_history WHERE followed_at < ?', (cutoff_time,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def remove_follow_log(username):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM following_history WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def increment_category_total(category):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO category_totals (category, total_posts) VALUES (?, 0)', (category,))
    c.execute('UPDATE category_totals SET total_posts = total_posts + 1 WHERE category = ?', (category,))
    conn.commit()
    conn.close()

def get_category_totals():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT category, total_posts FROM category_totals')
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}
