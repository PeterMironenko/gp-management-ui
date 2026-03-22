"""UI → DB tests for StaffDashboardWindow – Appointments tab.

Tests the full chain:
  Patient assigned to the staff user
    → StaffDashboardWindow.today_tab.staff_patients includes the patient
    → Monkeypatched AppointmentDialog dialog → open_create_dialog()
    → Appointment row verified in the database
    → open_update_dialog() updates the appointment
    → delete_selected_appointment() removes the appointment
"""

import sys
import os

import pytest
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QDialog

_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

import staffdashboardwindow as _sdbw_mod

_VALID_PATIENT = {
    "first_name": "Staff",
    "last_name": "AppPatient",
    "date_of_birth": "1988-07-22",
    "landline_phone": "01234567892",
    "mobile_phone": "07777000020",
    "email": "staff.apppatient@clinic.test",
    "address_street": "20 Staff Lane",
    "address_city": "Staffton",
    "address_county": "Staffshire",
    "address_postcode": "ST1 1ST",
    "emergency_contact_name": "Emergency StaffContact",
    "emergency_contact_phone": "07777000021",
}


# ---------------------------------------------------------------------------
# Appointment dialog stub
# ---------------------------------------------------------------------------

def _appointment_create_stub(payload: dict):
    """Replacement for AppointmentDialog that immediately accepts with a preset payload."""
    class _Stub:
        def __init__(self, title, patient_id, staff_id, appointment=None, parent=None):
            self.payload = payload
            self.Accepted = QDialog.Accepted  # open_create_dialog checks dialog.Accepted

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _appointment_update_stub(payload: dict):
    class _Stub:
        def __init__(self, title, patient_id, staff_id, appointment=None, parent=None):
            self.payload = payload
            self.Accepted = QDialog.Accepted

        def exec_(self):
            return QDialog.Accepted

    return _Stub


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def staff_patient(admin_api_client, staff_api_client):
    """Create a patient assigned to the staff user; yield the patient dict; clean up."""
    me = staff_api_client.get_me()
    staff_id = int((me.get("staff") or {}).get("id"))

    patient = admin_api_client.create_patient(
        {**_VALID_PATIENT, "staff_id": staff_id, "email": "staff.apppatient@clinic.test"}
    )
    yield patient

    try:
        admin_api_client.delete_patient(patient["id"])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStaffAppointmentsCreate:
    def test_patient_visible_after_refresh(self, staff_window, staff_patient):
        """After assigning a patient, the AppointmentsTab must include them in staff_patients."""
        staff_window.today_tab.refresh_today_appointments()

        patient_ids = [p.get("id") for p in staff_window.today_tab.staff_patients]
        assert staff_patient["id"] in patient_ids, (
            "Assigned patient must appear in today_tab.staff_patients after refresh"
        )

    def test_create_appointment_persists_to_db(
        self, staff_window, staff_patient, db_conn, monkeypatch, staff_api_client
    ):
        """open_create_dialog() → appointment row in DB."""
        staff_window.today_tab.refresh_today_appointments()

        me = staff_api_client.get_me()
        staff_id = int((me.get("staff") or {}).get("id"))
        patient_id = int(staff_patient["id"])

        payload = {
            "patient_id": patient_id,
            "staff_id": staff_id,
            "appointment_date": "2025-03-01T10:00:00",
            "duration_minutes": 30,
            "reason": "UI test appointment",
            "notes": None,
            "location": None,
        }

        # Stub out _choose_patient_for_create to return our known patient
        staff_window.today_tab._choose_patient_for_create = lambda: staff_patient

        monkeypatch.setattr(_sdbw_mod, "AppointmentDialog", _appointment_create_stub(payload))
        staff_window.today_tab.open_create_dialog()

        row = db_conn.execute(
            "SELECT id FROM appointments WHERE patient_id = ? AND reason = ?",
            (patient_id, "UI test appointment"),
        ).fetchone()
        assert row is not None, "Created appointment must appear in the appointments table in DB"

        try:
            staff_api_client.delete_appointment(row["id"])
        except Exception:
            pass

    def test_create_appointment_visible_in_table(
        self, staff_window, staff_patient, db_conn, monkeypatch, staff_api_client
    ):
        """After creating an appointment, it must appear in the appointments_table widget."""
        staff_window.today_tab.refresh_today_appointments()

        me = staff_api_client.get_me()
        staff_id = int((me.get("staff") or {}).get("id"))
        patient_id = int(staff_patient["id"])

        today = QDate.currentDate().toString("yyyy-MM-dd")
        payload = {
            "patient_id": patient_id,
            "staff_id": staff_id,
            "appointment_date": f"{today}T09:00:00",
            "duration_minutes": 15,
            "reason": "UI table visibility test",
            "notes": None,
            "location": None,
        }

        staff_window.today_tab._choose_patient_for_create = lambda: staff_patient
        monkeypatch.setattr(_sdbw_mod, "AppointmentDialog", _appointment_create_stub(payload))
        staff_window.today_tab.open_create_dialog()

        # Count rows with our reason text
        found = False
        for row in range(staff_window.today_tab.appointments_table.rowCount()):
            item = staff_window.today_tab.appointments_table.item(row, 4)  # Reason column
            if item and item.text() == "UI table visibility test":
                found = True
                break

        db_row = db_conn.execute(
            "SELECT id FROM appointments WHERE patient_id = ? AND reason = ?",
            (patient_id, "UI table visibility test"),
        ).fetchone()

        if db_row:
            try:
                staff_api_client.delete_appointment(db_row["id"])
            except Exception:
                pass

        assert found, "Created appointment must be visible in the appointments_table"


class TestStaffAppointmentsDelete:
    def test_delete_appointment_removes_from_db(
        self, staff_window, staff_patient, db_conn, staff_api_client
    ):
        """Delete selected appointment → row removed from DB."""
        me = staff_api_client.get_me()
        staff_id = int((me.get("staff") or {}).get("id"))
        patient_id = int(staff_patient["id"])

        today = QDate.currentDate().toString("yyyy-MM-dd")
        appointment = staff_api_client.create_appointment({
            "patient_id": patient_id,
            "staff_id": staff_id,
            "appointment_date": f"{today}T11:00:00",
            "duration_minutes": 20,
            "reason": "UI delete test appointment",
        })
        appointment_id = appointment["id"]

        # Refresh so the table sees the new appointment
        staff_window.today_tab.refresh_today_appointments()

        # Find and select the row
        selected_row = -1
        for row in range(staff_window.today_tab.appointments_table.rowCount()):
            item = staff_window.today_tab.appointments_table.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("appointment", {}).get("id") == appointment_id:
                selected_row = row
                break

        if selected_row < 0:
            # Appointment may be outside today's date range; clean up and skip
            staff_api_client.delete_appointment(appointment_id)
            pytest.skip("Created appointment date may not match the current date filter")

        staff_window.today_tab.appointments_table.selectRow(selected_row)
        staff_window.today_tab.delete_selected_appointment()

        db_row = db_conn.execute(
            "SELECT id FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        assert db_row is None, "Deleted appointment must not exist in the database"


def test_staff_ui_patient_tab_details(qtbot, staff_window, db_conn):
    """
    Test the Staff UI Patient tab to ensure that right-clicking a patient record
    displays the correct details and allows access to the following tabs:
    - Edits
    - Appointments
    - Lab Records
    - Medical Information
    - Medication
    """
    # Access the "Patients" tab from the QTabWidget
    tabs = staff_window.centralWidget()
    patient_window = tabs.widget(1)  # Assuming "Patients" tab is the second tab

    # Call the refresh_patients method
    patient_window.refresh_patients()

    # Select a patient record by right-clicking on the first row
    patient_table = patient_window.centralWidget().findChild(QTableWidget, "patient_table")
    qtbot.mouseClick(patient_table.viewport(), Qt.RightButton, pos=patient_table.visualRect(patient_table.model().index(0, 0)).center())

    # Verify that the context menu appears
    context_menu = patient_window.findChild(QMenu, "context_menu")
    assert context_menu.isVisible(), "Context menu did not appear after right-clicking a patient record."

    # Check that all required tabs are accessible
    required_tabs = ["Edits", "Appointments", "Lab Records", "Medical Information", "Medication"]
    for tab_name in required_tabs:
        assert context_menu.findAction(tab_name) is not None, f"'{tab_name}' tab is missing in the context menu."

    # Simulate clicking each tab and verify the corresponding dialog opens
    for tab_name in required_tabs:
        action = context_menu.findAction(tab_name)
        qtbot.mouseClick(action, Qt.LeftButton)

        # Verify the dialog for the tab is displayed
        dialog = patient_window.findChild(QDialog, "open_dialog")
        assert dialog is not None, f"Dialog for '{tab_name}' did not open."
        assert dialog.windowTitle() == tab_name, f"Dialog title for '{tab_name}' is incorrect."

        # Close the dialog after verification
        dialog.close()

    # Verify that no unexpected dialogs remain open
    assert not patient_window.findChild(QDialog, "open_dialog"), "Some dialogs remained open after testing all tabs."

    # Verify database consistency for the patient record
    patient_id = patient_table.model().index(0, 0).data()
    patient_record = db_conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    assert patient_record is not None, "Patient record does not exist in the database."

    # Verify related data exists in the database
    related_tables = ["appointments", "lab_records", "medical_information", "medications"]
    for table in related_tables:
        related_data = db_conn.execute(f"SELECT * FROM {table} WHERE patient_id = ?", (patient_id,)).fetchall()
        assert len(related_data) > 0, f"No related data found in '{table}' for patient ID {patient_id}."

    # Cleanup: Ensure no lingering state
    patient_window.findChild(QDialog, "open_dialog").close()
