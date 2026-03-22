"""UI → DB tests for LoginDialog.

Covers:
  - Successful admin login → is_admin=True, window routed to AdminWindow
  - Successful staff login → is_admin=False, window routed to StaffDashboardWindow
  - Empty credentials → warning shown, no token acquired
  - Wrong password → error shown, no token acquired
"""

import sys
import os

import pytest
from PyQt5.QtWidgets import QDialog

_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

from apiclient import ApiClient
from config import ConfigManager
from main import LoginDialog


# ---------------------------------------------------------------------------
# Minimal ConfigManager stub (avoids reading/writing the real config file)
# ---------------------------------------------------------------------------

class _StubConfigManager:
    def get_api_url(self) -> str:
        return ""

    def set_api_url(self, url: str) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoginDialog:
    """LoginDialog fills username/password → calls api_client.login()."""

    def test_admin_login_sets_is_admin_true(self, qtbot, live_server):
        """Valid admin credentials → is_admin=True, access_token populated."""
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        dlg.url_edit.setText(live_server["url"])
        dlg.username_edit.setText("uitestadmin")
        dlg.password_edit.setText("Admin1234!")

        dlg.handle_login()

        assert client.access_token, "Access token must be populated after login"
        assert client.is_admin is True

    def test_staff_login_sets_is_admin_false(self, qtbot, live_server):
        """Valid staff credentials → is_admin=False."""
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        dlg.url_edit.setText(live_server["url"])
        dlg.username_edit.setText("uiteststaff")
        dlg.password_edit.setText("Staff1234!")

        dlg.handle_login()

        assert client.access_token
        assert client.is_admin is False

    def test_empty_credentials_shows_warning_no_token(self, qtbot, live_server):
        """Empty username/password → warning shown, no token acquired."""
        warnings_shown = []
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        # Capture QMessageBox.warning calls inside main module
        import main as _main_mod
        original = getattr(_main_mod, "QMessageBox", None)

        class _Cap:
            @staticmethod
            def warning(*args, **kwargs):
                warnings_shown.append(args)
                return 0
            @staticmethod
            def critical(*args, **kwargs):
                return 0

        if original is not None:
            _main_mod.QMessageBox = _Cap

        try:
            dlg.url_edit.setText(live_server["url"])
            dlg.username_edit.setText("")
            dlg.password_edit.setText("")
            dlg.handle_login()
        finally:
            if original is not None:
                _main_mod.QMessageBox = original

        assert not client.access_token, "No token should be issued for empty credentials"
        assert warnings_shown, "A warning dialog should have been shown"

    def test_wrong_password_shows_error_no_token(self, qtbot, live_server):
        """Wrong password → error dialog shown, no token acquired."""
        errors_shown = []
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        import main as _main_mod
        original = getattr(_main_mod, "QMessageBox", None)

        class _Cap:
            @staticmethod
            def warning(*args, **kwargs):
                return 0
            @staticmethod
            def critical(*args, **kwargs):
                errors_shown.append(args)
                return 0

        if original is not None:
            _main_mod.QMessageBox = _Cap

        try:
            dlg.url_edit.setText(live_server["url"])
            dlg.username_edit.setText("uitestadmin")
            dlg.password_edit.setText("WrongPassword!")
            dlg.handle_login()
        finally:
            if original is not None:
                _main_mod.QMessageBox = original

        assert not client.access_token, "No token should be issued for wrong password"
        assert errors_shown, "An error dialog should have been shown"

    def test_admin_login_routes_to_admin_window(self, qtbot, live_server):
        """After successful admin login, is_admin is True (AdminWindow would open)."""
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        dlg.url_edit.setText(live_server["url"])
        dlg.username_edit.setText("uitestadmin")
        dlg.password_edit.setText("Admin1234!")
        dlg.handle_login()

        # The main() function checks is_admin to choose the window class.
        assert client.is_admin is True

    def test_staff_login_routes_to_staff_window(self, qtbot, live_server):
        """After successful staff login, is_admin is False (StaffDashboardWindow would open)."""
        client = ApiClient(live_server["url"])
        dlg = LoginDialog(client, _StubConfigManager())
        qtbot.addWidget(dlg)

        dlg.url_edit.setText(live_server["url"])
        dlg.username_edit.setText("uiteststaff")
        dlg.password_edit.setText("Staff1234!")
        dlg.handle_login()

        assert client.is_admin is False
