try:
    import pytest
except ImportError:
    pytest = None
from datetime import date, timedelta
from date_utils import parse_birthday_text, get_current_week_range, is_birthday_in_current_week, is_birthday_today, get_days_until
from database import BirthdayDatabase

def test_parse_birthday_text():
    ref = date(2026, 8, 29) # Saturday, Aug 29, 2026

    # Ukrainian month strings
    d, m, y = parse_birthday_text("29 серпня", reference_date=ref)
    assert d == 29 and m == 8 and y is None

    d, m, y = parse_birthday_text("15 вересня 1995", reference_date=ref)
    assert d == 15 and m == 9 and y == 1995

    # Relative days
    d, m, y = parse_birthday_text("Сьогодні", reference_date=ref)
    assert d == 29 and m == 8

    d, m, y = parse_birthday_text("Завтра", reference_date=ref)
    assert d == 30 and m == 8

    d, m, y = parse_birthday_text("За 3 дні", reference_date=ref)
    assert d == 1 and m == 9

def test_current_week_logic():
    # 2026-08-29 is a Saturday
    # Monday is 2026-08-24, Sunday is 2026-08-30
    ref = date(2026, 8, 29)
    start, end = get_current_week_range(ref)
    assert start == date(2026, 8, 24)
    assert end == date(2026, 8, 30)

    # Aug 25 is inside current week
    assert is_birthday_in_current_week(25, 8, ref) is True
    # Aug 29 is today inside current week
    assert is_birthday_in_current_week(29, 8, ref) is True
    # Sept 10 is NOT inside current week
    assert is_birthday_in_current_week(10, 9, ref) is False

def test_database_operations(tmp_path):
    db_file = str(tmp_path / "test_birthdays.db")
    db = BirthdayDatabase(db_path=db_file)

    ref = date(2026, 8, 29) # Saturday

    # Insert test friends
    db.upsert_friend(fb_name="Анна Тарасюк", profile_url="http://fb.com/1", birth_day=29, birth_month=8, birthday_str="29 серпня")
    db.upsert_friend(fb_name="Петро Сидоренко", profile_url="http://fb.com/2", birth_day=30, birth_month=8, birthday_str="30 серпня")
    db.upsert_friend(fb_name="Ольга Іваненко", profile_url="http://fb.com/3", birth_day=15, birth_month=11, birthday_str="15 листопада")

    all_f = db.get_all_friends()
    assert len(all_f) == 3

    today_f = db.get_friends_today(ref_date=ref)
    assert len(today_f) == 1
    assert today_f[0]["fb_name"] == "Анна Тарасюк"

    week_f = db.get_friends_this_week(ref_date=ref)
    assert len(week_f) == 2  # 29 Aug and 30 Aug are both in Mon-Sun range

    stats = db.get_stats()
    assert stats["total_friends"] == 3

if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    print("Running date utils tests...")
    test_parse_birthday_text()
    test_current_week_logic()
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_database_operations(Path(tmp_dir))
    print("✅ All cross-platform tests passed successfully!")
