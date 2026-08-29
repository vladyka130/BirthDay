import re
from datetime import datetime, date, timedelta

MONTHS_UA = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
    "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
    "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
    "січень": 1, "лютий": 2, "березень": 3, "квітень": 4,
    "травень": 5, "червень": 6, "липень": 7, "серпень": 8,
    "вересень": 9, "жовтень": 10, "листопад": 11, "грудень": 12
}

MONTHS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def parse_birthday_text(text: str, reference_date: date = None) -> tuple[int | None, int | None, int | None]:
    """
    Parses day, month, year from strings like:
    - '29 серпня'
    - '29 серпня 1995'
    - 'August 29'
    - 'Сьогодні' / 'Today'
    - 'Завтра' / 'Tomorrow'
    - 'За 3 дні'
    Returns (day, month, year).
    """
    if not text:
        return None, None, None

    if reference_date is None:
        reference_date = date.today()

    clean_text = text.strip().lower()

    if "сьогодні" in clean_text or "today" in clean_text:
        return reference_date.day, reference_date.month, None

    if "завтра" in clean_text or "tomorrow" in clean_text:
        dt = reference_date + timedelta(days=1)
        return dt.day, dt.month, None

    days_in_match = re.search(r"за\s+(\d+)\s+дн", clean_text)
    if days_in_match:
        n_days = int(days_in_match.group(1))
        dt = reference_date + timedelta(days=n_days)
        return dt.day, dt.month, None

    for name, month_num in {**MONTHS_UA, **MONTHS_EN}.items():
        if name in clean_text:
            numbers = [int(n) for n in re.findall(r"\b\d+\b", clean_text)]
            if len(numbers) >= 2:
                day = numbers[0]
                year = numbers[1] if numbers[1] > 1900 else None
                return day, month_num, year
            elif len(numbers) == 1:
                return numbers[0], month_num, None

    return None, None, None

def get_current_week_range(reference_date: date = None) -> tuple[date, date]:
    """Returns (monday_date, sunday_date) for the current week."""
    if reference_date is None:
        reference_date = date.today()
    start = reference_date - timedelta(days=reference_date.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end

def is_birthday_in_current_week(day: int, month: int, reference_date: date = None) -> bool:
    """Checks if a birthday (day, month) falls in the current week (Mon-Sun)."""
    if not day or not month:
        return False

    if reference_date is None:
        reference_date = date.today()

    start, end = get_current_week_range(reference_date)

    for year in (reference_date.year, reference_date.year + 1, reference_date.year - 1):
        try:
            b_date = date(year, month, day)
            if start <= b_date <= end:
                return True
        except ValueError:
            pass
    return False

def is_birthday_today(day: int, month: int, reference_date: date = None) -> bool:
    if not day or not month:
        return False
    if reference_date is None:
        reference_date = date.today()
    return day == reference_date.day and month == reference_date.month

def get_days_until(day: int, month: int, reference_date: date = None) -> int:
    """Calculates number of days remaining until next birthday (or offset in current week)."""
    if not day or not month:
        return 999
    if reference_date is None:
        reference_date = date.today()

    # If inside current week
    start, end = get_current_week_range(reference_date)
    for year in (reference_date.year, reference_date.year + 1, reference_date.year - 1):
        try:
            b_date = date(year, month, day)
            if start <= b_date <= end:
                return (b_date - reference_date).days
        except ValueError:
            pass

    # Default upcoming calculation
    for year in (reference_date.year, reference_date.year + 1):
        try:
            b_date = date(year, month, day)
            if b_date >= reference_date:
                return (b_date - reference_date).days
        except ValueError:
            pass
    return 999
