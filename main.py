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

        layout.addWidget(QLabel("URL:"), 0, 0)
        layout.addWidget(self.url_edit, 0, 1)

        layout.addWidget(QLabel("Username:"), 1, 0)
        layout.addWidget(self.username_edit, 1, 1)
        layout.addWidget(QLabel("Password:"), 2, 0)
        layout.addWidget(self.password_edit, 2, 1)

        button_row = QHBoxLayout()
        button_row.addWidget(login_button)
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
