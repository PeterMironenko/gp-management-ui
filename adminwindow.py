import re
from typing import List, Optional
from PyQt5.QtCore import Qt, QLocale, QDate
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apiclient import ApiClient


SYSTEM_LOCALE = QLocale.system()
LOCALE_DATE_FORMAT = SYSTEM_LOCALE.dateFormat(QLocale.ShortFormat)


def _iso_date_to_locale_text(value: str) -> str:
    if not value:
        return ""
    date_value = QDate.fromString(value, "yyyy-MM-dd")
    if not date_value.isValid():
        return value
    return SYSTEM_LOCALE.toString(date_value, LOCALE_DATE_FORMAT)


def _locale_or_iso_to_iso_date(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None

    date_value = SYSTEM_LOCALE.toDate(text, LOCALE_DATE_FORMAT)
    if not date_value.isValid():
        date_value = QDate.fromString(text, "yyyy-MM-dd")
    if not date_value.isValid():
        return None
    return date_value.toString("yyyy-MM-dd")


def validate_staff_data(staff_data: dict) -> Optional[str]:
    dob_value = staff_data.get("date_of_birth")
    if dob_value:
        parsed = _locale_or_iso_to_iso_date(dob_value)
        if parsed is None:
            return f"Date of Birth must match locale format ({LOCALE_DATE_FORMAT}) or ISO format (YYYY-MM-DD)."
        staff_data["date_of_birth"] = parsed

    phone_pattern = re.compile(r"^\+?[0-9]{7,15}$")
    work_phone = staff_data.get("work_phone")
    if work_phone and not phone_pattern.match(work_phone):
        return "Work phone must contain only digits (optional leading +) and be 7-15 characters long."

    mobile_phone = staff_data.get("mobile_phone")
    if mobile_phone and not phone_pattern.match(mobile_phone):
        return "Mobile phone must contain only digits (optional leading +) and be 7-15 characters long."

    email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    work_email = staff_data.get("work_email")
    if work_email and not email_pattern.match(work_email):
        return "Work email must be a valid email address."

    return None


class CreateUserDialog(QDialog):
    def __init__(self, positions: List[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create User")
        self.payload: Optional[dict] = None

        layout = QGridLayout()

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.show_passwords_button = QPushButton("Show Passwords")
        self.show_passwords_button.setCheckable(True)
        self.show_passwords_button.toggled.connect(self._toggle_password_visibility)

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.date_of_birth = QLineEdit()
        self.date_of_birth.setPlaceholderText(LOCALE_DATE_FORMAT)
        self.work_phone = QLineEdit()
        self.mobile_phone = QLineEdit()
        self.work_email = QLineEdit()
        self.position = QComboBox()
        self.position.addItems(positions)

        layout.addWidget(QLabel("Username:"), 0, 0)
        layout.addWidget(self.username, 0, 1)
        layout.addWidget(QLabel("Password:"), 1, 0)
        layout.addWidget(self.password, 1, 1)
        layout.addWidget(QLabel("Confirm Password:"), 2, 0)
        layout.addWidget(self.confirm_password, 2, 1)
        layout.addWidget(self.show_passwords_button, 2, 2)
        layout.addWidget(QLabel("First Name:"), 3, 0)
        layout.addWidget(self.first_name, 3, 1)
        layout.addWidget(QLabel("Last Name:"), 4, 0)
        layout.addWidget(self.last_name, 4, 1)
        layout.addWidget(QLabel("DOB:"), 5, 0)
        layout.addWidget(self.date_of_birth, 5, 1)
        layout.addWidget(QLabel("Work Phone:"), 6, 0)
        layout.addWidget(self.work_phone, 6, 1)
        layout.addWidget(QLabel("Mobile Phone:"), 7, 0)
        layout.addWidget(self.mobile_phone, 7, 1)
        layout.addWidget(QLabel("Work Email:"), 8, 0)
        layout.addWidget(self.work_email, 8, 1)
        layout.addWidget(QLabel("Position:"), 9, 0)
        layout.addWidget(self.position, 9, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 10, 0, 1, 2)

        self.setLayout(layout)

    def _toggle_password_visibility(self, checked: bool) -> None:
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.password.setEchoMode(mode)
        self.confirm_password.setEchoMode(mode)
        self.show_passwords_button.setText("Hide Passwords" if checked else "Show Passwords")

    def _on_submit(self) -> None:
        username = self.username.text().strip()
        password = self.password.text().strip()
        confirm = self.confirm_password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Username and password are required.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return

        staff_data = {
            "first_name": self.first_name.text().strip() or None,
            "last_name": self.last_name.text().strip() or None,
            "date_of_birth": self.date_of_birth.text().strip() or None,
            "work_phone": self.work_phone.text().strip() or None,
            "mobile_phone": self.mobile_phone.text().strip() or None,
            "work_email": self.work_email.text().strip() or None,
            "position": self.position.currentText().strip() or None,
        }
        validation_error = validate_staff_data(staff_data)
        if validation_error:
            QMessageBox.warning(self, "Validation Error", validation_error)
            return

        self.payload = {
            "username": username,
            "password": password,
            "staff_data": staff_data,
        }
        self.accept()


class UpdateUserDialog(QDialog):
    def __init__(self, user: dict, positions: List[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Update User")
        self.payload: Optional[dict] = None

        layout = QGridLayout()

        self.username = QLineEdit(user.get("username", ""))
        self.password = QLineEdit()
        self.password.setPlaceholderText("Leave blank to keep current password")
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText("Repeat new password")
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.show_passwords_button = QPushButton("Show Passwords")
        self.show_passwords_button.setCheckable(True)
        self.show_passwords_button.toggled.connect(self._toggle_password_visibility)

        staff = user.get("staff") or {}
        self.first_name = QLineEdit(staff.get("first_name", ""))
        self.last_name = QLineEdit(staff.get("last_name", ""))
        self.date_of_birth = QLineEdit(_iso_date_to_locale_text(staff.get("date_of_birth", "")))
        self.date_of_birth.setPlaceholderText(LOCALE_DATE_FORMAT)
        self.work_phone = QLineEdit(staff.get("work_phone", ""))
        self.mobile_phone = QLineEdit(staff.get("mobile_phone", ""))
        self.work_email = QLineEdit(staff.get("work_email", ""))
        self.position = QComboBox()
        self.position.addItems(positions)
        current_position = (staff.get("position", "") or "").strip().lower()
        if current_position:
            index = self.position.findText(current_position)
            if index >= 0:
                self.position.setCurrentIndex(index)

        layout.addWidget(QLabel("Username:"), 0, 0)
        layout.addWidget(self.username, 0, 1)
        layout.addWidget(QLabel("New Password:"), 1, 0)
        layout.addWidget(self.password, 1, 1)
        layout.addWidget(QLabel("Confirm Password:"), 2, 0)
        layout.addWidget(self.confirm_password, 2, 1)
        layout.addWidget(self.show_passwords_button, 2, 2)
        layout.addWidget(QLabel("First Name:"), 3, 0)
        layout.addWidget(self.first_name, 3, 1)
        layout.addWidget(QLabel("Last Name:"), 4, 0)
        layout.addWidget(self.last_name, 4, 1)
        layout.addWidget(QLabel("DOB:"), 5, 0)
        layout.addWidget(self.date_of_birth, 5, 1)
        layout.addWidget(QLabel("Work Phone:"), 6, 0)
        layout.addWidget(self.work_phone, 6, 1)
        layout.addWidget(QLabel("Mobile Phone:"), 7, 0)
        layout.addWidget(self.mobile_phone, 7, 1)
        layout.addWidget(QLabel("Work Email:"), 8, 0)
        layout.addWidget(self.work_email, 8, 1)
        layout.addWidget(QLabel("Position:"), 9, 0)
        layout.addWidget(self.position, 9, 1)
        layout.addWidget(QLabel("Current password is not readable (stored securely)."), 10, 0, 1, 3)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Update")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 11, 0, 1, 2)

        self.setLayout(layout)

    def _toggle_password_visibility(self, checked: bool) -> None:
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.password.setEchoMode(mode)
        self.confirm_password.setEchoMode(mode)
        self.show_passwords_button.setText("Hide Passwords" if checked else "Show Passwords")

    def _on_submit(self) -> None:
        username = self.username.text().strip()
        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return

        password = self.password.text().strip()
        confirm_password = self.confirm_password.text().strip()
        if password or confirm_password:
            if not password:
                QMessageBox.warning(self, "Validation Error", "New password is required when confirmation is provided.")
                return
            if password != confirm_password:
                QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
                return

        staff_data = {
            "first_name": self.first_name.text().strip() or None,
            "last_name": self.last_name.text().strip() or None,
            "date_of_birth": self.date_of_birth.text().strip() or None,
            "work_phone": self.work_phone.text().strip() or None,
            "mobile_phone": self.mobile_phone.text().strip() or None,
            "work_email": self.work_email.text().strip() or None,
            "position": self.position.currentText().strip() or None,
        }
        validation_error = validate_staff_data(staff_data)
        if validation_error:
            QMessageBox.warning(self, "Validation Error", validation_error)
            return

        self.payload = {
            "username": username,
            "password": password,
            "staff_data": staff_data,
        }
        self.accept()


class DeleteUserDialog(QDialog):
    def __init__(self, user_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Delete User")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Delete this user?"))
        user_field = QLineEdit(user_text)
        user_field.setReadOnly(True)
        layout.addWidget(user_field)

        buttons = QHBoxLayout()
        delete_btn = QPushButton("Delete")
        cancel_btn = QPushButton("Cancel")
        delete_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(delete_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)


class SearchUsersDialog(QDialog):
    def __init__(self, positions: List[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Search Users")
        self.payload: Optional[dict] = None

        layout = QGridLayout()

        self.user_id = QLineEdit()
        self.username = QLineEdit()
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.date_of_birth = QLineEdit()
        self.date_of_birth.setPlaceholderText(LOCALE_DATE_FORMAT)
        self.work_phone = QLineEdit()
        self.mobile_phone = QLineEdit()
        self.work_email = QLineEdit()
        self.position = QComboBox()
        self.position.addItem("")
        self.position.addItems(positions)

        layout.addWidget(QLabel("User ID:"), 0, 0)
        layout.addWidget(self.user_id, 0, 1)
        layout.addWidget(QLabel("Username:"), 1, 0)
        layout.addWidget(self.username, 1, 1)
        layout.addWidget(QLabel("First Name:"), 2, 0)
        layout.addWidget(self.first_name, 2, 1)
        layout.addWidget(QLabel("Last Name:"), 3, 0)
        layout.addWidget(self.last_name, 3, 1)
        layout.addWidget(QLabel("DOB:"), 4, 0)
        layout.addWidget(self.date_of_birth, 4, 1)
        layout.addWidget(QLabel("Work Phone:"), 5, 0)
        layout.addWidget(self.work_phone, 5, 1)
        layout.addWidget(QLabel("Mobile Phone:"), 6, 0)
        layout.addWidget(self.mobile_phone, 6, 1)
        layout.addWidget(QLabel("Work Email:"), 7, 0)
        layout.addWidget(self.work_email, 7, 1)
        layout.addWidget(QLabel("Position:"), 8, 0)
        layout.addWidget(self.position, 8, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Search")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 9, 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        user_id = self.user_id.text().strip()
        if user_id and not user_id.isdigit():
            QMessageBox.warning(self, "Validation Error", "User ID must be numeric.")
            return

        dob_raw = self.date_of_birth.text().strip()
        if dob_raw:
            dob_iso = _locale_or_iso_to_iso_date(dob_raw)
            if dob_iso is None:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    f"DOB must match locale format ({LOCALE_DATE_FORMAT}) or ISO format (YYYY-MM-DD).",
                )
                return
        else:
            dob_iso = None

        self.payload = {
            "id": int(user_id) if user_id else None,
            "username": self.username.text().strip() or None,
            "first_name": self.first_name.text().strip() or None,
            "last_name": self.last_name.text().strip() or None,
            "date_of_birth": dob_iso,
            "work_phone": self.work_phone.text().strip() or None,
            "mobile_phone": self.mobile_phone.text().strip() or None,
            "work_email": self.work_email.text().strip() or None,
            "position": self.position.currentText().strip() or None,
        }
        self.accept()


class AdminWindow(QMainWindow):
    def __init__(self, api_client: ApiClient) -> None:
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Admin Panel - User Management")
        self.resize(700, 600)
        self.all_users: List[dict] = []
        self.users: List[dict] = []
        self.positions: List[str] = []
        self.selected_user_id: Optional[int] = None
        
        self._build_ui()
        self.refresh_users()
    
    def _build_ui(self) -> None:
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("User Management")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        top_controls_layout = QHBoxLayout()
        top_controls_layout.addStretch()
        create_button = QPushButton()
        create_icon = QIcon.fromTheme("list-add")
        if not create_icon.isNull():
            create_button.setIcon(create_icon)
        else:
            create_button.setText("+")
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        refresh_icon = QIcon.fromTheme("view-refresh")
        if not refresh_icon.isNull():
            refresh_button.setIcon(refresh_icon)
        else:
            refresh_button.setText("⟳")
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_users)
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_search_dialog)
        top_controls_layout.addWidget(create_button)
        top_controls_layout.addWidget(refresh_button)
        top_controls_layout.addWidget(filter_button)
        main_layout.addLayout(top_controls_layout)
        
        # Users list section
        list_label = QLabel("Existing Users:")
        main_layout.addWidget(list_label)

        users_header = QLabel("ID    Username            First Name      Last Name       Position")
        users_header_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        users_header_font.setBold(True)
        users_header.setFont(users_header_font)
        main_layout.addWidget(users_header)
        
        self.users_list = QListWidget()
        self.users_list.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.users_list.itemSelectionChanged.connect(self.on_user_selected)
        self.users_list.itemDoubleClicked.connect(lambda _item: self.open_update_dialog())
        self.users_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.users_list.customContextMenuRequested.connect(self._open_users_context_menu)
        main_layout.addWidget(self.users_list)
        
        # User action buttons
        user_actions_layout = QHBoxLayout()
        
        main_layout.addLayout(user_actions_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def refresh_users(self) -> None:
        try:
            self.positions = [row["position"] for row in self.api_client.list_positions()]
            self.all_users = self.api_client.list_users()
            self._render_users(self.all_users)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(exc)}")

    def _render_users(self, users: List[dict]) -> None:
        self.users = users
        self.users_list.clear()

        def fixed(value: str, width: int) -> str:
            text = (value or "-").strip()
            if len(text) > width:
                return f"{text[: width - 1]}…"
            return f"{text:<{width}}"

        for user in users:
            staff = user.get("staff") or {}
            first_name = staff.get("first_name") or "-"
            last_name = staff.get("last_name") or "-"
            position = staff.get("position") or "-"
            item_text = (
                f"{str(user.get('id', '-'))}  "
                f"{fixed(user.get('username', '-'), 18)} "
                f"{fixed(first_name, 14)} "
                f"{fixed(last_name, 14)} "
                f"{fixed(position, 12)}"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, user['id'])
            self.users_list.addItem(item)

    def _matches_filter(self, user: dict, criteria: dict) -> bool:
        staff = user.get("staff") or {}

        if criteria.get("id") is not None and user.get("id") != criteria["id"]:
            return False

        def contains(value: str, query: str) -> bool:
            return query.lower() in (value or "").lower()

        if criteria.get("username") and not contains(user.get("username", ""), criteria["username"]):
            return False
        if criteria.get("first_name") and not contains(staff.get("first_name", ""), criteria["first_name"]):
            return False
        if criteria.get("last_name") and not contains(staff.get("last_name", ""), criteria["last_name"]):
            return False
        if criteria.get("date_of_birth") and not contains(staff.get("date_of_birth", ""), criteria["date_of_birth"]):
            return False
        if criteria.get("work_phone") and not contains(staff.get("work_phone", ""), criteria["work_phone"]):
            return False
        if criteria.get("mobile_phone") and not contains(staff.get("mobile_phone", ""), criteria["mobile_phone"]):
            return False
        if criteria.get("work_email") and not contains(staff.get("work_email", ""), criteria["work_email"]):
            return False
        if criteria.get("position") and not contains(staff.get("position", ""), criteria["position"]):
            return False

        return True

    def open_search_dialog(self) -> None:
        dialog = SearchUsersDialog(self.positions, self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered_users = [
                user for user in self.all_users if self._matches_filter(user, dialog.payload)
            ]
            self._render_users(filtered_users)
    
    def on_user_selected(self) -> None:
        current_item = self.users_list.currentItem()
        if current_item:
            self.selected_user_id = current_item.data(Qt.ItemDataRole.UserRole)

    def _open_users_context_menu(self, pos) -> None:
        item = self.users_list.itemAt(pos)
        if item is None:
            return
        self.users_list.setCurrentItem(item)

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.users_list.mapToGlobal(pos))
        if selected_action == delete_action:
            self.open_delete_dialog()

    def _get_selected_user(self) -> tuple[int, str] | None:
        current_item = self.users_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a user first.")
            return None
        user_id = current_item.data(Qt.ItemDataRole.UserRole)
        return user_id, current_item.text()
    
    def open_create_dialog(self) -> None:
        if not self.positions:
            QMessageBox.warning(self, "Warning", "No positions available. Please check positions table.")
            return

        dialog = CreateUserDialog(self.positions, self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_user(
                    dialog.payload["username"],
                    dialog.payload["password"],
                    staff_data=dialog.payload["staff_data"],
                )
                QMessageBox.information(self, "Success", "User created successfully.")
                self.refresh_users()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", f"Error: {str(exc)}")

    def open_update_dialog(self) -> None:
        selected = self._get_selected_user()
        if not selected:
            return
        user_id, _ = selected

        try:
            user = self.api_client.get_user(user_id)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load user: {str(exc)}")
            return

        if not self.positions:
            QMessageBox.warning(self, "Warning", "No positions available. Please check positions table.")
            return

        dialog = UpdateUserDialog(user, self.positions, self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_user(
                    user_id,
                    username=dialog.payload["username"],
                    password=dialog.payload["password"],
                    staff_data=dialog.payload["staff_data"],
                )
                QMessageBox.information(self, "Success", "User updated successfully.")
                self.refresh_users()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", f"Error: {str(exc)}")

    def open_delete_dialog(self) -> None:
        selected = self._get_selected_user()
        if not selected:
            return
        user_id, user_text = selected

        dialog = DeleteUserDialog(user_text, self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.api_client.delete_user(user_id)
                QMessageBox.information(self, "Success", "User deleted successfully.")
                self.refresh_users()
            except Exception as exc:
                QMessageBox.critical(self, "Delete Failed", f"Error: {str(exc)}")

        