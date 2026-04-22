import sqlite3
import os
import time

DATABASE_PATH = os.path.expanduser("~/.kaya/kaya_history.db")

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Raw events for feature calculation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            keycode INTEGER,
            is_down INTEGER,
            is_backspace INTEGER,
            app_name TEXT,
            modifiers INTEGER
        )
    ''')
    
    # Feature vectors for historical analysis (cross-session)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feature_vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            mode TEXT,
            wpm REAL,
            backspace_rate REAL,
            ikl_variance REAL,
            hold_time_mean REAL,
            error_rate REAL,
            burnout_score REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def log_event(ts, keycode, is_down, is_backspace, app_name, modifiers):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (ts, keycode, is_down, is_backspace, app_name, modifiers)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (ts, keycode, is_down, is_backspace, app_name, modifiers))
    conn.commit()
    conn.close()

def get_last_n_events(n):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT ts, keycode, is_down, is_backspace, app_name, modifiers FROM events ORDER BY id DESC LIMIT ?', (n,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def log_features(mode, wpm, bs_rate, ikl_var, hold_mean, error_rate, score):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feature_vectors (ts, mode, wpm, backspace_rate, ikl_variance, hold_time_mean, error_rate, burnout_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (time.time(), mode, wpm, bs_rate, ikl_var, hold_mean, error_rate, score))
    conn.commit()
    conn.close()

def get_historical_averages(mode, days=7):
    cutoff = time.time() - (days * 86400)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT AVG(wpm), AVG(backspace_rate), AVG(ikl_variance), AVG(hold_time_mean), AVG(error_rate)
        FROM feature_vectors 
        WHERE mode = ? AND ts > ?
    ''', (mode, cutoff))
    row = cursor.fetchone()
    conn.close()
    return row
