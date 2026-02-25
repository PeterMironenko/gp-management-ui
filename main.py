import sys
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apiclient import ApiClient
from adminwindow import AdminWindow
from staffdashboardwindow import StaffDashboardWindow
from config import ConfigManager

class LoginDialog(QDialog):
    def __init__(self, api_client: ApiClient, config_manager: ConfigManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.config_manager = config_manager
        self.setWindowTitle("Login")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout()

        self.url_edit = QLineEdit(self.api_client.base_url)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.handle_login)

        register_button = QPushButton("Register")
        register_button.clicked.connect(self.open_register_dialog)

        layout.addWidget(QLabel("URL:"), 0, 0)
        layout.addWidget(self.url_edit, 0, 1)

        layout.addWidget(QLabel("Username:"), 1, 0)
        layout.addWidget(self.username_edit, 1, 1)
        layout.addWidget(QLabel("Password:"), 2, 0)
        layout.addWidget(self.password_edit, 2, 1)

        button_row = QHBoxLayout()
        button_row.addWidget(login_button)
        button_row.addWidget(register_button)
        layout.addLayout(button_row, 3, 0, 1, 2)

        self.setLayout(layout)

    def handle_login(self) -> None:
        url = self.url_edit.text().strip()
        self.api_client.base_url = url
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password are required.")
            return
        try:
            self.api_client.login(username, password)
            # Save the API URL to config after successful login
            self.config_manager.set_api_url(url)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Login failed", str(exc))
            return
        self.accept()

    def open_register_dialog(self) -> None:
        dialog = RegisterDialog(self.api_client, self)
        if dialog.exec_() == QDialog.Accepted:
            # After successful registration, pre-fill username for convenience
            self.username_edit.setText(dialog.username())
            self.password_edit.setFocus()


class RegisterDialog(QDialog):
    """Dialog used to register a new user via the API."""

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self._username: str = ""
        self.setWindowTitle("Register User")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout()

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_confirm_edit = QLineEdit()
        self.password_confirm_edit.setEchoMode(QLineEdit.Password)

        layout.addWidget(QLabel("Username:"), 0, 0)
        layout.addWidget(self.username_edit, 0, 1)
        layout.addWidget(QLabel("Password:"), 1, 0)
        layout.addWidget(self.password_edit, 1, 1)
        layout.addWidget(QLabel("Confirm Password:"), 2, 0)
        layout.addWidget(self.password_confirm_edit, 2, 1)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Register")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.on_register_clicked)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def on_register_clicked(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        password_confirm = self.password_confirm_edit.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password are required.")
            return

        if password != password_confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        try:
            self.api_client.register(username, password)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Registration failed", str(exc))
            return

        self._username = username
        QMessageBox.information(self, "Success", "User registered successfully.")
        self.accept()

    def username(self) -> str:
        return self._username


def main() -> None:
    app = QApplication(sys.argv)

    # Load configuration
    config_manager = ConfigManager()
    api_url = config_manager.get_api_url()

    api_client = ApiClient(api_url)

    login_dialog = LoginDialog(api_client, config_manager)
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0)

    if api_client.is_admin:
        window = AdminWindow(api_client)
    else:
        window = StaffDashboardWindow(api_client)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
