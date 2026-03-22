"""Shared fixtures for gp-management-ui UI-to-database end-to-end tests.

Architecture
------------
* A real Flask backend is started once per test session in a background thread,
  backed by a temporary SQLite file. The server stays up for all tests.
* An admin ApiClient and a staff ApiClient are created once per session.
* Each window fixture is function-scoped so every test gets a fresh window
  (which re-fetches data from the live server).
* A ``db_conn`` fixture gives tests a direct SQLite connection for low-level
  DB assertions after UI actions.
* A ``suppress_msgbox`` autouse fixture replaces all QMessageBox static
  methods with no-ops so that informational/error dialogs do not block the
  test event loop.

Running
-------
  cd gp-management-ui
  QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
"""

import os
import socket
import sqlite3
import sys
import threading
import time
from datetime import date

import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox

# ---------------------------------------------------------------------------
# Ensure both repos are on sys.path
# ---------------------------------------------------------------------------
_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
_BACKEND_DIR = os.path.abspath(os.path.join(_TESTS_DIR, "..", "..", "gp-management"))

for _p in (_UI_DIR, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 15.0) -> None:
    """Poll until the server responds or timeout expires."""
    import requests as _req

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            _req.get(url, timeout=0.5)
            return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError(f"Test server at {url} did not start within {timeout}s")


# ---------------------------------------------------------------------------
# Session-scoped live Flask server
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def live_server():
    """Start a real Flask server in a background thread.

    Pre-seeds:
      * 4 staff positions
      * Admin user   (user id 1 → is_admin=True)  + linked staff record
      * Staff user   (user id 2 → is_admin=False) + linked staff record

    Yields a dict with server URL, db_path, and Flask app/db references.
    """
    # Deferred imports so sys.path is populated before loading backend modules
    from app import app as _flask_app, db as _db
    from blocklist import BLOCKLIST
    from passlib.hash import pbkdf2_sha256
    from models.user import UserModel
    from models.staff import StaffModel
    from models.position import PositionModel

    port = _free_port()
    # Keep the same DB engine that app.py initialized to avoid Flask-SQLAlchemy
    # engine cache pitfalls, and reset it to a clean schema for the test session.
    _flask_app.config["TESTING"] = True

    with _flask_app.app_context():
        active_db_path = _db.engine.url.database
        _db.drop_all()
        _db.create_all()
        BLOCKLIST.clear()

        # Seed positions
        for pos_name in ("doctor", "nurse", "receptionist", "pharmacist"):
            if not PositionModel.query.filter_by(position=pos_name).first():
                _db.session.add(PositionModel(position=pos_name))
        _db.session.commit()

        # Admin user — MUST be user id 1 (app.py checks int(identity)==1)
        admin = UserModel(
            username="uitestadmin",
            password=pbkdf2_sha256.hash("Admin1234!"),
        )
        _db.session.add(admin)
        _db.session.commit()
        _db.session.add(
            StaffModel(
                user_id=admin.id,
                first_name="Admin",
                last_name="Tester",
                date_of_birth=date(1980, 1, 1),
                work_phone="02070000001",
                mobile_phone="07000000001",
                work_email="uitestadmin@clinic.test",
                position="doctor",
            )
        )
        _db.session.commit()

        # Regular staff user
        staff_user = UserModel(
            username="uiteststaff",
            password=pbkdf2_sha256.hash("Staff1234!"),
        )
        _db.session.add(staff_user)
        _db.session.commit()
        _db.session.add(
            StaffModel(
                user_id=staff_user.id,
                first_name="Staff",
                last_name="Tester",
                date_of_birth=date(1985, 2, 2),
                work_phone="02070000002",
                mobile_phone="07000000002",
                work_email="uiteststaff@clinic.test",
                position="nurse",
            )
        )
        _db.session.commit()

    # Start werkzeug server in a daemon thread
    from werkzeug.serving import make_server as _make_server

    _wsgi_server = _make_server("127.0.0.1", port, _flask_app)
    _thread = threading.Thread(target=_wsgi_server.serve_forever, daemon=True)
    _thread.start()

    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(f"{base_url}/position")

    yield {
        "url": base_url,
        # Use the actual engine database path so raw sqlite assertions hit the same DB.
        "db_path": active_db_path,
        "flask_app": _flask_app,
        "db": _db,
    }

    _wsgi_server.shutdown()
    # No file deletion here: this DB file is managed by the backend app config.


# ---------------------------------------------------------------------------
# API client fixtures (session-scoped, authenticated)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def admin_api_client(live_server):
    """ApiClient authenticated as admin (user id 1, is_admin=True)."""
    from apiclient import ApiClient

    client = ApiClient(live_server["url"])
    client.login("uitestadmin", "Admin1234!")
    assert client.is_admin, "Admin client must have is_admin=True"
    return client


@pytest.fixture(scope="session")
def staff_api_client(live_server):
    """ApiClient authenticated as a regular staff user (is_admin=False)."""
    from apiclient import ApiClient

    client = ApiClient(live_server["url"])
    client.login("uiteststaff", "Staff1234!")
    assert not client.is_admin, "Staff client must have is_admin=False"
    return client


# ---------------------------------------------------------------------------
# Direct DB connection for SQL-level assertions
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_conn(live_server):
    """SQLite3 connection for direct DB verification in tests."""
    conn = sqlite3.connect(live_server["db_path"])
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# QMessageBox suppressor (autouse so every test benefits automatically)
# ---------------------------------------------------------------------------

class _SilentMsgBox:
    """Drop-in QMessageBox replacement that swallows all static calls."""

    Ok = QMessageBox.Ok
    Yes = QMessageBox.Yes
    No = QMessageBox.No

    @staticmethod
    def information(*_args, **_kwargs):
        return QMessageBox.Ok

    @staticmethod
    def critical(*_args, **_kwargs):
        return QMessageBox.Ok

    @staticmethod
    def warning(*_args, **_kwargs):
        return QMessageBox.Ok

    @staticmethod
    def question(*_args, **_kwargs):
        return QMessageBox.Yes


@pytest.fixture(autouse=True)
def suppress_msgbox(monkeypatch):
    """Replace QMessageBox with a silent stub in all UI modules."""
    import importlib
    for module_name in ("adminwindow", "staffdashboardwindow", "patientwindow", "main"):
        # Force-import if not yet loaded so the patch sticks
        try:
            mod = sys.modules.get(module_name) or importlib.import_module(module_name)
            monkeypatch.setattr(mod, "QMessageBox", _SilentMsgBox)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Window fixtures (function-scoped → fresh window per test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_window(qtbot, admin_api_client):
    """AdminWindow backed by the live server, registered with qtbot."""
    from adminwindow import AdminWindow

    win = AdminWindow(admin_api_client)
    qtbot.addWidget(win)
    return win


@pytest.fixture()
def staff_window(qtbot, staff_api_client):
    """StaffDashboardWindow backed by the live server, registered with qtbot."""
    from staffdashboardwindow import StaffDashboardWindow

    win = StaffDashboardWindow(staff_api_client)
    qtbot.addWidget(win)
    return win


# ---------------------------------------------------------------------------
# Window fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_window(qtbot, admin_api_client):
    """A live AdminWindow backed by the running test server."""
    # QApplication is managed automatically by pytest-qt's qtbot fixture
    from adminwindow import AdminWindow

    win = AdminWindow(admin_api_client)
    qtbot.addWidget(win)
    yield win
    win.close()


@pytest.fixture()
def staff_window(qtbot, staff_api_client):
    """A live StaffDashboardWindow backed by the running test server."""
    from staffdashboardwindow import StaffDashboardWindow

    win = StaffDashboardWindow(staff_api_client)
    qtbot.addWidget(win)
    yield win
    win.close()
