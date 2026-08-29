import os
import sys
import subprocess
from date_utils import get_current_week_range
from database import BirthdayDatabase

def send_windows_notification(title: str, message: str):
    """Sends a Windows notification using winotify, plyer, or PowerShell fallback."""
    # Method 1: winotify
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="Facebook Birthday Assistant",
            title=title,
            msg=message,
            duration="short"
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True
    except Exception:
        pass

    # Method 2: plyer
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Facebook Birthday Assistant",
            timeout=10
        )
        return True
    except Exception:
        pass

    # Method 3: PowerShell Buran/Toast notification fallback (Native Windows)
    try:
        clean_title = title.replace('"', "'")
        clean_msg = message.replace('"', "'")
        ps_script = f"""
        [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.Visible = $True
        $notify.ShowBalloonTip(10000, "{clean_title}", "{clean_msg}", [System.Windows.Forms.ToolTipIcon]::Info)
        Start-Sleep -s 2
        $notify.Dispose()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=5)
        return True
    except Exception as e:
        print(f"[Notifier Fallback Error]: {e}")
        return False

def check_and_notify_birthdays(db: BirthdayDatabase = None) -> dict:
    if db is None:
        db = BirthdayDatabase()

    today_friends = db.get_friends_today()
    this_week_friends = db.get_friends_this_week()

    summary = {
        "today_count": len(today_friends),
        "this_week_count": len(this_week_friends),
        "notified": False
    }

    if today_friends:
        names = ", ".join([f["fb_name"] for f in today_friends[:3]])
        if len(today_friends) > 3:
            names += f" та ще {len(today_friends) - 3}"
        title = "🎈 Сьогодні день народження!"
        message = f"Сьогодні святкують: {names}. Не забудьте привітати!"
        send_windows_notification(title, message)
        summary["notified"] = True
    elif this_week_friends:
        names = ", ".join([f"{f['fb_name']} ({f['birthday_str']})" for f in this_week_friends[:3]])
        if len(this_week_friends) > 3:
            names += f" та ще {len(this_week_friends) - 3}"
        title = f"🎂 Дні народження на цьому тижні ({len(this_week_friends)})"
        message = f"На цьому тижні святкують: {names}."
        send_windows_notification(title, message)
        summary["notified"] = True

    return summary

if __name__ == "__main__":
    check_and_notify_birthdays()
