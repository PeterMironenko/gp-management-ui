"""UI → DB tests for AdminWindow – Approval Required tab.

Verifies the end-to-end flow:
  drug (is_approval_required=True) + patient + medication (unapproved)
    → refresh_approval_required_records() shows it in the table
    → _approve_medication()  updates DB (is_approved = True)
    → second refresh removes it from the table
"""

import sys
import os

import pytest
from PyQt5.QtCore import Qt

_TESTS_DIR = os.path.dirname(__file__)
_UI_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _UI_DIR not in sys.path:
    sys.path.insert(0, _UI_DIR)

_VALID_PATIENT = {
    "first_name": "Approval",
    "last_name": "FlowPatient",
    "date_of_birth": "1975-11-01",
    "landline_phone": "01234567891",
    "mobile_phone": "07777000010",
    "email": "approvalflow@clinic.test",
    "address_street": "10 Approval Lane",
    "address_city": "Approveton",
    "address_county": "Approvalshire",
    "address_postcode": "AP1 1AP",
    "emergency_contact_name": "Emergency ApprovalContact",
    "emergency_contact_phone": "07777000011",
}


@pytest.fixture()
def approval_seed(admin_api_client):
    """Seed drug + patient + unapproved medication; yield their ids; clean up after."""
    me = admin_api_client.get_me()
    staff_id = int((me.get("staff") or {}).get("id"))

    drug = admin_api_client.create_drug({
        "drug_name": "ApprovalTestDrug",
        "generic_name": "atd_generic",
        "is_approval_required": True,
    })
    drug_id = drug["id"]

    patient = admin_api_client.create_patient(
        {**_VALID_PATIENT, "staff_id": staff_id, "email": "approvalflow@clinic.test"}
    )
    patient_id = patient["id"]

    med = admin_api_client.create_medication({
        "patient_id": patient_id,
        "staff_id": staff_id,
        "drug_id": drug_id,
        "dosage": "10mg",
        "frequency": "twice daily",
        "route": "oral",
        "start_date": "2024-01-15",
        "is_approved": False,
    })
    med_id = med["id"]

    yield {
        "drug_id": drug_id,
        "patient_id": patient_id,
        "medication_id": med_id,
        "staff_id": staff_id,
    }

    # Cleanup (order matters: medication → patient → drug)
    for cleanup_fn, _id in [
        (admin_api_client.delete_medication, med_id),
        (admin_api_client.delete_patient, patient_id),
        (admin_api_client.delete_drug, drug_id),
    ]:
        try:
            cleanup_fn(_id)
        except Exception:
            pass


class TestApprovalFlow:
    def test_unapproved_medication_shown_in_table(self, admin_window, approval_seed):
        """After seeding an unapproved medication, it must appear in the approval_required_table."""
        admin_window.refresh_approval_required_records()

        # Find the row whose medication id matches our seeded medication
        med_id = approval_seed["medication_id"]
        found = False
        for row in range(admin_window.approval_required_table.rowCount()):
            item = admin_window.approval_required_table.item(row, 0)
            if item is None:
                continue
            med_dict = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(med_dict, dict) and med_dict.get("id") == med_id:
                found = True
                break

        assert found, (
            f"Unapproved medication (id={med_id}) must appear in the approval_required_table"
        )

    def test_approve_medication_updates_db(self, admin_window, db_conn, approval_seed):
        """Calling _approve_medication() must set is_approved=True in the database."""
        admin_window.refresh_approval_required_records()

        med_id = approval_seed["medication_id"]
        staff_id = approval_seed["staff_id"]

        # Build the medication dict as the table would hold it
        medication_dict = {
            "id": med_id,
            "patient_id": approval_seed["patient_id"],
            "staff_id": staff_id,
            "drug_id": approval_seed["drug_id"],
            "dosage": "10mg",
            "frequency": "twice daily",
            "route": "oral",
            "start_date": "2024-01-15",
            "end_date": None,
            "notes": None,
            "is_approved": False,
        }

        admin_window._approve_medication(medication_dict)

        row = db_conn.execute(
            "SELECT is_approved FROM medications WHERE id = ?", (med_id,)
        ).fetchone()
        assert row is not None
        assert row["is_approved"], (
            "is_approved must be truthy in the DB after _approve_medication()"
        )

    def test_approved_medication_removed_from_table(self, admin_window, db_conn, approval_seed):
        """After approving, refreshing the table must remove the medication from view."""
        admin_window.refresh_approval_required_records()

        med_id = approval_seed["medication_id"]
        staff_id = approval_seed["staff_id"]

        # Extract the medication dict from table (row 0 in the approval required table)
        item = None
        for row in range(admin_window.approval_required_table.rowCount()):
            candidate = admin_window.approval_required_table.item(row, 0)
            if candidate is None:
                continue
            med_dict = candidate.data(Qt.ItemDataRole.UserRole)
            if isinstance(med_dict, dict) and med_dict.get("id") == med_id:
                item = med_dict
                break

        assert item is not None, "Seeded medication must be present before approving"

        admin_window._approve_medication(item)
        admin_window.refresh_approval_required_records()

        # The medication should no longer appear
        still_present = False
        for row in range(admin_window.approval_required_table.rowCount()):
            candidate = admin_window.approval_required_table.item(row, 0)
            if candidate is None:
                continue
            med_dict = candidate.data(Qt.ItemDataRole.UserRole)
            if isinstance(med_dict, dict) and med_dict.get("id") == med_id:
                still_present = True
                break

        assert not still_present, (
            "Approved medication must not appear in the approval_required_table after refresh"
        )

    def test_approved_medication_approval_count_decreases(self, admin_window, approval_seed):
        """Approving one medication must reduce the visible row count by at least one."""
        admin_window.refresh_approval_required_records()

        med_id = approval_seed["medication_id"]
        count_before = 0
        med_dict_to_approve = None

        for row in range(admin_window.approval_required_table.rowCount()):
            item = admin_window.approval_required_table.item(row, 0)
            if item is None:
                continue
            d = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(d, dict) and not d.get("is_approved"):
                count_before += 1
                if d.get("id") == med_id:
                    med_dict_to_approve = d

        assert med_dict_to_approve is not None, "Seeded medication must be in the table"

        admin_window._approve_medication(med_dict_to_approve)
        admin_window.refresh_approval_required_records()

        count_after = sum(
            1
            for row in range(admin_window.approval_required_table.rowCount())
            if (lambda item: item is not None and isinstance(item.data(Qt.ItemDataRole.UserRole), dict))(
                admin_window.approval_required_table.item(row, 0)
            )
            and not admin_window.approval_required_table.item(row, 0).data(Qt.ItemDataRole.UserRole).get("is_approved")
        )

        assert count_after < count_before, (
            "Approving a medication must reduce the number of pending approval rows"
        )
