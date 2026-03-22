# UI to Database Test Suite Report

## Purpose
This document describes the PyQt5 UI-to-database automated test suite in `gp-management-ui` and records the latest execution results.

The suite validates end-to-end flows:
- UI interaction in dialogs/windows
- API calls through `ApiClient`
- Persistence verification directly in SQLite

## Test Suite Architecture
- Test framework: `pytest`
- UI test plugin: `pytest-qt`
- UI toolkit: `PyQt5`
- Runtime mode: `QT_QPA_PLATFORM=offscreen`
- Backend strategy: live Flask server started once per test session
- Data verification strategy: direct SQLite assertions through `db_conn`

Core fixture file:
- `tests/conftest.py`

## Coverage Overview
The suite currently includes the following files:

1. `tests/test_ui_login.py`
- Login success for admin and staff users
- Invalid login handling (empty credentials, wrong password)
- Admin/staff routing behavior validation via login state

2. `tests/test_ui_admin_users.py`
- Admin user create, update, delete UI flows
- Database verification for each CRUD action
- Dialog validation cases for create user form

3. `tests/test_ui_admin_patients_drugs.py`
- Admin patient create, update, delete UI flows
- Admin drug create, update, delete UI flows
- Database verification for patient/drug operations
- Drug dialog validation tests

4. `tests/test_ui_approval_flow.py`
- Approval required medication visibility
- Approve action updates DB state
- Approved record disappears from pending approvals table

5. `tests/test_ui_staff_appointments.py`
- Staff patient visibility in appointments tab
- Appointment create and delete flows
- Staff patient tab detail-window access flow
- Database verification for appointment lifecycle

## Detailed Test Steps

This section lists all test cases in `tests/test_ui_*.py` and describes the exact test flow for each.

### tests/test_ui_login.py

1. `test_admin_login_sets_is_admin_true`
- Create `ApiClient` with live server URL.
- Create `LoginDialog` and register it with `qtbot`.
- Fill URL, username `uitestadmin`, password `Admin1234!`.
- Call `handle_login()`.
- Assert access token exists.
- Assert `is_admin` is `True`.

2. `test_staff_login_sets_is_admin_false`
- Create client and login dialog.
- Fill URL, username `uiteststaff`, password `Staff1234!`.
- Call `handle_login()`.
- Assert access token exists.
- Assert `is_admin` is `False`.

3. `test_empty_credentials_shows_warning_no_token`
- Create client and login dialog.
- Monkeypatch `main.QMessageBox` with capture stub for warning calls.
- Fill URL but leave username and password empty.
- Call `handle_login()`.
- Restore original `QMessageBox`.
- Assert no access token issued.
- Assert warning was captured.

4. `test_wrong_password_shows_error_no_token`
- Create client and login dialog.
- Monkeypatch `main.QMessageBox` with capture stub for critical calls.
- Fill URL, valid username `uitestadmin`, invalid password `WrongPassword!`.
- Call `handle_login()`.
- Restore original `QMessageBox`.
- Assert no access token issued.
- Assert critical/error was captured.

5. `test_admin_login_routes_to_admin_window`
- Create client and dialog.
- Fill valid admin credentials.
- Call `handle_login()`.
- Assert `is_admin` is `True` as routing condition for admin window.

6. `test_staff_login_routes_to_staff_window`
- Create client and dialog.
- Fill valid staff credentials.
- Call `handle_login()`.
- Assert `is_admin` is `False` as routing condition for staff window.

### tests/test_ui_admin_users.py

1. `test_create_user_appears_in_db`
- Build unique staff payload and create-user payload.
- Monkeypatch `CreateUserDialog` with accepted stub returning payload.
- Call `admin_window.open_create_dialog()`.
- Query `users` table by username.
- Assert row exists.
- Cleanup by deleting created user via API.

2. `test_created_user_visible_in_table`
- Build unique create payload.
- Monkeypatch `CreateUserDialog`.
- Call `open_create_dialog()`.
- Find username row in `users_table`.
- Assert row is present in UI table.
- Cleanup created DB row via API.

3. `test_update_username_persists_to_db`
- Create user through API with unique staff fields.
- Resolve user id by username using `list_users()`.
- Refresh users and select user row in table.
- Monkeypatch `UpdateUserDialog` to return updated payload.
- Call `open_update_dialog()`.
- Query `users` table by user id.
- Assert username changed in DB.
- Cleanup user via API in `finally` block.

4. `test_delete_user_removes_from_db`
- Create user via API.
- Resolve user id and select corresponding row in table.
- Monkeypatch `DeleteUserDialog` with accepted stub.
- Call `open_delete_dialog()`.
- Query `users` table by id.
- Assert row is removed.

5. `test_delete_user_removed_from_table`
- Create user via API.
- Resolve user id, refresh and select user row.
- Monkeypatch delete dialog stub.
- Call `open_delete_dialog()`.
- Search `users_table` for username.
- Assert row is no longer visible in table.
- Perform best-effort cleanup on exception.

6. `test_create_dialog_empty_username_gives_no_payload`
- Create `CreateUserDialog`.
- Set empty username with valid password values.
- Trigger `_on_submit()`.
- Assert `payload` remains `None`.

7. `test_create_dialog_password_mismatch_gives_no_payload`
- Create dialog.
- Set username and mismatched password/confirm values.
- Trigger `_on_submit()`.
- Assert `payload` remains `None`.

8. `test_create_dialog_valid_input_produces_payload`
- Create dialog.
- Fill valid username, matching passwords, and required staff fields.
- Trigger `_on_submit()`.
- Assert payload is set.
- Assert payload username matches entered value.

### tests/test_ui_admin_patients_drugs.py

1. `test_create_patient_appears_in_db`
- Read admin staff id via `/me`.
- Build patient payload with target `staff_id` and unique email.
- Monkeypatch `PatientDialog` create stub.
- Call `open_create_patient_dialog()`.
- Query `patients` table by email.
- Assert row exists.
- Cleanup patient via API.

2. `test_create_patient_visible_in_table`
- Build patient payload with visible display name and unique email.
- Monkeypatch patient create dialog.
- Call create dialog flow.
- Find row in `patients_table` by first-name column.
- Assert row is visible.
- Cleanup DB row via API.

3. `test_update_patient_persists_to_db`
- Create patient via API.
- Refresh patients and select row by patient id from `UserRole` data.
- Monkeypatch patient update dialog payload.
- Call `open_update_patient_dialog()`.
- Query DB by patient id.
- Assert updated first name and email persisted.
- Cleanup patient in `finally` block.

4. `test_delete_patient_removes_from_db`
- Create patient via API.
- Refresh table and select row by patient id.
- Monkeypatch `DeleteUserDialog` with patient-compatible stub.
- Call `open_delete_patient_dialog()`.
- Query DB for patient id.
- Assert row is deleted.

5. `test_create_drug_appears_in_db`
- Build create-drug payload.
- Monkeypatch `DrugDialog` create stub.
- Call `open_create_drug_dialog()`.
- Query `drugs` table by drug name.
- Assert row exists.
- Cleanup created drug via API.

6. `test_create_drug_visible_in_table`
- Build create-drug payload with unique name.
- Monkeypatch create dialog.
- Execute create flow.
- Find row in `drugs_table` by drug name column.
- Assert row is visible.
- Cleanup created drug.

7. `test_update_drug_persists_to_db`
- Create drug via API.
- Refresh drugs and select row by id (`UserRole` value).
- Monkeypatch update dialog payload.
- Call `open_update_drug_dialog()`.
- Query DB by drug id.
- Assert new drug name persisted.
- Cleanup in `finally` block.

8. `test_delete_drug_removes_from_db`
- Create drug via API.
- Refresh drugs and select row by id.
- Call `open_delete_drug_dialog()` (question dialog auto-confirmed by fixture).
- Query DB by id.
- Assert row is deleted.

9. `test_empty_drug_name_gives_no_payload`
- Create `DrugDialog`.
- Leave `drug_name` empty.
- Submit dialog via `_on_submit()`.
- Assert payload remains `None`.

10. `test_valid_drug_name_produces_payload`
- Create `DrugDialog`.
- Set valid drug name and optional generic name.
- Submit dialog.
- Assert payload exists.
- Assert payload `drug_name` equals `ValidDrug`.

### tests/test_ui_approval_flow.py

Shared fixture `approval_seed` setup steps:
- Read admin staff id from `/me`.
- Create drug with `is_approval_required=True`.
- Create patient assigned to admin staff id.
- Create medication with `is_approved=False`.
- Yield ids for test use.
- Cleanup in order: medication, patient, drug.

1. `test_unapproved_medication_shown_in_table`
- Refresh approval-required records in admin window.
- Iterate table rows and inspect medication dict in column 0 `UserRole`.
- Match by seeded medication id.
- Assert seeded medication is present.

2. `test_approve_medication_updates_db`
- Refresh approval-required data.
- Build medication dict payload with required fields.
- Call `admin_window._approve_medication()`.
- Query `medications` table by id.
- Assert `is_approved` is truthy in DB.

3. `test_approved_medication_removed_from_table`
- Refresh approval-required table and find seeded medication row.
- Call `_approve_medication()` for that row's medication dict.
- Refresh table again.
- Scan rows by medication id.
- Assert medication is no longer present.

4. `test_approved_medication_approval_count_decreases`
- Refresh table and count all pending unapproved medication rows.
- Identify seeded medication row data.
- Approve seeded medication.
- Refresh and recount pending rows.
- Assert pending count decreased.

### tests/test_ui_staff_appointments.py

Shared fixture `staff_patient` setup steps:
- Read staff user staff id from `/me`.
- Create patient assigned to that staff id via admin API.
- Yield patient object.
- Cleanup patient after test.

1. `test_patient_visible_after_refresh`
- Call `staff_window.today_tab.refresh_today_appointments()`.
- Collect patient ids from `today_tab.staff_patients`.
- Assert fixture patient id is included.

2. `test_create_appointment_persists_to_db`
- Refresh appointments tab.
- Read current staff id and patient id.
- Build appointment payload.
- Stub `_choose_patient_for_create()` to return fixture patient.
- Monkeypatch `AppointmentDialog` create stub.
- Call `open_create_dialog()`.
- Query `appointments` table by patient id and reason.
- Assert row exists.
- Cleanup appointment via API.

3. `test_create_appointment_visible_in_table`
- Refresh appointments tab.
- Build same-day appointment payload.
- Stub patient picker and monkeypatch create dialog.
- Call `open_create_dialog()`.
- Scan `appointments_table` reason column.
- Assert new reason text appears in UI.
- Cleanup created appointment if found.

4. `test_delete_appointment_removes_from_db`
- Create same-day appointment via API.
- Refresh appointments table.
- Find row by appointment id in row `UserRole` payload.
- If not found, cleanup and skip (date-filter mismatch guard).
- Select row and call `delete_selected_appointment()`.
- Query DB by appointment id.
- Assert row is deleted.

5. `test_staff_ui_patient_tab_details`
- Access the real `PatientWindow` instance via `staff_window.patient_window`.
- Refresh the patient table for the logged-in staff member.
- Find the fixture patient row in `patient_table` by matching selected patient id from the row `UserRole` payload.
- Select the patient row.
- Monkeypatch the supported patient detail windows:
	- `AppointmentsWindow`
	- `LabRecordsWindow`
	- `MedicalInformationWindow`
	- `MedicationsWindow`
- Call each public patient detail opener:
	- `open_appointments_window()`
	- `open_labrecords_window()`
	- `open_medicalinformation_window()`
	- `open_medications_window()`
- Assert each detail window was invoked with the selected patient and `PatientWindow` as parent.

## How To Run
From `gp-management-ui`:

**On Linux and MacOS**
```bash
pip install -r requirements-test.txt
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m pytest -q
```

**On Windows**
```PowerShell
pip install -r requirements-test.txt
set QT_QPA_PLATFORM=offscreen
.\.venv\Scripts\py.test.exe -m pytest -q
```

If you want to have report for each induvidual test, run command with additional *-v* option, like this:

```PowerShell
.\.venv\Scripts\py.test.exe -m pytest -q -v
```

You should see the output as below:

```PowerShell
tests/test_ui_admin_patients_drugs.py::TestCreatePatient::test_create_patient_appears_in_db PASSED                                                                                                                                                                                                                                                                                [  3%]
tests/test_ui_admin_patients_drugs.py::TestCreatePatient::test_create_patient_visible_in_table PASSED                                                                                                                                                                                                                                                                             [  6%]
tests/test_ui_admin_patients_drugs.py::TestUpdatePatient::test_update_patient_persists_to_db PASSED                                                                                                                                                                                                                                                                               [  9%]
tests/test_ui_admin_patients_drugs.py::TestDeletePatient::test_delete_patient_removes_from_db PASSED                                                                                                                                                                                                                                                                              [ 12%]
tests/test_ui_admin_patients_drugs.py::TestCreateDrug::test_create_drug_appears_in_db PASSED                                                                                                                                                                                                                                                                                      [ 15%]
tests/test_ui_admin_patients_drugs.py::TestCreateDrug::test_create_drug_visible_in_table PASSED                                                                                                                                                                                                                                                                                   [ 18%]
tests/test_ui_admin_patients_drugs.py::TestUpdateDrug::test_update_drug_persists_to_db PASSED                                                                                                                                                                                                                                                                                     [ 21%]
tests/test_ui_admin_patients_drugs.py::TestDeleteDrug::test_delete_drug_removes_from_db PASSED                                                                                                                                                                                                                                                                                    [ 25%]
tests/test_ui_admin_patients_drugs.py::TestDrugDialogValidation::test_empty_drug_name_gives_no_payload PASSED                                                                                                                                                                                                                                                                     [ 28%] 
tests/test_ui_admin_patients_drugs.py::TestDrugDialogValidation::test_valid_drug_name_produces_payload PASSED  
```


## Latest Test Results
Execution date: 2026-03-22

Summary:
- Collected: 33 tests
- Passed: 33
- Failed: 0
- Errors: 0
- Warnings: 1
- Duration: 2.63s

Module-level result:
- `tests/test_ui_admin_patients_drugs.py` -> 10 passed
- `tests/test_ui_admin_users.py` -> 8 passed
- `tests/test_ui_approval_flow.py` -> 4 passed
- `tests/test_ui_login.py` -> 6 passed
- `tests/test_ui_staff_appointments.py` -> 5 passed

Warning details:
- `DeprecationWarning` from `passlib` using `crypt` (Python 3.13 deprecation notice)

## Notes
- The suite uses a real backend and verifies persisted rows, so these are integration-style UI tests rather than pure unit tests.
- Dialog interactions are stabilized by controlled dialog stubs and message-box suppression in test fixtures.
