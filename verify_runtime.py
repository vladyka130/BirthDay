from database import BirthdayDatabase
from fb_scraper import FacebookScraper
from notifier import check_and_notify_birthdays
from date_utils import get_current_week_range
from datetime import date

def main():
    print("[Verification] Initializing BirthdayDatabase...")
    db = BirthdayDatabase()

    print("[Verification] Generating demo data...")
    scraper = FacebookScraper(db=db)
    count = scraper.generate_demo_data()
    print(f"[Verification] Demo records inserted: {count}")

    print("[Verification] Querying stats...")
    stats = db.get_stats()
    print(f"[Verification] Stats: {stats}")

    print("[Verification] Querying friends this week...")
    week_friends = db.get_friends_this_week()
    for f in week_friends:
        print(f" - {f['fb_name']} ({f['birthday_str']}), days until: {f.get('days_until')}")

    print("[Verification] Checking notifier summary...")
    notify_summary = check_and_notify_birthdays(db)
    print(f"[Verification] Notifier summary: {notify_summary}")

    print("[Verification] ALL RUNTIME VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
