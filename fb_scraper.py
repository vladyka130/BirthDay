import os
import time
import re
import asyncio
from playwright.sync_api import sync_playwright
from database import BirthdayDatabase
from date_utils import parse_birthday_text

STATE_DIR = os.path.join(os.path.expanduser("~"), ".fb_birthday_app")
STATE_FILE = os.path.join(STATE_DIR, "fb_state.json")
os.makedirs(STATE_DIR, exist_ok=True)

def _ensure_event_loop():
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

def _launch_browser_with_fallback(p, headless=False, args=None):
    """Attempts to launch installed Chrome, installed Edge, or Playwright Chromium."""
    if args is None:
        args = ["--disable-notifications"]

    # Try 1: Installed Google Chrome
    try:
        return p.chromium.launch(channel="chrome", headless=headless, args=args)
    except Exception as e1:
        print(f"[FB Scraper] System Chrome launch failed: {e1}. Trying system Edge...")

    # Try 2: Installed Microsoft Edge (Default on Windows 10/11)
    try:
        return p.chromium.launch(channel="msedge", headless=headless, args=args)
    except Exception as e2:
        print(f"[FB Scraper] System Edge launch failed: {e2}. Trying standard Playwright Chromium...")

    # Try 3: Standard Playwright Chromium
    return p.chromium.launch(headless=headless, args=args)

class FacebookScraper:
    def __init__(self, state_file: str = STATE_FILE, db: BirthdayDatabase = None):
        self.state_file = state_file
        self.db = db if db else BirthdayDatabase()

    def is_logged_in(self) -> bool:
        """Checks if valid state file with c_user and xs session cookies exists."""
        if not os.path.exists(self.state_file):
            return False
        _ensure_event_loop()
        try:
            with sync_playwright() as p:
                browser = _launch_browser_with_fallback(p, headless=True)
                context = browser.new_context(storage_state=self.state_file)
                cookies = context.cookies()
                c_user = [c for c in cookies if c.get("name") == "c_user"]
                xs = [c for c in cookies if c.get("name") == "xs"]
                try:
                    browser.close()
                except Exception:
                    pass
                return len(c_user) > 0 and len(xs) > 0
        except Exception:
            return False

    def set_manual_cookies(self, c_user: str, xs: str) -> bool:
        """Manually sets c_user and xs session cookies and saves state file."""
        _ensure_event_loop()
        try:
            with sync_playwright() as p:
                browser = _launch_browser_with_fallback(p, headless=True)
                context = browser.new_context()
                context.add_cookies([
                    {
                        "name": "c_user",
                        "value": c_user.strip(),
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True,
                        "httpOnly": False
                    },
                    {
                        "name": "xs",
                        "value": xs.strip(),
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True,
                        "httpOnly": True
                    }
                ])
                context.storage_state(path=self.state_file)
                try:
                    browser.close()
                except Exception:
                    pass
                return True
        except Exception as e:
            print(f"[FB Scraper] Error setting manual cookies: {e}")
            return False

    def launch_login_session(self, status_callback=None):
        """Opens a visible browser for the user to log into Facebook."""
        _ensure_event_loop()

        def log(msg: str):
            print(f"[FB Scraper] {msg}")
            if status_callback:
                status_callback(msg)

        log("Запуск браузера для авторизації...")
        try:
            with sync_playwright() as p:
                browser = _launch_browser_with_fallback(
                    p,
                    headless=False,
                    args=["--disable-notifications", "--start-maximized"]
                )
                
                kwargs = {}
                if os.path.exists(self.state_file):
                    try:
                        kwargs["storage_state"] = self.state_file
                    except Exception:
                        pass

                context = browser.new_context(**kwargs)
                page = context.new_page()
                
                log("Перехід на facebook.com/events/birthdays/...")
                page.goto("https://www.facebook.com/events/birthdays/", wait_until="domcontentloaded")
                log("Браузер відкрито. Будь ласка, введіть логін/пароль у відкритому вікні!")

                logged_in_detected = False

                while True:
                    try:
                        if page.is_closed():
                            break
                    except Exception:
                        break

                    time.sleep(0.8)
                    try:
                        cookies = context.cookies()
                        c_user_cookie = [c for c in cookies if c.get("name") == "c_user"]
                        if c_user_cookie:
                            user_id = c_user_cookie[0].get("value", "")
                            try:
                                context.storage_state(path=self.state_file)
                            except Exception:
                                pass
                            if not logged_in_detected:
                                log(f"✅ Вхід успішно виявлено (ID: {user_id})! Авторизацію збережено. Можете закрити вікно.")
                                logged_in_detected = True
                    except Exception:
                        pass

                try:
                    context.storage_state(path=self.state_file)
                except Exception:
                    pass

                try:
                    browser.close()
                except Exception:
                    pass

                if logged_in_detected or self.is_logged_in():
                    log("УСПІХ: Сесію авторизації збережено!")
                    return {"success": True}
                else:
                    log("УВАГА: Авторизація не була завершена.")
                    return {"success": False, "error": "Авторизація не завершена. Переконайтесь, що увійшли в акаунт у відкритому вікні браузера."}

        except Exception as e:
            err_msg = str(e)
            log(f"Помилка відкриття браузера: {err_msg}")
            return {"success": False, "error": err_msg}

    def sync_birthdays(self, progress_callback=None, headless=False) -> dict:
        """
        Navigates to Facebook Birthdays page using saved storage state,
        parses friend details and saves them into the local database.
        """
        _ensure_event_loop()

        def log(msg: str):
            print(f"[FB Scraper] {msg}")
            if progress_callback:
                progress_callback(msg)

        log("Запуск браузера для синхронізації...")
        scraped_friends = []

        try:
            with sync_playwright() as p:
                browser = _launch_browser_with_fallback(
                    p,
                    headless=headless,
                    args=["--disable-notifications"]
                )

                kwargs = {}
                if os.path.exists(self.state_file):
                    kwargs["storage_state"] = self.state_file

                context = browser.new_context(**kwargs)
                page = context.new_page()

                log("Перехід на facebook.com/events/birthdays/...")
                page.goto("https://www.facebook.com/events/birthdays/", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)

                cookies = context.cookies()
                c_user_cookie = [c for c in cookies if c.get("name") == "c_user"]
                
                if not c_user_cookie and ("login" in page.url.lower() or page.query_selector('input[name="email"]')):
                    log("ПОМИЛКА: Необхідно авторизуватися в Facebook!")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "error": "Акаунт Facebook не авторизовано у вікні програми.\nНатисніть '🔑 Вхід у Facebook' і виконайте вхід у вікні Chrome, що відкриється.",
                        "count": 0
                    }

                log("Авторизація підтверджена! Зчитування днів народження...")

                try:
                    context.storage_state(path=self.state_file)
                except Exception:
                    pass

                for i in range(12):
                    page.keyboard.press("PageDown")
                    time.sleep(0.5)

                time.sleep(1.5)

                main_element = page.query_selector('div[role="main"]')
                if not main_element:
                    main_element = page.body

                processed_names = set()
                items = main_element.query_selector_all('div')
                for item in items:
                    try:
                        link = item.query_selector('a[href*="/user/"], a[href*="profile.php"], a[href*="facebook.com/"]')
                        if not link:
                            continue

                        name = link.inner_text().strip()
                        href = link.get_attribute('href') or ""

                        if not name or name in processed_names or len(name) < 2:
                            continue

                        if name.lower() in ["головна", "події", "дні народження", "друзі", "facebook", "home", "events", "menu"]:
                            continue

                        img = item.query_selector('img')
                        avatar_url = img.get_attribute('src') if img else ""

                        item_text = item.inner_text()
                        day, month, year = parse_birthday_text(item_text)

                        if day and month:
                            processed_names.add(name)
                            friend_data = {
                                "fb_name": name,
                                "profile_url": href,
                                "avatar_url": avatar_url or "",
                                "birth_day": day,
                                "birth_month": month,
                                "birth_year": year,
                                "birthday_str": f"{day} {month}",
                                "raw_info": item_text[:100]
                            }
                            self.db.upsert_friend(**friend_data)
                            scraped_friends.append(friend_data)
                    except Exception:
                        continue

                log(f"Успішно імпортовано/оновлено {len(scraped_friends)} друзів з датами народження.")
                try:
                    browser.close()
                except Exception:
                    pass
                return {"success": True, "count": len(scraped_friends), "friends": scraped_friends}

        except Exception as e:
            err_msg = str(e)
            log(f"Помилка під час синхронізації: {err_msg}")
            return {"success": False, "error": err_msg, "count": 0}

    def generate_demo_data(self):
        """Generates realistic demo friends with birthdays for testing UI."""
        from datetime import date, timedelta

        today = date.today()
        mon = today - timedelta(days=today.weekday())

        demo_list = [
            {"fb_name": "Олександр Коваленко", "profile_url": "https://facebook.com", "birth_day": today.day, "birth_month": today.month, "birthday_str": f"{today.day} серпня"},
            {"fb_name": "Марія Шевченко", "profile_url": "https://facebook.com", "birth_day": (mon + timedelta(days=2)).day, "birth_month": (mon + timedelta(days=2)).month, "birthday_str": f"{(mon + timedelta(days=2)).day} серпня"},
            {"fb_name": "Дмитро Мельник", "profile_url": "https://facebook.com", "birth_day": (mon + timedelta(days=4)).day, "birth_month": (mon + timedelta(days=4)).month, "birthday_str": f"{(mon + timedelta(days=4)).day} серпня"},
            {"fb_name": "Анна Бойко", "profile_url": "https://facebook.com", "birth_day": 12, "birth_month": 9, "birthday_str": "12 вересня"},
            {"fb_name": "Віталій Кравченко", "profile_url": "https://facebook.com", "birth_day": 25, "birth_month": 9, "birthday_str": "25 вересня"},
            {"fb_name": "Олена Ткаченко", "profile_url": "https://facebook.com", "birth_day": 5, "birth_month": 10, "birthday_str": "5 жовтня"},
        ]

        for item in demo_list:
            self.db.upsert_friend(
                fb_name=item["fb_name"],
                profile_url=item["profile_url"],
                birth_day=item["birth_day"],
                birth_month=item["birth_month"],
                birthday_str=item["birthday_str"],
                raw_info="Тестові дані"
            )
        return len(demo_list)
