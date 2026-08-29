import sqlite3
import os
from datetime import datetime, date
from date_utils import is_birthday_in_current_week, is_birthday_today, get_days_until

APP_DIR = os.path.join(os.path.expanduser("~"), ".fb_birthday_app")
os.makedirs(APP_DIR, exist_ok=True)
DEFAULT_DB_FILE = os.path.join(APP_DIR, "birthdays.db")
LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), "birthdays.db")

# Auto-migrate local database to user directory if needed
if os.path.exists(LOCAL_DB_FILE) and not os.path.exists(DEFAULT_DB_FILE):
    import shutil
    try:
        shutil.copy2(LOCAL_DB_FILE, DEFAULT_DB_FILE)
    except Exception:
        pass

DB_FILE = DEFAULT_DB_FILE if (os.path.exists(DEFAULT_DB_FILE) or not os.access(os.path.dirname(__file__), os.W_OK)) else LOCAL_DB_FILE

class BirthdayDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path else DB_FILE
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS friends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fb_name TEXT UNIQUE NOT NULL,
                    profile_url TEXT,
                    avatar_url TEXT,
                    birth_day INTEGER,
                    birth_month INTEGER,
                    birth_year INTEGER,
                    birthday_str TEXT,
                    raw_info TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Auto-clean legacy invalid/generic profile URLs
            conn.execute("""
                UPDATE friends SET profile_url = ''
                WHERE profile_url LIKE '%facebook.com' OR profile_url LIKE '%facebook.com/'
                   OR profile_url LIKE '%/me' OR profile_url LIKE '%/me/%';
            """)
            conn.commit()

    def upsert_friend(self, fb_name: str, profile_url: str = "", avatar_url: str = "",
                      birth_day: int = None, birth_month: int = None, birth_year: int = None,
                      birthday_str: str = "", raw_info: str = ""):
        if not fb_name:
            return

        from fb_scraper import clean_profile_url
        profile_url = clean_profile_url(profile_url)

        if avatar_url and "emoji.php" in avatar_url:
            avatar_url = ""

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO friends (fb_name, profile_url, avatar_url, birth_day, birth_month, birth_year, birthday_str, raw_info, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fb_name) DO UPDATE SET
                    profile_url=excluded.profile_url,
                    avatar_url=CASE WHEN excluded.avatar_url <> '' THEN excluded.avatar_url WHEN avatar_url LIKE '%emoji.php%' THEN '' ELSE avatar_url END,
                    birth_day=excluded.birth_day,
                    birth_month=excluded.birth_month,
                    birth_year=excluded.birth_year,
                    birthday_str=excluded.birthday_str,
                    raw_info=excluded.raw_info,
                    last_updated=excluded.last_updated
            """, (fb_name, profile_url, avatar_url, birth_day, birth_month, birth_year, birthday_str, raw_info, now_str))
            conn.commit()

    def get_all_friends(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM friends ORDER BY birth_month, birth_day")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_friends_this_week(self, ref_date: date = None) -> list[dict]:
        all_friends = self.get_all_friends()
        result = []
        for friend in all_friends:
            d, m = friend.get("birth_day"), friend.get("birth_month")
            if d and m and is_birthday_in_current_week(d, m, ref_date):
                friend["days_until"] = get_days_until(d, m, ref_date)
                result.append(friend)
        result.sort(key=lambda x: x["days_until"])
        return result

    def get_friends_today(self, ref_date: date = None) -> list[dict]:
        all_friends = self.get_all_friends()
        result = []
        for friend in all_friends:
            d, m = friend.get("birth_day"), friend.get("birth_month")
            if d and m and is_birthday_today(d, m, ref_date):
                result.append(friend)
        return result

    def search_friends(self, query: str) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{query}%"
            cursor.execute("SELECT * FROM friends WHERE fb_name LIKE ? OR birthday_str LIKE ? ORDER BY birth_month, birth_day", (pattern, pattern))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        all_friends = self.get_all_friends()
        this_week = self.get_friends_this_week()
        today = self.get_friends_today()
        return {
            "total_friends": len(all_friends),
            "this_week_count": len(this_week),
            "today_count": len(today)
        }
