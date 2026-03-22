"""UI → DB tests for AdminWindow – User Management tab.

Tests drive the real AdminWindow widget, monkeypatching only the dialog
classes so exec_() returns Accepted instantly with a pre-set payload.
The live Flask server (session-scoped) persists across all tests; each
test is responsible for cleaning up its own DB rows.
"""

import sys
import os
from uuid import uuid4

import pytest
from PyQt5.QtWidgets import QDialog

_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

import adminwindow as _aw_mod


# ---------------------------------------------------------------------------
# Dialog stub factories
# ---------------------------------------------------------------------------

def _create_stub(payload: dict):
    """Return a CreateUserDialog replacement that immediately accepts."""
    class _Stub:
        def __init__(self, positions, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _update_stub(payload: dict):
    """Return an UpdateUserDialog replacement that immediately accepts."""
    class _Stub:
        def __init__(self, user, positions, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _delete_stub():
    """Return a DeleteUserDialog replacement that immediately confirms deletion."""
    class _Stub:
        def __init__(self, user_text, parent=None):
            self.payload = None

        def exec_(self):
            return QDialog.Accepted

    return _Stub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_STAFF = {
    "first_name": "Test",
    "last_name": "UIUser",
    "date_of_birth": "1985-06-15",
    "work_phone": "01234567890",
    "mobile_phone": "07777000001",
    "work_email": "test.uiuser@clinic.test",
    "position": "nurse",
}


def _unique_staff_data(prefix: str) -> dict:
    """Return staff payload with unique phone/email fields to avoid uniqueness clashes."""
    token = uuid4().hex[:8]
    # Keep lengths within model limits while staying numeric for phone fields.
    phone_tail = str(int(token, 16) % 10_000_000).zfill(7)
    return {
        **_VALID_STAFF,
        "work_phone": f"0208{phone_tail}",
        "mobile_phone": f"07{phone_tail}1",
        "work_email": f"{prefix}.{token}@clinic.test",
    }


def _user_id_by_username(api_client, username: str) -> int:
    """Lookup a user's id by username via API list_users()."""
    users = api_client.list_users()
    for user in users:
        if user.get("username") == username:
            return int(user["id"])
    raise AssertionError(f"User '{username}' was not returned by list_users().")


def _find_row(table, col: int, text: str) -> int:
    """Return the row index of the first cell in *col* that contains *text*, or -1."""
    for row in range(table.rowCount()):
        item = table.item(row, col)
        if item and item.text() == text:
            return row
    return -1


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateUser:
    """open_create_dialog() → api_client.create_user() → users table in DB."""

    def test_create_user_appears_in_db(self, admin_window, db_conn, monkeypatch):
        username = "ui_create_user_test"
        payload = {
            "username": username,
            "password": "Secure1234!",
            "staff_data": _unique_staff_data("create"),
        }

        monkeypatch.setattr(_aw_mod, "CreateUserDialog", _create_stub(payload))
        admin_window.open_create_dialog()

        row = db_conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        assert row is not None, "Created user must appear in the database"

        # cleanup
        admin_window.api_client.delete_user(row["id"])

    def test_created_user_visible_in_table(self, admin_window, db_conn, monkeypatch):
        username = "ui_table_visibility_test"
        payload = {
            "username": username,
            "password": "Secure1234!",
            "staff_data": _unique_staff_data("visible"),
        }

        monkeypatch.setattr(_aw_mod, "CreateUserDialog", _create_stub(payload))
        admin_window.open_create_dialog()

        row_idx = _find_row(admin_window.users_table, 1, username)
        assert row_idx >= 0, "Created user must appear in the users_table widget"

        db_row = db_conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if db_row:
            admin_window.api_client.delete_user(db_row["id"])


class TestUpdateUser:
    """Select a row → open_update_dialog() → api_client.update_user() → DB."""

    def test_update_username_persists_to_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        original_name = "ui_before_update"
        updated_name = "ui_after_update"

        created = admin_api_client.create_user(
            original_name,
            "Secure1234!",
            staff_data=_unique_staff_data("before"),
        )
        user_id = _user_id_by_username(admin_api_client, original_name)

        try:
            admin_window.refresh_users()
            row_idx = _find_row(admin_window.users_table, 1, original_name)
            assert row_idx >= 0, "User must be visible in the table before update"
            admin_window.users_table.selectRow(row_idx)

            updated_payload = {
                "username": updated_name,
                "password": "",  # keep existing
                "staff_data": _unique_staff_data("after"),
            }
            monkeypatch.setattr(_aw_mod, "UpdateUserDialog", _update_stub(updated_payload))
            admin_window.open_update_dialog()

            db_row = db_conn.execute(
                "SELECT username FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            assert db_row is not None
            assert db_row["username"] == updated_name, (
                f"DB username should be '{updated_name}', got '{db_row['username']}'"
            )
        finally:
            admin_api_client.delete_user(user_id)


class TestDeleteUser:
    """Select a row → open_delete_dialog() → api_client.delete_user() → row gone from DB."""

    def test_delete_user_removes_from_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        username = "ui_delete_me"

        created = admin_api_client.create_user(
            username,
            "Secure1234!",
            staff_data=_unique_staff_data("deleteme"),
        )
        user_id = _user_id_by_username(admin_api_client, username)

        admin_window.refresh_users()
        row_idx = _find_row(admin_window.users_table, 1, username)
        assert row_idx >= 0, "User must be visible in the table before deletion"
        admin_window.users_table.selectRow(row_idx)

        monkeypatch.setattr(_aw_mod, "DeleteUserDialog", _delete_stub())
        admin_window.open_delete_dialog()

        db_row = db_conn.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        assert db_row is None, "Deleted user must not exist in the database"

    def test_delete_user_removed_from_table(self, admin_window, db_conn, monkeypatch, admin_api_client):
        username = "ui_delete_table_check"

        created = admin_api_client.create_user(
            username,
            "Secure1234!",
            staff_data=_unique_staff_data("deltable"),
        )
        user_id = _user_id_by_username(admin_api_client, username)

        try:
            admin_window.refresh_users()
            row_idx = _find_row(admin_window.users_table, 1, username)
            assert row_idx >= 0
            admin_window.users_table.selectRow(row_idx)

            monkeypatch.setattr(_aw_mod, "DeleteUserDialog", _delete_stub())
            admin_window.open_delete_dialog()

            row_after = _find_row(admin_window.users_table, 1, username)
            assert row_after < 0, "Deleted user must not appear in the users_table after deletion"
        except Exception:
            # Best-effort cleanup if test fails before deletion
            try:
                admin_api_client.delete_user(user_id)
            except Exception:
                pass
            raise


class TestDialogValidation:
    """Stand-alone dialog validation: invalid input → payload remains None."""

    def test_create_dialog_empty_username_gives_no_payload(self, qapp):
        dialog = _aw_mod.CreateUserDialog(["nurse"])
        dialog.username.setText("")
        dialog.password.setText("Secure1234!")
        dialog.confirm_password.setText("Secure1234!")
        dialog._on_submit()
        assert dialog.payload is None, "Empty username must not produce a payload"

    def test_create_dialog_password_mismatch_gives_no_payload(self, qapp):
        dialog = _aw_mod.CreateUserDialog(["nurse"])
        dialog.username.setText("someuser")
        dialog.password.setText("Password1!")
        dialog.confirm_password.setText("DifferentPass!")
        dialog._on_submit()
        assert dialog.payload is None, "Password mismatch must not produce a payload"

    def test_create_dialog_valid_input_produces_payload(self, qapp):
        dialog = _aw_mod.CreateUserDialog(["nurse"])
        dialog.username.setText("validuser")
        dialog.password.setText("Secure1234!")
        dialog.confirm_password.setText("Secure1234!")
        dialog.first_name.setText("Valid")
        dialog.last_name.setText("User")
        dialog.date_of_birth.setText("15/06/1985")
        dialog.work_phone.setText("01234567890")
        dialog.mobile_phone.setText("07777000001")
        dialog.work_email.setText("valid@clinic.test")
        dialog._on_submit()
        assert dialog.payload is not None, "All required fields filled → payload must be set"
        assert dialog.payload["username"] == "validuser"
