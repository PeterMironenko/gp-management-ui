"""UI → DB tests for AdminWindow – Patient Management and Drug Management tabs.

Drives the real AdminWindow widget:
  * Patient CRUD via open_create_patient_dialog / open_update_patient_dialog /
    open_delete_patient_dialog
  * Drug CRUD via open_create_drug_dialog / open_update_drug_dialog /
    open_delete_drug_dialog
"""

import sys
import os

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTableWidgetItem

_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

import adminwindow as _aw_mod
import patientwindow as _pw_mod


# ---------------------------------------------------------------------------
# Patient dialog stub factories
# ---------------------------------------------------------------------------

def _patient_create_stub(payload: dict):
    """Replacement for patientwindow.PatientDialog (create path)."""
    class _Stub:
        def __init__(self, title, staff_id, patient=None, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _patient_update_stub(payload: dict):
    """Replacement for patientwindow.PatientDialog (update path)."""
    class _Stub:
        def __init__(self, title, staff_id, patient=None, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _delete_user_stub():
    """Replacement for adminwindow.DeleteUserDialog (used for both user and patient deletion)."""
    class _Stub:
        def __init__(self, text, parent=None):
            self.payload = None

        def setWindowTitle(self, _title):
            return None

        def exec_(self):
            return QDialog.Accepted

    return _Stub


# ---------------------------------------------------------------------------
# Drug dialog stub factories
# ---------------------------------------------------------------------------

def _drug_create_stub(payload: dict):
    class _Stub:
        def __init__(self, title, record=None, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


def _drug_update_stub(payload: dict):
    class _Stub:
        def __init__(self, title, record=None, parent=None):
            self.payload = payload

        def exec_(self):
            return QDialog.Accepted

    return _Stub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PATIENT = {
    "first_name": "Patient",
    "last_name": "UITest",
    "date_of_birth": "1990-03-20",
    "landline_phone": "01234567890",
    "mobile_phone": "07777000002",
    "email": "patient.uitest@clinic.test",
    "address_street": "1 Test Street",
    "address_city": "Testtown",
    "address_county": "Testshire",
    "address_postcode": "TE1 1ST",
    "emergency_contact_name": "Emergency Contact",
    "emergency_contact_phone": "07777000003",
}


def _find_row(table, col: int, text: str) -> int:
    """Return the first row index where `table.item(row, col).text() == text`, else -1."""
    for row in range(table.rowCount()):
        item = table.item(row, col)
        if item and item.text() == text:
            return row
    return -1


def _find_row_by_user_role(table, col: int, value) -> int:
    """Return first row where item(row, col).data(UserRole) == value, else -1."""
    for row in range(table.rowCount()):
        item = table.item(row, col)
        if item and item.data(Qt.ItemDataRole.UserRole) == value:
            return row
    return -1


# ---------------------------------------------------------------------------
# Patient tests
# ---------------------------------------------------------------------------

class TestCreatePatient:
    def test_create_patient_appears_in_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        """Drive open_create_patient_dialog() and verify the patient row lands in DB."""
        # Get a valid staff_id from the admin's own staff record
        me = admin_api_client.get_me()
        staff_id = (me.get("staff") or {}).get("id")
        assert staff_id is not None, "Admin must have a staff record"

        payload = {**_VALID_PATIENT, "staff_id": int(staff_id), "email": "db_create@clinic.test"}

        monkeypatch.setattr(_aw_mod, "PatientDialog", _patient_create_stub(payload))
        admin_window.open_create_patient_dialog()

        row = db_conn.execute(
            "SELECT id FROM patients WHERE email = ?", ("db_create@clinic.test",)
        ).fetchone()
        assert row is not None, "Created patient must appear in the database"

        admin_api_client.delete_patient(row["id"])

    def test_create_patient_visible_in_table(self, admin_window, db_conn, monkeypatch, admin_api_client):
        """After creation, patient must appear in the patients_table widget."""
        me = admin_api_client.get_me()
        staff_id = (me.get("staff") or {}).get("id")

        email = "table_visible@clinic.test"
        payload = {**_VALID_PATIENT, "staff_id": int(staff_id), "email": email,
                   "first_name": "Visible", "last_name": "PatientUI"}

        monkeypatch.setattr(_aw_mod, "PatientDialog", _patient_create_stub(payload))
        admin_window.open_create_patient_dialog()

        # Search patients_table for the new first_name
        row_idx = _find_row(admin_window.patients_table, 1, "Visible")
        assert row_idx >= 0, "Created patient must appear in the patients_table widget"

        db_row = db_conn.execute("SELECT id FROM patients WHERE email = ?", (email,)).fetchone()
        if db_row:
            admin_api_client.delete_patient(db_row["id"])


class TestUpdatePatient:
    def test_update_patient_persists_to_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        """Select patient row → open_update_patient_dialog() → verify DB update."""
        me = admin_api_client.get_me()
        staff_id = int((me.get("staff") or {}).get("id"))

        original_patient = admin_api_client.create_patient(
            {**_VALID_PATIENT, "staff_id": staff_id, "email": "upd_before@clinic.test",
             "first_name": "Before", "last_name": "Update"}
        )
        patient_id = original_patient["id"]

        try:
            admin_window.refresh_patients()

            # Find the row by patient_id stored in UserRole data on column 0
            row_idx = _find_row_by_user_role(admin_window.patients_table, 0, patient_id)
            assert row_idx >= 0, "Patient must be in patients_table before update"
            admin_window.patients_table.selectRow(row_idx)

            updated_payload = {**_VALID_PATIENT, "staff_id": staff_id,
                               "email": "upd_after@clinic.test",
                               "first_name": "After", "last_name": "Update"}

            monkeypatch.setattr(_aw_mod, "PatientDialog", _patient_update_stub(updated_payload))
            admin_window.open_update_patient_dialog()

            db_row = db_conn.execute(
                "SELECT first_name, email FROM patients WHERE id = ?", (patient_id,)
            ).fetchone()
            assert db_row is not None
            assert db_row["first_name"] == "After"
            assert db_row["email"] == "upd_after@clinic.test"
        finally:
            try:
                admin_api_client.delete_patient(patient_id)
            except Exception:
                pass


class TestDeletePatient:
    def test_delete_patient_removes_from_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        """Select patient row → open_delete_patient_dialog() → row gone from DB."""
        me = admin_api_client.get_me()
        staff_id = int((me.get("staff") or {}).get("id"))

        patient = admin_api_client.create_patient(
            {**_VALID_PATIENT, "staff_id": staff_id, "email": "del_patient@clinic.test",
             "first_name": "DeleteMe", "last_name": "Patient"}
        )
        patient_id = patient["id"]

        admin_window.refresh_patients()
        row_idx = _find_row_by_user_role(admin_window.patients_table, 0, patient_id)
        assert row_idx >= 0
        admin_window.patients_table.selectRow(row_idx)

        monkeypatch.setattr(_aw_mod, "DeleteUserDialog", _delete_user_stub())
        admin_window.open_delete_patient_dialog()

        db_row = db_conn.execute(
            "SELECT id FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        assert db_row is None, "Deleted patient must not exist in the database"


# ---------------------------------------------------------------------------
# Drug tests
# ---------------------------------------------------------------------------

class TestCreateDrug:
    def test_create_drug_appears_in_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        drug_name = "UITestDrugCreate"
        payload = {
            "drug_name": drug_name,
            "generic_name": "generic_create",
            "form": "tablet",
            "strength": "10mg",
            "manufacturer": "TestPharma",
            "description": "Created by UI test",
            "is_approval_required": False,
        }

        monkeypatch.setattr(_aw_mod, "DrugDialog", _drug_create_stub(payload))
        admin_window.open_create_drug_dialog()

        row = db_conn.execute(
            "SELECT id FROM drugs WHERE drug_name = ?", (drug_name,)
        ).fetchone()
        assert row is not None, "Created drug must appear in the database"

        admin_api_client.delete_drug(row["id"])

    def test_create_drug_visible_in_table(self, admin_window, db_conn, monkeypatch, admin_api_client):
        drug_name = "UITestDrugTable"
        payload = {
            "drug_name": drug_name,
            "generic_name": "generic_table",
            "form": "capsule",
            "strength": "20mg",
            "manufacturer": "TablePharma",
            "description": "Table visibility test",
            "is_approval_required": False,
        }

        monkeypatch.setattr(_aw_mod, "DrugDialog", _drug_create_stub(payload))
        admin_window.open_create_drug_dialog()

        row_idx = _find_row(admin_window.drugs_table, 1, drug_name)
        assert row_idx >= 0, "Created drug must appear in the drugs_table widget"

        db_row = db_conn.execute("SELECT id FROM drugs WHERE drug_name = ?", (drug_name,)).fetchone()
        if db_row:
            admin_api_client.delete_drug(db_row["id"])


class TestUpdateDrug:
    def test_update_drug_persists_to_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        original_name = "UITestDrugBeforeUpdate"
        drug = admin_api_client.create_drug({
            "drug_name": original_name,
            "generic_name": "g_before",
            "is_approval_required": False,
        })
        drug_id = drug["id"]

        try:
            admin_window.refresh_drugs()
            row_idx = _find_row_by_user_role(admin_window.drugs_table, 0, drug_id)
            assert row_idx >= 0, "Drug must be visible in table before update"
            admin_window.drugs_table.selectRow(row_idx)

            updated_payload = {
                "drug_name": "UITestDrugAfterUpdate",
                "generic_name": "g_after",
                "is_approval_required": False,
            }
            monkeypatch.setattr(_aw_mod, "DrugDialog", _drug_update_stub(updated_payload))
            admin_window.open_update_drug_dialog()

            db_row = db_conn.execute(
                "SELECT drug_name FROM drugs WHERE id = ?", (drug_id,)
            ).fetchone()
            assert db_row is not None
            assert db_row["drug_name"] == "UITestDrugAfterUpdate"
        finally:
            try:
                admin_api_client.delete_drug(drug_id)
            except Exception:
                pass


class TestDeleteDrug:
    def test_delete_drug_removes_from_db(self, admin_window, db_conn, monkeypatch, admin_api_client):
        drug = admin_api_client.create_drug({
            "drug_name": "UITestDrugDeleteMe",
            "is_approval_required": False,
        })
        drug_id = drug["id"]

        admin_window.refresh_drugs()
        row_idx = _find_row_by_user_role(admin_window.drugs_table, 0, drug_id)
        assert row_idx >= 0
        admin_window.drugs_table.selectRow(row_idx)

        admin_window.open_delete_drug_dialog()

        db_row = db_conn.execute(
            "SELECT id FROM drugs WHERE id = ?", (drug_id,)
        ).fetchone()
        assert db_row is None, "Deleted drug must not exist in the database"


# ---------------------------------------------------------------------------
# Drug dialog validation
# ---------------------------------------------------------------------------

class TestDrugDialogValidation:
    def test_empty_drug_name_gives_no_payload(self, qapp):
        dialog = _aw_mod.DrugDialog("Create Drug")
        dialog.drug_name.setText("")
        dialog._on_submit()
        assert dialog.payload is None

    def test_valid_drug_name_produces_payload(self, qapp):
        dialog = _aw_mod.DrugDialog("Create Drug")
        dialog.drug_name.setText("ValidDrug")
        dialog.generic_name.setText("generic")
        dialog._on_submit()
        assert dialog.payload is not None
        assert dialog.payload["drug_name"] == "ValidDrug"
