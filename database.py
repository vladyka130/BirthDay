import sqlite3
import os
from datetime import datetime, date
from date_utils import is_birthday_in_current_week, is_birthday_today, get_days_until

DB_FILE = os.path.join(os.path.dirname(__file__), "birthdays.db")

class BirthdayDatabase:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
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
            conn.commit()

    def upsert_friend(self, fb_name: str, profile_url: str = "", avatar_url: str = "",
                      birth_day: int = None, birth_month: int = None, birth_year: int = None,
                      birthday_str: str = "", raw_info: str = ""):
        if not fb_name:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO friends (fb_name, profile_url, avatar_url, birth_day, birth_month, birth_year, birthday_str, raw_info, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fb_name) DO UPDATE SET
                    profile_url=excluded.profile_url,
                    avatar_url=CASE WHEN excluded.avatar_url <> '' THEN excluded.avatar_url ELSE avatar_url END,
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
