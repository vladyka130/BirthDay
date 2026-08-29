import sys
import os
import webbrowser
import traceback
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QTabWidget, QMessageBox, QProgressBar, QGridLayout, QSizePolicy, QGroupBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QLinearGradient, QBrush

from database import BirthdayDatabase
from fb_scraper import FacebookScraper
from date_utils import get_days_until, is_birthday_in_current_week, is_birthday_today
from notifier import check_and_notify_birthdays, send_windows_notification

# Ultra-Modern Glassmorphism & Cyberpunk Dark Theme Stylesheet
ULTRA_DARK_STYLESHEET = """
QMainWindow {
    background-color: #0d0e15;
}
QWidget {
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
    color: #a9b1d6;
}

/* Header & Glass Containers */
QFrame#HeaderFrame {
    background-color: #161622;
    border-bottom: 1px solid #1f2335;
    padding: 8px 16px;
}
QFrame#StatCardToday {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff007f, stop:1 #7a00ff);
    border-radius: 16px;
    padding: 18px;
}
QFrame#StatCardWeek {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1b26, stop:1 #24283b);
    border: 1px solid #3b4261;
    border-radius: 16px;
    padding: 18px;
}
QFrame#StatCardTotal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #161622, stop:1 #1f2335);
    border: 1px solid #2ac3de;
    border-radius: 16px;
    padding: 18px;
}
QFrame#StatCardWeek:hover, QFrame#StatCardTotal:hover {
    border: 1px solid #7dcfff;
}

/* Friend Cards */
QFrame#FriendCard {
    background-color: #161622;
    border-radius: 14px;
    border: 1px solid #1f2335;
}
QFrame#FriendCard:hover {
    border: 1px solid #7dcfff;
    background-color: #1a1b26;
}
QFrame#FriendCardToday {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #291528, stop:1 #161622);
    border-radius: 14px;
    border: 2px solid #ff757f;
}
QFrame#FriendCardToday:hover {
    border: 2px solid #c0caf5;
}

/* Labels & Typography */
QLabel#AppTitle {
    font-size: 22px;
    font-weight: 800;
    color: #7dcfff;
    letter-spacing: 0.5px;
}
QLabel#StatusBadge {
    font-size: 13px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 12px;
    background-color: #1f2335;
    color: #7aa2f7;
}
QLabel#StatNumHighlight {
    font-size: 32px;
    font-weight: 900;
    color: #ffffff;
}
QLabel#StatNumNormal {
    font-size: 30px;
    font-weight: 800;
    color: #7dcfff;
}
QLabel#StatTitleHighlight {
    font-size: 13px;
    font-weight: 700;
    color: #f7768e;
    text-transform: uppercase;
}
QLabel#StatTitleNormal {
    font-size: 13px;
    font-weight: 700;
    color: #565f89;
    text-transform: uppercase;
}

/* Buttons */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7dcfff, stop:1 #7aa2f7);
    color: #0f0f17;
    font-size: 14px;
    font-weight: 700;
    border-radius: 10px;
    padding: 10px 20px;
    border: none;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #bb9af7, stop:1 #7dcfff);
}
QPushButton:pressed {
    background-color: #73daca;
}
QPushButton#FbButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1877f2, stop:1 #0052cc);
    color: #ffffff;
}
QPushButton#FbButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #1d4ed8);
}
QPushButton#SecondaryBtn {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #3b4261;
}
QPushButton#SecondaryBtn:hover {
    background-color: #24283b;
    border: 1px solid #7dcfff;
    color: #ffffff;
}

/* Inputs & Tabs */
QLineEdit {
    background-color: #161622;
    border: 1px solid #24283b;
    border-radius: 10px;
    padding: 10px 14px;
    color: #c0caf5;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid #7dcfff;
    background-color: #1a1b26;
}
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background-color: #161622;
    color: #565f89;
    padding: 12px 24px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 6px;
    font-weight: 700;
    font-size: 14px;
}
QTabBar::tab:selected {
    background-color: #1f2335;
    color: #7dcfff;
    border-bottom: 3px solid #7dcfff;
}
QGroupBox {
    background-color: #161622;
    border: 1px solid #24283b;
    border-radius: 12px;
    margin-top: 14px;
    padding: 20px;
    font-weight: 700;
    color: #7dcfff;
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
    def __init__(self, friend: dict, parent=None):
        super().__init__(parent)
        is_today = is_birthday_today(friend.get("birth_day"), friend.get("birth_month"))
        self.setObjectName("FriendCardToday" if is_today else "FriendCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(16)

        # Avatar Initial Badge
        name = friend.get("fb_name", "Друг")
        initials = "".join([part[0].upper() for part in name.split()[:2]]) if name else "?"

        avatar_label = QLabel(initials)
        avatar_label.setFixedSize(52, 52)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if is_today:
            avatar_style = """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff007f, stop:1 #7a00ff);
                color: #ffffff;
                font-size: 20px;
                font-weight: 900;
                border-radius: 26px;
            """
        else:
            avatar_style = """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7dcfff, stop:1 #7aa2f7);
                color: #0f0f17;
                font-size: 19px;
                font-weight: 800;
                border-radius: 26px;
            """
        avatar_label.setStyleSheet(avatar_style)

        # Info Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 17px; font-weight: 700; color: #c0caf5;")

        bday_str = friend.get("birthday_str", "")
        days_until = get_days_until(friend.get("birth_day"), friend.get("birth_month"))

        # Badge pill logic
        if is_today:
            pill_text = f"🎉 СЬОГОДНІ ДЕНЬ НАРОДЖЕННЯ! ({bday_str})"
            pill_style = "background-color: #ff757f; color: #15161e; font-weight: 800; padding: 4px 10px; border-radius: 8px; font-size: 12px;"
        elif days_until == 1:
            pill_text = f"🎂 ЗАВТРА ({bday_str})"
            pill_style = "background-color: #73daca; color: #15161e; font-weight: 800; padding: 4px 10px; border-radius: 8px; font-size: 12px;"
        elif 0 < days_until <= 7:
            pill_text = f"📅 НА ЦЬОМУ ТИЖНІ (через {days_until} дн.) — {bday_str}"
            pill_style = "background-color: #7aa2f7; color: #15161e; font-weight: 800; padding: 4px 10px; border-radius: 8px; font-size: 12px;"
        elif days_until < 0:
            pill_text = f"🗓️ Був на цьому тижні ({abs(days_until)} дн. тому) — {bday_str}"
            pill_style = "background-color: #24283b; color: #565f89; font-weight: 600; padding: 4px 10px; border-radius: 8px; font-size: 12px;"
        else:
            pill_text = f"🗓️ {bday_str}"
            pill_style = "background-color: #1f2335; color: #7dcfff; font-weight: 600; padding: 4px 10px; border-radius: 8px; font-size: 12px;"

        pill_label = QLabel(pill_text)
        pill_label.setStyleSheet(pill_style)
        pill_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        info_layout.addWidget(name_label)
        info_layout.addWidget(pill_label)

        layout.addWidget(avatar_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        # Action Buttons
        profile_url = friend.get("profile_url", "")
        if profile_url:
            btn_open = QPushButton("🌐 Профіль FB")
            btn_open.setObjectName("SecondaryBtn")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.clicked.connect(lambda: webbrowser.open(profile_url))
            layout.addWidget(btn_open)


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
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

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

        # Stat Hero Banner Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        # Card 1: Today
        self.card_today = QFrame()
        self.card_today.setObjectName("StatCardToday")
        today_l = QVBoxLayout(self.card_today)
        self.lbl_today_num = QLabel("0", self.card_today)
        self.lbl_today_num.setObjectName("StatNumHighlight")
        lbl_today_title = QLabel("🎈 Сьогодні святкують", self.card_today)
        lbl_today_title.setObjectName("StatTitleHighlight")
        today_l.addWidget(lbl_today_title)
        today_l.addWidget(self.lbl_today_num)

        # Card 2: Current Week
        self.card_week = QFrame()
        self.card_week.setObjectName("StatCardWeek")
        week_l = QVBoxLayout(self.card_week)
        self.lbl_week_num = QLabel("0", self.card_week)
        self.lbl_week_num.setObjectName("StatNumNormal")
        lbl_week_title = QLabel("📅 На цьому тижні", self.card_week)
        lbl_week_title.setObjectName("StatTitleNormal")
        week_l.addWidget(lbl_week_title)
        week_l.addWidget(self.lbl_week_num)

        # Card 3: Total Database
        self.card_total = QFrame()
        self.card_total.setObjectName("StatCardTotal")
        total_l = QVBoxLayout(self.card_total)
        self.lbl_total_num = QLabel("0", self.card_total)
        self.lbl_total_num.setObjectName("StatNumNormal")
        lbl_total_title = QLabel("👥 Усього в базі", self.card_total)
        lbl_total_title.setObjectName("StatTitleNormal")
        total_l.addWidget(lbl_total_title)
        total_l.addWidget(self.lbl_total_num)

        stats_layout.addWidget(self.card_today)
        stats_layout.addWidget(self.card_week)
        stats_layout.addWidget(self.card_total)
        main_layout.addLayout(stats_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #161622; border-radius: 6px; min-height: 8px; max-height: 8px; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7dcfff, stop:1 #bb9af7); border-radius: 6px; }")
        main_layout.addWidget(self.progress_bar)

        # Main Navigation Tabs
        self.tabs = QTabWidget()

        # Tab 1: Current Week
        self.tab_week = QWidget()
        tab_week_layout = QVBoxLayout(self.tab_week)
        tab_week_layout.setContentsMargins(0, 14, 0, 0)

        self.scroll_week = QScrollArea()
        self.scroll_week.setWidgetResizable(True)
        self.scroll_week_content = QWidget()
        self.layout_week_list = QVBoxLayout(self.scroll_week_content)
        self.layout_week_list.setSpacing(12)
        self.layout_week_list.addStretch()
        self.scroll_week.setWidget(self.scroll_week_content)

        tab_week_layout.addWidget(self.scroll_week)

        # Tab 2: All Friends
        self.tab_all = QWidget()
        tab_all_layout = QVBoxLayout(self.tab_all)
        tab_all_layout.setContentsMargins(0, 14, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Пошук за ім'ям або датою народження...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        tab_all_layout.addWidget(self.search_input)

        self.scroll_all = QScrollArea()
        self.scroll_all.setWidgetResizable(True)
        self.scroll_all_content = QWidget()
        self.layout_all_list = QVBoxLayout(self.scroll_all_content)
        self.layout_all_list.setSpacing(12)
        self.layout_all_list.addStretch()
        self.scroll_all.setWidget(self.scroll_all_content)

        tab_all_layout.addWidget(self.scroll_all)

        # Tab 3: Settings
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout(self.tab_settings)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(16)

        group_cookies = QGroupBox("🔑 Альтернативна авторизація (Ручні куки c_user & xs)")
        group_l = QVBoxLayout(group_cookies)
        group_l.setSpacing(10)

        lbl_cookie_info = QLabel("Ви можете вставити значення c_user та xs зі свого браузера Chrome/Edge:")
        lbl_cookie_info.setStyleSheet("color: #565f89; font-size: 13px;")

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

        self.tabs.addTab(self.tab_week, "📅 На цьому тижні")
        self.tabs.addTab(self.tab_all, "👥 Усі друзі")
        self.tabs.addTab(self.tab_settings, "⚙️ Налаштування & Тест")
        main_layout.addWidget(self.tabs)

        self.lbl_status = QLabel("Готовий до роботи.")
        self.lbl_status.setStyleSheet("color: #565f89; font-size: 13px;")
        main_layout.addWidget(self.lbl_status)

    def _refresh_data(self):
        stats = self.db.get_stats()
        self.lbl_today_num.setText(str(stats["today_count"]))
        self.lbl_week_num.setText(str(stats["this_week_count"]))
        self.lbl_total_num.setText(str(stats["total_friends"]))

        self._clear_layout(self.layout_week_list)
        week_friends = self.db.get_friends_this_week()
        if not week_friends:
            no_data = QLabel("🎈 На цьому тижні немає днів народження друзів.")
            no_data.setStyleSheet("font-size: 16px; font-weight: 600; color: #565f89; padding: 40px;")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_week_list.addWidget(no_data)
        else:
            for friend in week_friends:
                self.layout_week_list.addWidget(FriendCardWidget(friend))
        self.layout_week_list.addStretch()

        self._populate_all_friends(self.db.get_all_friends())
        
        if self.scraper.is_logged_in():
            self.lbl_status_badge.setText("🟢 FB Авторизовано")
            self.lbl_status_badge.setStyleSheet("font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 12px; background-color: #1a2b26; color: #73daca;")
            self.lbl_status.setText("Акаунт Facebook авторизований.")
        else:
            self.lbl_status_badge.setText("🟡 Потрібен вхід")
            self.lbl_status_badge.setStyleSheet("font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 12px; background-color: #2b261a; color: #e0af68;")
            self.lbl_status.setText("Акаунт не авторизований. Натисніть '🔑 Вхід у Facebook'.")

        check_and_notify_birthdays(self.db)

    def _populate_all_friends(self, friends_list: list):
        self._clear_layout(self.layout_all_list)
        if not friends_list:
            no_data = QLabel("Список порожній. Натисніть 'Синхронізувати' або 'Завантажити демо-дані'.")
            no_data.setStyleSheet("font-size: 16px; font-weight: 600; color: #565f89; padding: 40px;")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_all_list.addWidget(no_data)
        else:
            for friend in friends_list:
                self.layout_all_list.addWidget(FriendCardWidget(friend))
        self.layout_all_list.addStretch()

    def _clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_search_text_changed(self, text: str):
        if not text.strip():
            self._populate_all_friends(self.db.get_all_friends())
        else:
            filtered = self.db.search_friends(text.strip())
            self._populate_all_friends(filtered)

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
        success = send_windows_notification("🎂 Тестове сповіщення", "Додаток перевіряє роботу сповіщень Windows!")
        if success:
            QMessageBox.information(self, "Сповіщення", "Сповіщення успішно надіслано в систему Windows!")
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
    app = QApplication(sys.argv)
    window = BirthdayAssistantApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
