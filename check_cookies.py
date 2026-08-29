import os
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "fb_user_data")

def check_cookies():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True
        )
        cookies = context.cookies()
        print(f"[Cookie Check] Total cookies found: {len(cookies)}")
        fb_cookies = [c for c in cookies if "facebook" in c.get("domain", "")]
        print(f"[Cookie Check] Facebook cookies count: {len(fb_cookies)}")
        c_user = [c for c in fb_cookies if c.get("name") == "c_user"]
        xs = [c for c in fb_cookies if c.get("name") == "xs"]
        print(f"[Cookie Check] c_user cookie: {c_user}")
        print(f"[Cookie Check] xs cookie: {xs}")
        context.close()

if __name__ == "__main__":
    check_cookies()
