import sys
import os
import webbrowser
import traceback
import hashlib
import urllib.request
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QTabWidget, QMessageBox, QProgressBar, QGridLayout, QSizePolicy, QGroupBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QLinearGradient, QBrush, QPixmap, QPainterPath

from database import BirthdayDatabase
from fb_scraper import FacebookScraper
from date_utils import get_days_until, is_birthday_in_current_week, is_birthday_today
from notifier import check_and_notify_birthdays, send_desktop_notification, send_windows_notification

AVATAR_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".fb_birthday_app", "avatars")
os.makedirs(AVATAR_CACHE_DIR, exist_ok=True)

def make_circular_pixmap(pixmap: QPixmap, size: int = 44) -> QPixmap:
    if pixmap.isNull():
        return QPixmap()
    
    scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    out_pixmap = QPixmap(size, size)
    out_pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(out_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    painter.drawPixmap(0, 0, scaled, x, y, size, size)
    painter.end()
    
    return out_pixmap

class AvatarDownloaderWorker(QThread):
    avatar_loaded = pyqtSignal(str, QPixmap)

    def __init__(self, avatar_url: str, cache_path: str):
        super().__init__()
        self.avatar_url = avatar_url
        self.cache_path = cache_path

    def run(self):
        try:
            req = urllib.request.Request(
                self.avatar_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                if data:
                    with open(self.cache_path, "wb") as f:
                        f.write(data)
                    pixmap = QPixmap(self.cache_path)
                    if not pixmap.isNull():
                        self.avatar_loaded.emit(self.cache_path, pixmap)
        except Exception:
            pass

# Ultra-Modern Glassmorphism & Cyberpunk Dark Theme Stylesheet
ULTRA_DARK_STYLESHEET = """
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Ubuntu", "Cantarell", "Helvetica Neue", sans-serif;
}
QMainWindow {
    background-color: #161717;
}
QWidget {
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
    color: #e5e8e6;
}

/* Header & Containers */
QFrame#HeaderFrame {
    background-color: #202222;
    border-bottom: 1px solid #2c302f;
    padding: 8px 16px;
}
QFrame#StatCardToday {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #106038, stop:1 #167a48);
    border: 1px solid #25a260;
    border-radius: 4px;
    padding: 0px;
}
QFrame#StatCardWeek {
    background-color: #202222;
    border: 1px solid #2c302f;
    border-radius: 4px;
    padding: 0px;
}
QFrame#StatCardTotal {
    background-color: #202222;
    border: 1px solid #106038;
    border-radius: 4px;
    padding: 0px;
}
QFrame#StatCardWeek:hover, QFrame#StatCardTotal:hover {
    border: 1px solid #25a260;
}

/* Friend Cards */
QFrame#FriendCard {
    background-color: #202222;
    border-radius: 4px;
    border: 1px solid #2c302f;
}
QFrame#FriendCard:hover {
    border: 1px solid #106038;
    background-color: #242727;
}
QFrame#FriendCardToday {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b181e, stop:1 #202222);
    border-radius: 4px;
    border: 2px solid #e60017;
}
QFrame#FriendCardToday:hover {
    border: 2px solid #ff4d4d;
}

/* Labels & Typography */
QLabel#AppTitle {
    font-size: 20px;
    font-weight: 800;
    color: #e5e8e6;
    letter-spacing: 0.5px;
}
QLabel#StatusBadge {
    font-size: 13px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 4px;
    background-color: #282c2b;
    color: #25a260;
    border: 1px solid #373d3b;
}
QLabel#StatNumHighlight {
    font-size: 16px;
    font-weight: 900;
    color: #ffffff;
}
QLabel#StatNumNormal {
    font-size: 16px;
    font-weight: 800;
    color: #25a260;
}
QLabel#StatTitleHighlight {
    font-size: 12px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#StatTitleNormal {
    font-size: 12px;
    font-weight: 700;
    color: #8f9895;
}

/* Buttons */
QPushButton {
    background-color: #106038;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    border-radius: 4px;
    padding: 8px 16px;
    border: none;
}
QPushButton:hover {
    background-color: #167a48;
}
QPushButton:pressed {
    background-color: #0d4d2d;
}
QPushButton#FbButton {
    background-color: #e60017;
    color: #ffffff;
}
QPushButton#FbButton:hover {
    background-color: #ff1a30;
}
QPushButton#SecondaryBtn {
    background-color: #282c2b;
    color: #e5e8e6;
    border: 1px solid #373d3b;
}
QPushButton#SecondaryBtn:hover {
    background-color: #106038;
    border: 1px solid #167a48;
    color: #ffffff;
}

/* Inputs & Tabs */
QLineEdit {
    background-color: #282c2b;
    border: 1px solid #373d3b;
    border-radius: 4px;
    padding: 7px 10px;
    color: #e5e8e6;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid #106038;
    background-color: #2c3130;
}
QTabWidget::pane {
    border: 1px solid #2c302f;
    background-color: #202222;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #282c2b;
    color: #8f9895;
    padding: 8px 18px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 3px;
    font-weight: 700;
    font-size: 14px;
    border: 1px solid #373d3b;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #106038;
    color: #ffffff;
    border: 1px solid #167a48;
}
QGroupBox {
    background-color: #202222;
    border: 1px solid #2c302f;
    border-radius: 4px;
    margin-top: 14px;
    padding: 16px;
    font-weight: 700;
    color: #e5e8e6;
}
QScrollArea {
    border: none;
    background: transparent;
}
"""

class LoginWorker(QThread):
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)

    def __init__(self, scraper: FacebookScraper):
        super().__init__()
        self.scraper = scraper

    def run(self):
        res = self.scraper.launch_login_session(status_callback=self.status_signal.emit)
        self.finished_signal.emit(res)


class SyncWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)

    def __init__(self, scraper: FacebookScraper):
        super().__init__()
        self.scraper = scraper

    def run(self):
        result = self.scraper.sync_birthdays(progress_callback=self.progress_signal.emit)
        self.finished_signal.emit(result)


class FriendCardWidget(QFrame):
    AVATAR_SIZE = 44

    def __init__(self, friend: dict, parent=None):
        super().__init__(parent)
        is_today = is_birthday_today(friend.get("birth_day"), friend.get("birth_month"))
        self.setObjectName("FriendCardToday" if is_today else "FriendCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # Avatar Profile Picture / Initial Badge Fallback
        name = friend.get("fb_name", "Друг")
        initials = "".join([part[0].upper() for part in name.split()[:2]]) if name else "?"
        avatar_url = (friend.get("avatar_url") or "").strip()

        self.avatar_label = QLabel(initials)
        self.avatar_label.setFixedSize(self.AVATAR_SIZE, self.AVATAR_SIZE)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        radius = self.AVATAR_SIZE // 2
        if is_today:
            self.avatar_style = f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e60017, stop:1 #ff4d4d);
                color: #ffffff;
                font-size: 16px;
                font-weight: 900;
                border-radius: {radius}px;
            """
        else:
            self.avatar_style = f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #106038, stop:1 #167a48);
                color: #ffffff;
                font-size: 15px;
                font-weight: 800;
                border-radius: {radius}px;
            """
        self.avatar_label.setStyleSheet(self.avatar_style)

        if avatar_url:
            url_hash = hashlib.md5(avatar_url.encode('utf-8')).hexdigest()
            cache_path = os.path.join(AVATAR_CACHE_DIR, f"{url_hash}.jpg")
            if os.path.exists(cache_path):
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    self.set_circular_avatar(pixmap)
            else:
                self.downloader = AvatarDownloaderWorker(avatar_url, cache_path)
                self.downloader.avatar_loaded.connect(self.on_avatar_downloaded)
                self.downloader.start()

        # Info Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #e5e8e6;")

        bday_str = friend.get("birthday_str", "")
        days_until = get_days_until(friend.get("birth_day"), friend.get("birth_month"))

        # Badge pill logic
        if is_today:
            pill_text = f"🎉 СЬОГОДНІ ДЕНЬ НАРОДЖЕННЯ! ({bday_str})"
            pill_style = "background-color: #e60017; color: #ffffff; font-weight: 800; padding: 2px 8px; border-radius: 3px; font-size: 11px;"
        elif days_until == 1:
            pill_text = f"🎂 ЗАВТРА ({bday_str})"
            pill_style = "background-color: #106038; color: #ffffff; font-weight: 800; padding: 2px 8px; border-radius: 3px; font-size: 11px;"
        elif 0 < days_until <= 7:
            pill_text = f"📅 НА ЦЬОМУ ТИЖНІ (через {days_until} дн.) — {bday_str}"
            pill_style = "background-color: #177846; color: #ffffff; font-weight: 800; padding: 2px 8px; border-radius: 3px; font-size: 11px;"
        elif days_until < 0:
            pill_text = f"🗓️ Був на цьому тижні ({abs(days_until)} дн. тому) — {bday_str}"
            pill_style = "background-color: #282c2b; color: #8f9895; font-weight: 600; padding: 2px 8px; border-radius: 3px; font-size: 11px;"
        else:
            pill_text = f"🗓️ {bday_str}"
            pill_style = "background-color: #282c2b; color: #25a260; font-weight: 600; padding: 2px 8px; border-radius: 3px; font-size: 11px;"

        pill_label = QLabel(pill_text)
        pill_label.setStyleSheet(pill_style)
        pill_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        info_layout.addWidget(name_label)
        info_layout.addWidget(pill_label)

        layout.addWidget(self.avatar_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        # Action Buttons
        raw_url = friend.get("profile_url", "")
        from fb_scraper import clean_profile_url
        profile_url = clean_profile_url(raw_url)

        if profile_url:
            btn_open = QPushButton("🌐 Профіль FB")
            btn_open.setObjectName("SecondaryBtn")
            btn_open.setStyleSheet("padding: 4px 10px; font-size: 12px; border-radius: 3px;")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.clicked.connect(lambda checked=False, url=profile_url: webbrowser.open(url))
            layout.addWidget(btn_open)

    def on_avatar_downloaded(self, cache_path: str, pixmap: QPixmap):
        self.set_circular_avatar(pixmap)

    def set_circular_avatar(self, pixmap: QPixmap):
        circular_pix = make_circular_pixmap(pixmap, self.AVATAR_SIZE)
        if not circular_pix.isNull():
            radius = self.AVATAR_SIZE // 2
            self.avatar_label.setText("")
            self.avatar_label.setPixmap(circular_pix)
            self.avatar_label.setStyleSheet(f"border-radius: {radius}px; background: transparent;")


class BirthdayAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = BirthdayDatabase()
        self.scraper = FacebookScraper(db=self.db)
        self.sync_thread = None
        self.login_thread = None

        self.setWindowTitle("Facebook Birthday Assistant v2.0")
        self.setMinimumSize(920, 680)
        self.setStyleSheet(ULTRA_DARK_STYLESHEET)

        self._init_ui()
        self._refresh_data()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Header Bar
        header_layout = QHBoxLayout()
        
        app_title = QLabel("🎂 FB BIRTHDAY ASSISTANT")
        app_title.setObjectName("AppTitle")

        self.lbl_status_badge = QLabel("⚪ Перевірка...")
        self.lbl_status_badge.setObjectName("StatusBadge")

        header_layout.addWidget(app_title)
        header_layout.addWidget(self.lbl_status_badge)
        header_layout.addStretch()

        self.btn_fb_login = QPushButton("🔑 Вхід у Facebook")
        self.btn_fb_login.setObjectName("FbButton")
        self.btn_fb_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fb_login.clicked.connect(self._on_fb_login_clicked)

        self.btn_sync = QPushButton("🔄 Синхронізувати")
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync.clicked.connect(self._on_sync_clicked)

        header_layout.addWidget(self.btn_fb_login)
        header_layout.addWidget(self.btn_sync)
        main_layout.addLayout(header_layout)

        # Stat Hero Banner Cards (Compact Badges)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        # Card 1: Today
        self.card_today = QFrame()
        self.card_today.setObjectName("StatCardToday")
        today_l = QHBoxLayout(self.card_today)
        today_l.setContentsMargins(12, 6, 12, 6)
        lbl_today_title = QLabel("🎈 Сьогодні святкують", self.card_today)
        lbl_today_title.setObjectName("StatTitleHighlight")
        self.lbl_today_num = QLabel("0", self.card_today)
        self.lbl_today_num.setObjectName("StatNumHighlight")
        today_l.addWidget(lbl_today_title)
        today_l.addStretch()
        today_l.addWidget(self.lbl_today_num)

        # Card 2: Current Week
        self.card_week = QFrame()
        self.card_week.setObjectName("StatCardWeek")
        week_l = QHBoxLayout(self.card_week)
        week_l.setContentsMargins(12, 6, 12, 6)
        lbl_week_title = QLabel("📅 На цьому тижні", self.card_week)
        lbl_week_title.setObjectName("StatTitleNormal")
        self.lbl_week_num = QLabel("0", self.card_week)
        self.lbl_week_num.setObjectName("StatNumNormal")
        week_l.addWidget(lbl_week_title)
        week_l.addStretch()
        week_l.addWidget(self.lbl_week_num)

        # Card 3: Total Database
        self.card_total = QFrame()
        self.card_total.setObjectName("StatCardTotal")
        total_l = QHBoxLayout(self.card_total)
        total_l.setContentsMargins(12, 6, 12, 6)
        lbl_total_title = QLabel("👥 Усього в базі", self.card_total)
        lbl_total_title.setObjectName("StatTitleNormal")
        self.lbl_total_num = QLabel("0", self.card_total)
        self.lbl_total_num.setObjectName("StatNumNormal")
        total_l.addWidget(lbl_total_title)
        total_l.addStretch()
        total_l.addWidget(self.lbl_total_num)

        stats_layout.addWidget(self.card_today)
        stats_layout.addWidget(self.card_week)
        stats_layout.addWidget(self.card_total)
        main_layout.addLayout(stats_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #202222; border-radius: 4px; min-height: 6px; max-height: 6px; } QProgressBar::chunk { background-color: #106038; border-radius: 4px; }")
        main_layout.addWidget(self.progress_bar)

        # Main Navigation Tabs
        self.tabs = QTabWidget()

        # Tab 1: Current Week & Search
        self.tab_week = QWidget()
        tab_week_layout = QVBoxLayout(self.tab_week)
        tab_week_layout.setContentsMargins(0, 10, 0, 0)
        tab_week_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Швидкий пошук друга за ім'ям або датою...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        tab_week_layout.addWidget(self.search_input)

        self.scroll_week = QScrollArea()
        self.scroll_week.setWidgetResizable(True)
        self.scroll_week_content = QWidget()
        self.layout_week_list = QVBoxLayout(self.scroll_week_content)
        self.layout_week_list.setSpacing(6)
        self.layout_week_list.addStretch()
        self.scroll_week.setWidget(self.scroll_week_content)

        tab_week_layout.addWidget(self.scroll_week)

        # Tab 2: Settings
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout(self.tab_settings)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(16)

        group_cookies = QGroupBox("🔑 Альтернативна авторизація (Ручні куки c_user & xs)")
        group_l = QVBoxLayout(group_cookies)
        group_l.setSpacing(10)

        lbl_cookie_info = QLabel("Ви можете вставити значення c_user та xs зі свого браузера Chrome/Edge:")
        lbl_cookie_info.setStyleSheet("color: #8f9895; font-size: 13px;")

        self.input_c_user = QLineEdit()
        self.input_c_user.setPlaceholderText("Введіть c_user (наприклад: 10000123456789)")

        self.input_xs = QLineEdit()
        self.input_xs.setPlaceholderText("Введіть xs (наприклад: 44%3A...)")

        btn_save_cookies = QPushButton("Зберегти куки Facebook")
        btn_save_cookies.setObjectName("SecondaryBtn")
        btn_save_cookies.clicked.connect(self._on_save_cookies_clicked)

        group_l.addWidget(lbl_cookie_info)
        group_l.addWidget(self.input_c_user)
        group_l.addWidget(self.input_xs)
        group_l.addWidget(btn_save_cookies)

        btn_demo = QPushButton("🧪 Завантажити демо-дані")
        btn_demo.setObjectName("SecondaryBtn")
        btn_demo.clicked.connect(self._on_load_demo_clicked)

        btn_notify_test = QPushButton("🔔 Перевірити сповіщення Windows")
        btn_notify_test.setObjectName("SecondaryBtn")
        btn_notify_test.clicked.connect(self._on_test_notification_clicked)

        settings_layout.addWidget(group_cookies)
        settings_layout.addWidget(btn_demo)
        settings_layout.addWidget(btn_notify_test)
        settings_layout.addStretch()

        self.tabs.addTab(self.tab_week, "📅 Дні народження")
        self.tabs.addTab(self.tab_settings, "⚙️ Налаштування & Тест")
        main_layout.addWidget(self.tabs)

        self.lbl_status = QLabel("Готовий до роботи.")
        self.lbl_status.setStyleSheet("color: #8f9895; font-size: 13px;")
        main_layout.addWidget(self.lbl_status)

    def _refresh_data(self):
        stats = self.db.get_stats()
        self.lbl_today_num.setText(str(stats["today_count"]))
        self.lbl_week_num.setText(str(stats["this_week_count"]))
        self.lbl_total_num.setText(str(stats["total_friends"]))

        self._populate_week_friends()

        if self.scraper.is_logged_in():
            self.lbl_status_badge.setText("🟢 FB Авторизовано")
            self.lbl_status_badge.setStyleSheet("font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 10px; background-color: #106038; color: #ffffff; border: 1px solid #167a48;")
            self.lbl_status.setText("Акаунт Facebook авторизований.")
        else:
            self.lbl_status_badge.setText("🟡 Потрібен вхід")
            self.lbl_status_badge.setStyleSheet("font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 10px; background-color: #282c2b; color: #d9a726; border: 1px solid #373d3b;")
            self.lbl_status.setText("Акаунт не авторизований. Натисніть '🔑 Вхід у Facebook'.")

        check_and_notify_birthdays(self.db)

    def _populate_week_friends(self):
        search_text = self.search_input.text().strip() if hasattr(self, 'search_input') else ""
        self._clear_layout(self.layout_week_list)

        if search_text:
            friends = self.db.search_friends(search_text)
        else:
            friends = self.db.get_friends_this_week()

        if not friends:
            msg = f"🔍 За запитом '{search_text}' нічого не знайдено." if search_text else "🎈 На цьому тижні немає днів народження друзів."
            no_data = QLabel(msg)
            no_data.setStyleSheet("font-size: 15px; font-weight: 600; color: #8f9895; padding: 30px;")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_week_list.addWidget(no_data)
        else:
            for friend in friends:
                self.layout_week_list.addWidget(FriendCardWidget(friend))
        self.layout_week_list.addStretch()

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_search_text_changed(self, text: str):
        self._populate_week_friends()

    def _on_fb_login_clicked(self):
        self.btn_fb_login.setEnabled(False)
        self.lbl_status.setText("Відкриття браузера... Будь ласка, авторизуйтесь у вікні Facebook.")

        self.login_thread = LoginWorker(self.scraper)
        self.login_thread.status_signal.connect(lambda msg: self.lbl_status.setText(msg))
        self.login_thread.finished_signal.connect(self._on_login_finished)
        self.login_thread.start()

    def _on_login_finished(self, res: dict):
        self.btn_fb_login.setEnabled(True)
        if res.get("success"):
            QMessageBox.information(self, "Авторизація успішна", "Вхід у Facebook успішно виконано!")
            self.lbl_status.setText("✅ Сесію збережено. Натисніть 'Синхронізувати'.")
        else:
            QMessageBox.warning(self, "Авторизацію не завершено", f"{res.get('error', 'Вхід не було завершено')}")
            self.lbl_status.setText(f"Статус: {res.get('error')}")
        self._refresh_data()

    def _on_save_cookies_clicked(self):
        c_user = self.input_c_user.text().strip()
        xs = self.input_xs.text().strip()
        if not c_user or not xs:
            QMessageBox.warning(self, "Увага", "Будь ласка, введіть значення c_user та xs!")
            return

        ok = self.scraper.set_manual_cookies(c_user, xs)
        if ok:
            QMessageBox.information(self, "Успіх", "Куки Facebook збережено!")
            self._refresh_data()
        else:
            QMessageBox.warning(self, "Помилка", "Не вдалося зберегти куки.")

    def _on_sync_clicked(self):
        self.btn_sync.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Запуск синхронізації з Facebook...")

        self.sync_thread = SyncWorker(self.scraper)
        self.sync_thread.progress_signal.connect(lambda msg: self.lbl_status.setText(msg))
        self.sync_thread.finished_signal.connect(self._on_sync_finished)
        self.sync_thread.start()

    def _on_sync_finished(self, result: dict):
        self.btn_sync.setEnabled(True)
        self.progress_bar.setVisible(False)
        if result.get("success"):
            QMessageBox.information(self, "Успіх", f"Успішно оновлено друзів: {result.get('count', 0)}")
            self.lbl_status.setText("Синхронізацію успішно завершено.")
        else:
            QMessageBox.warning(self, "Увага", f"{result.get('error', 'Помилка під час синхронізації')}")
            self.lbl_status.setText(f"Помилка: {result.get('error')}")
        self._refresh_data()

    def _on_load_demo_clicked(self):
        count = self.scraper.generate_demo_data()
        self._refresh_data()
        QMessageBox.information(self, "Демо-дані", f"Завантажено {count} тестових записів у базу даних!")

    def _on_test_notification_clicked(self):
        success = send_desktop_notification("🎂 Тестове сповіщення", "Додаток перевіряє роботу системних сповіщень!")
        if success:
            QMessageBox.information(self, "Сповіщення", "Сповіщення успішно надіслано в систему!")
        else:
            QMessageBox.warning(self, "Помилка", "Не вдалося надіслати сповіщення.")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("[UNCAUGHT EXCEPTION]:\n", err_text)
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Помилка виконання")
    msg_box.setText(f"Виникла виняткова ситуація:\n{exc_value}")
    msg_box.setDetailedText(err_text)
    msg_box.exec()

sys.excepthook = handle_exception

def main():
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)
    window = BirthdayAssistantApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
