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
