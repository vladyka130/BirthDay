from fb_scraper import FacebookScraper
import traceback

def test_login():
    print("[Test Full Login] Initializing scraper...")
    scraper = FacebookScraper()
    print("[Test Full Login] Calling launch_login_session...")
    try:
        res = scraper.launch_login_session(status_callback=lambda msg: print("[STATUS]", msg))
        print("[Test Full Login] Result:", res)
    except Exception as e:
        print("[Test Full Login] EXCEPTION OCCURRED:")
        traceback.print_exc()

if __name__ == "__main__":
    test_login()
