import re
from typing import List, Optional
from PyQt5.QtCore import Qt, QLocale, QDate
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apiclient import ApiClient
from patientwindow import FilterPatientsDialog, PatientDialog


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
        self.setWindowTitle("Admin Panel")
        self.resize(980, 680)
        self.all_users: List[dict] = []
        self.users: List[dict] = []
        self.positions: List[str] = []
        self.all_patients: List[dict] = []
        self.selected_user_id: Optional[int] = None
        self.selected_patient_id: Optional[int] = None

        self._build_ui()
        self.refresh_users()
        self.refresh_patients()
        self.refresh_assignment_data()

    def _build_ui(self) -> None:
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        tabs = QTabWidget()
        tabs.addTab(self._build_user_management_tab(), "User Management")
        tabs.addTab(self._build_patient_management_tab(), "Patient Management")
        tabs.addTab(self._build_patient_assignment_tab(), "Patient Assignment")
        main_layout.addWidget(tabs)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def _build_user_management_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        title_label = QLabel("User Management")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

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

        controls_layout.addWidget(create_button)
        controls_layout.addWidget(refresh_button)
        controls_layout.addWidget(filter_button)
        layout.addLayout(controls_layout)

        layout.addWidget(QLabel("Existing Users:"))

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "First Name", "Last Name", "Position"])
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.itemSelectionChanged.connect(self.on_user_selected)
        self.users_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        self.users_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.users_table.customContextMenuRequested.connect(self._open_users_context_menu)
        layout.addWidget(self.users_table)

        tab.setLayout(layout)
        return tab

    def _build_patient_management_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        title_label = QLabel("Patient Management")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        create_button = QPushButton()
        create_icon = QIcon.fromTheme("list-add")
        if not create_icon.isNull():
            create_button.setIcon(create_icon)
        else:
            create_button.setText("+")
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_patient_dialog)

        refresh_button = QPushButton()
        refresh_icon = QIcon.fromTheme("view-refresh")
        if not refresh_icon.isNull():
            refresh_button.setIcon(refresh_icon)
        else:
            refresh_button.setText("⟳")
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_patients)

        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_filter_patients_dialog)

        controls_layout.addWidget(create_button)
        controls_layout.addWidget(refresh_button)
        controls_layout.addWidget(filter_button)
        layout.addLayout(controls_layout)

        layout.addWidget(QLabel("Existing Patients:"))

        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(7)
        self.patients_table.setHorizontalHeaderLabels(
            ["ID", "First Name", "Last Name", "DOB", "Email", "Assigned to", "Position"]
        )
        self.patients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patients_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.patients_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.patients_table.verticalHeader().setVisible(False)
        self.patients_table.horizontalHeader().setStretchLastSection(True)
        self.patients_table.itemSelectionChanged.connect(self.on_patient_selected)
        self.patients_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_patient_dialog())
        self.patients_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.patients_table.customContextMenuRequested.connect(self._open_patients_context_menu)
        layout.addWidget(self.patients_table)

        tab.setLayout(layout)
        return tab

    def _build_patient_assignment_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        title_label = QLabel("Patient Assignment")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_assignment_data)
        assign_button = QPushButton("Assign Selected Patient")
        assign_button.clicked.connect(self.assign_selected_patient)
        controls_layout.addWidget(refresh_button)
        controls_layout.addWidget(assign_button)
        layout.addLayout(controls_layout)

        list_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Staff Users"))
        self.assignment_staff_table = QTableWidget()
        self.assignment_staff_table.setColumnCount(3)
        self.assignment_staff_table.setHorizontalHeaderLabels(["Staff ID", "Username", "Name"])
        self.assignment_staff_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assignment_staff_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.assignment_staff_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assignment_staff_table.verticalHeader().setVisible(False)
        self.assignment_staff_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.assignment_staff_table)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Patients"))
        self.assignment_patients_table = QTableWidget()
        self.assignment_patients_table.setColumnCount(4)
        self.assignment_patients_table.setHorizontalHeaderLabels(["Patient ID", "First Name", "Last Name", "Current Staff ID"])
        self.assignment_patients_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assignment_patients_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.assignment_patients_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assignment_patients_table.verticalHeader().setVisible(False)
        self.assignment_patients_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.assignment_patients_table)

        list_layout.addLayout(left_layout)
        list_layout.addLayout(right_layout)
        layout.addLayout(list_layout)

        tab.setLayout(layout)
        return tab

    def refresh_users(self) -> None:
        try:
            self.positions = [row["position"] for row in self.api_client.list_positions()]
            self.all_users = self.api_client.list_users()
            self._render_users(self.all_users)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(exc)}")

    def _render_users(self, users: List[dict]) -> None:
        self.users = users
        self.users_table.setRowCount(0)

        self.users_table.setRowCount(len(users))

        for row_index, user in enumerate(users):
            staff = user.get("staff") or {}
            first_name = staff.get("first_name") or "-"
            last_name = staff.get("last_name") or "-"
            position = staff.get("position") or "-"

            id_item = QTableWidgetItem(str(user.get("id", "-")))
            id_item.setData(Qt.ItemDataRole.UserRole, user["id"])
            username_item = QTableWidgetItem(user.get("username") or "-")
            first_name_item = QTableWidgetItem(first_name)
            last_name_item = QTableWidgetItem(last_name)
            position_item = QTableWidgetItem(position)

            self.users_table.setItem(row_index, 0, id_item)
            self.users_table.setItem(row_index, 1, username_item)
            self.users_table.setItem(row_index, 2, first_name_item)
            self.users_table.setItem(row_index, 3, last_name_item)
            self.users_table.setItem(row_index, 4, position_item)

        self.users_table.resizeColumnsToContents()

    def refresh_patients(self) -> None:
        try:
            self.all_patients = self.api_client.list_patients()
            self._render_patients(self.all_patients)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load patients: {str(exc)}")

    def _render_patients(self, patients: List[dict]) -> None:
        self.patients_table.setRowCount(len(patients))

        staff_name_by_id: dict[int, str] = {}
        staff_position_by_id: dict[int, str] = {}
        for user in self.all_users:
            staff = user.get("staff") or {}
            staff_id = staff.get("id")
            if staff_id is None:
                continue
            first_name = (staff.get("first_name") or "").strip()
            last_name = (staff.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            staff_name_by_id[int(staff_id)] = full_name or "-"
            staff_position_by_id[int(staff_id)] = (staff.get("position") or "-").strip() or "-"

        for row_index, patient in enumerate(patients):
            patient_id_item = QTableWidgetItem(str(patient.get("id", "-")))
            patient_id_item.setData(Qt.ItemDataRole.UserRole, patient.get("id"))
            self.patients_table.setItem(row_index, 0, patient_id_item)
            self.patients_table.setItem(row_index, 1, QTableWidgetItem(patient.get("first_name") or "-"))
            self.patients_table.setItem(row_index, 2, QTableWidgetItem(patient.get("last_name") or "-"))
            self.patients_table.setItem(
                row_index,
                3,
                QTableWidgetItem(_iso_date_to_locale_text(patient.get("date_of_birth") or "")),
            )
            self.patients_table.setItem(row_index, 4, QTableWidgetItem(patient.get("email") or "-"))
            patient_staff_id = patient.get("staff_id")
            assigned_to = "-"
            assigned_position = "-"
            if patient_staff_id is not None:
                assigned_to = staff_name_by_id.get(int(patient_staff_id), "-")
                assigned_position = staff_position_by_id.get(int(patient_staff_id), "-")
            self.patients_table.setItem(row_index, 5, QTableWidgetItem(assigned_to))
            self.patients_table.setItem(row_index, 6, QTableWidgetItem(assigned_position))

        self.patients_table.resizeColumnsToContents()

    def on_patient_selected(self) -> None:
        current_row = self.patients_table.currentRow()
        if current_row >= 0:
            id_item = self.patients_table.item(current_row, 0)
            if id_item is not None:
                patient_id = id_item.data(Qt.ItemDataRole.UserRole)
                if patient_id is not None:
                    self.selected_patient_id = int(patient_id)

    def _matches_patient_filter(self, patient: dict, criteria: dict) -> bool:
        def contains(value: str, query: str) -> bool:
            return query.lower() in (value or "").lower()

        if criteria.get("first_name") and not contains(patient.get("first_name", ""), criteria["first_name"]):
            return False
        if criteria.get("last_name") and not contains(patient.get("last_name", ""), criteria["last_name"]):
            return False
        if criteria.get("email") and not contains(patient.get("email", ""), criteria["email"]):
            return False
        if criteria.get("mobile_phone") and not contains(patient.get("mobile_phone", ""), criteria["mobile_phone"]):
            return False
        if criteria.get("address_city") and not contains(patient.get("address_city", ""), criteria["address_city"]):
            return False

        return True

    def open_filter_patients_dialog(self) -> None:
        dialog = FilterPatientsDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered_patients = [
                patient for patient in self.all_patients if self._matches_patient_filter(patient, dialog.payload)
            ]
            self._render_patients(filtered_patients)

    def _open_patients_context_menu(self, pos) -> None:
        item = self.patients_table.itemAt(pos)
        if item is None:
            return
        self.patients_table.selectRow(item.row())

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.patients_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.open_delete_patient_dialog()

    def _get_selected_patient(self) -> tuple[int, dict] | None:
        current_row = self.patients_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a patient first.")
            return None

        id_item = self.patients_table.item(current_row, 0)
        if id_item is None:
            QMessageBox.warning(self, "Warning", "Selected row has no patient ID.")
            return None

        patient_id = id_item.data(Qt.ItemDataRole.UserRole)
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected row has invalid patient ID.")
            return None

        patient = next((row for row in self.all_patients if row.get("id") == int(patient_id)), None)
        if patient is None:
            QMessageBox.warning(self, "Warning", "Selected patient is not available anymore.")
            return None

        return int(patient_id), patient

    def _resolve_default_staff_id(self) -> int | None:
        try:
            return self.api_client.get_current_staff_id()
        except Exception:
            pass

        for user in self.all_users:
            staff = user.get("staff") or {}
            staff_id = staff.get("id")
            if staff_id is not None:
                return int(staff_id)
        return None

    def open_create_patient_dialog(self) -> None:
        staff_id = self._resolve_default_staff_id()
        if staff_id is None:
            QMessageBox.warning(self, "Warning", "No staff record available to assign patient.")
            return

        dialog = PatientDialog("Create Patient", staff_id=staff_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_patient(dialog.payload)
                QMessageBox.information(self, "Success", "Patient created successfully.")
                self.refresh_patients()
                self.refresh_assignment_data()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", f"Error: {str(exc)}")

    def open_update_patient_dialog(self) -> None:
        selected = self._get_selected_patient()
        if not selected:
            return

        patient_id, patient = selected
        staff_id = patient.get("staff_id")
        if staff_id is None:
            staff_id = self._resolve_default_staff_id()
        if staff_id is None:
            QMessageBox.warning(self, "Warning", "No staff record available for patient update.")
            return

        dialog = PatientDialog("Update Patient", staff_id=int(staff_id), patient=patient, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_patient(patient_id, dialog.payload)
                QMessageBox.information(self, "Success", "Patient updated successfully.")
                self.refresh_patients()
                self.refresh_assignment_data()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", f"Error: {str(exc)}")

    def open_delete_patient_dialog(self) -> None:
        selected = self._get_selected_patient()
        if not selected:
            return

        patient_id, patient = selected
        patient_text = (
            f"ID: {patient.get('id', '-')} | Name: {patient.get('first_name', '-') } {patient.get('last_name', '-') }"
        )
        dialog = DeleteUserDialog(patient_text, self)
        dialog.setWindowTitle("Delete Patient")
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.api_client.delete_patient(patient_id)
                QMessageBox.information(self, "Success", "Patient deleted successfully.")
                self.refresh_patients()
                self.refresh_assignment_data()
            except Exception as exc:
                QMessageBox.critical(self, "Delete Failed", f"Error: {str(exc)}")

    def refresh_assignment_data(self) -> None:
        try:
            users = self.api_client.list_users()
            patients = self.api_client.list_patients()
            self.all_users = users
            self._render_assignment_staff(users)
            self._render_assignment_patients(patients)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load assignment data: {str(exc)}")

    def _render_assignment_staff(self, users: List[dict]) -> None:
        staff_users = [user for user in users if (user.get("staff") or {}).get("id") is not None]
        self.assignment_staff_table.setRowCount(len(staff_users))

        for row_index, user in enumerate(staff_users):
            staff = user.get("staff") or {}
            staff_id = staff.get("id")
            full_name = f"{staff.get('first_name', '')} {staff.get('last_name', '')}".strip() or "-"

            staff_id_item = QTableWidgetItem(str(staff_id))
            staff_id_item.setData(Qt.ItemDataRole.UserRole, staff_id)
            self.assignment_staff_table.setItem(row_index, 0, staff_id_item)
            self.assignment_staff_table.setItem(row_index, 1, QTableWidgetItem(user.get("username") or "-"))
            self.assignment_staff_table.setItem(row_index, 2, QTableWidgetItem(full_name))

        self.assignment_staff_table.resizeColumnsToContents()

    def _render_assignment_patients(self, patients: List[dict]) -> None:
        self.assignment_patients_table.setRowCount(len(patients))

        for row_index, patient in enumerate(patients):
            patient_id = patient.get("id")
            patient_id_item = QTableWidgetItem(str(patient_id))
            patient_id_item.setData(Qt.ItemDataRole.UserRole, patient_id)
            self.assignment_patients_table.setItem(row_index, 0, patient_id_item)
            self.assignment_patients_table.setItem(row_index, 1, QTableWidgetItem(patient.get("first_name") or "-"))
            self.assignment_patients_table.setItem(row_index, 2, QTableWidgetItem(patient.get("last_name") or "-"))
            self.assignment_patients_table.setItem(row_index, 3, QTableWidgetItem(str(patient.get("staff_id", "-"))))

        self.assignment_patients_table.resizeColumnsToContents()

    def assign_selected_patient(self) -> None:
        staff_row = self.assignment_staff_table.currentRow()
        patient_row = self.assignment_patients_table.currentRow()

        if staff_row < 0 or patient_row < 0:
            QMessageBox.warning(self, "Warning", "Select one staff user and one patient first.")
            return

        staff_item = self.assignment_staff_table.item(staff_row, 0)
        patient_item = self.assignment_patients_table.item(patient_row, 0)
        if staff_item is None or patient_item is None:
            QMessageBox.warning(self, "Warning", "Invalid selection.")
            return

        staff_id = staff_item.data(Qt.ItemDataRole.UserRole)
        patient_id = patient_item.data(Qt.ItemDataRole.UserRole)
        if staff_id is None or patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected row is missing identifiers.")
            return

        try:
            self.api_client.update_patient(int(patient_id), {"staff_id": int(staff_id)})
            QMessageBox.information(self, "Success", "Patient assigned successfully.")
            self.refresh_patients()
            self.refresh_assignment_data()
        except Exception as exc:
            QMessageBox.critical(self, "Assignment Failed", f"Error: {str(exc)}")

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
        current_row = self.users_table.currentRow()
        if current_row >= 0:
            id_item = self.users_table.item(current_row, 0)
            if id_item is not None:
                self.selected_user_id = id_item.data(Qt.ItemDataRole.UserRole)

    def _open_users_context_menu(self, pos) -> None:
        item = self.users_table.itemAt(pos)
        if item is None:
            return
        self.users_table.selectRow(item.row())

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.users_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.open_delete_dialog()

    def _get_selected_user(self) -> tuple[int, str] | None:
        current_row = self.users_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user first.")
            return None

        id_item = self.users_table.item(current_row, 0)
        username_item = self.users_table.item(current_row, 1)
        first_name_item = self.users_table.item(current_row, 2)
        last_name_item = self.users_table.item(current_row, 3)
        position_item = self.users_table.item(current_row, 4)

        if id_item is None:
            QMessageBox.warning(self, "Warning", "Selected row has no user ID.")
            return None

        user_id = id_item.data(Qt.ItemDataRole.UserRole)
        user_text = (
            f"ID: {id_item.text()} | Username: {username_item.text() if username_item else '-'} | "
            f"Name: {(first_name_item.text() if first_name_item else '-')} "
            f"{(last_name_item.text() if last_name_item else '-')} | "
            f"Position: {position_item.text() if position_item else '-'}"
        )
        return user_id, user_text
    
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

