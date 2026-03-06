import re
from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import Qt, QLocale, QDate, QDateTime, QTime
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from apiclient import ApiClient


SYSTEM_LOCALE = QLocale.system()
LOCALE_DATE_FORMAT = SYSTEM_LOCALE.dateFormat(QLocale.ShortFormat)
LOCALE_DATETIME_FORMAT = SYSTEM_LOCALE.dateTimeFormat(QLocale.ShortFormat)


def _apply_refresh_icon(button: QPushButton) -> None:
    refresh_icon = QIcon.fromTheme("view-refresh")
    if not refresh_icon.isNull():
        button.setIcon(refresh_icon)
    else:
        button.setText("⟳")


def _apply_create_icon(button: QPushButton) -> None:
    create_icon = QIcon.fromTheme("list-add")
    if not create_icon.isNull():
        button.setIcon(create_icon)
    else:
        button.setText("+")


def _create_list_header(text: str) -> QLabel:
    label = QLabel(text)
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setBold(True)
    label.setFont(font)
    return label


def _iso_date_to_locale_text(value: str) -> str:
    if not value:
        return ""
    date_value = QDate.fromString(value, "yyyy-MM-dd")
    if not date_value.isValid():
        return value
    return SYSTEM_LOCALE.toString(date_value, LOCALE_DATE_FORMAT)


def _iso_datetime_to_locale_text(value: str) -> str:
    if not value:
        return ""
    datetime_value = QDateTime.fromString(value, "yyyy-MM-ddTHH:mm:ss")
    if not datetime_value.isValid():
        datetime_value = QDateTime.fromString(value, "yyyy-MM-ddTHH:mm")
    if not datetime_value.isValid():
        datetime_value = QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss")
    if not datetime_value.isValid():
        return value
    return SYSTEM_LOCALE.toString(datetime_value, LOCALE_DATETIME_FORMAT)


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


def _locale_or_iso_to_iso_datetime(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None

    datetime_value = SYSTEM_LOCALE.toDateTime(text, LOCALE_DATETIME_FORMAT)
    if not datetime_value.isValid():
        datetime_value = QDateTime.fromString(text, "yyyy-MM-ddTHH:mm:ss")
    if not datetime_value.isValid():
        datetime_value = QDateTime.fromString(text, "yyyy-MM-ddTHH:mm")
    if not datetime_value.isValid():
        datetime_value = QDateTime.fromString(text, "yyyy-MM-dd HH:mm:ss")
    if not datetime_value.isValid():
        return None
    return datetime_value.toString("yyyy-MM-ddTHH:mm:ss")


def validate_patient_data(patient_data: dict) -> Optional[str]:
    dob = patient_data.get("date_of_birth")
    if dob:
        parsed = _locale_or_iso_to_iso_date(dob)
        if parsed is None:
            return f"Date of Birth must match locale format ({LOCALE_DATE_FORMAT}) or ISO format (YYYY-MM-DD)."
        patient_data["date_of_birth"] = parsed

    phone_pattern = re.compile(r"^\+?[0-9]{7,15}$")
    for field in ("landline_phone", "mobile_phone", "emergency_contact_phone"):
        value = patient_data.get(field)
        if value and not phone_pattern.match(value):
            return f"{field.replace('_', ' ').title()} is invalid."

    email = patient_data.get("email")
    if email:
        email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        if not email_pattern.match(email):
            return "Email must be a valid address."

    return None


class PatientDialog(QDialog):
    def __init__(self, title: str, staff_id: int, patient: Optional[dict] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.staff_id = staff_id
        self.payload: Optional[dict] = None

        patient = patient or {}

        layout = QGridLayout()

        self.first_name = QLineEdit(patient.get("first_name", ""))
        self.last_name = QLineEdit(patient.get("last_name", ""))
        self.date_of_birth = QLineEdit(_iso_date_to_locale_text(patient.get("date_of_birth", "")))
        self.date_of_birth.setPlaceholderText(LOCALE_DATE_FORMAT)
        self.landline_phone = QLineEdit(patient.get("landline_phone", ""))
        self.mobile_phone = QLineEdit(patient.get("mobile_phone", ""))
        self.email = QLineEdit(patient.get("email", ""))
        self.address_street = QLineEdit(patient.get("address_street", ""))
        self.address_city = QLineEdit(patient.get("address_city", ""))
        self.address_county = QLineEdit(patient.get("address_county", ""))
        self.address_postcode = QLineEdit(patient.get("address_postcode", ""))
        self.emergency_contact_name = QLineEdit(patient.get("emergency_contact_name", ""))
        self.emergency_contact_phone = QLineEdit(patient.get("emergency_contact_phone", ""))

        labels = [
            ("First Name:", self.first_name),
            ("Last Name:", self.last_name),
            ("DOB:", self.date_of_birth),
            ("Landline:", self.landline_phone),
            ("Mobile:", self.mobile_phone),
            ("Email:", self.email),
            ("Street:", self.address_street),
            ("City:", self.address_city),
            ("County:", self.address_county),
            ("Postcode:", self.address_postcode),
            ("Emergency Name:", self.emergency_contact_name),
            ("Emergency Phone:", self.emergency_contact_phone),
        ]

        for row, (label, widget) in enumerate(labels):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(widget, row, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, len(labels), 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        payload = {
            "staff_id": self.staff_id,
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "date_of_birth": self.date_of_birth.text().strip(),
            "landline_phone": self.landline_phone.text().strip(),
            "mobile_phone": self.mobile_phone.text().strip(),
            "email": self.email.text().strip(),
            "address_street": self.address_street.text().strip(),
            "address_city": self.address_city.text().strip(),
            "address_county": self.address_county.text().strip(),
            "address_postcode": self.address_postcode.text().strip(),
            "emergency_contact_name": self.emergency_contact_name.text().strip(),
            "emergency_contact_phone": self.emergency_contact_phone.text().strip(),
        }

        required_fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "landline_phone",
            "mobile_phone",
            "email",
            "address_street",
            "address_city",
            "address_county",
            "address_postcode",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
        for field in required_fields:
            if not payload[field]:
                QMessageBox.warning(self, "Validation Error", f"{field.replace('_', ' ').title()} is required.")
                return

        validation_error = validate_patient_data(payload)
        if validation_error:
            QMessageBox.warning(self, "Validation Error", validation_error)
            return

        self.payload = payload
        self.accept()


class FilterPatientsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filter Patients")
        self.payload: Optional[dict] = None

        layout = QGridLayout()
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.mobile_phone = QLineEdit()
        self.city = QLineEdit()

        layout.addWidget(QLabel("First Name:"), 0, 0)
        layout.addWidget(self.first_name, 0, 1)
        layout.addWidget(QLabel("Last Name:"), 1, 0)
        layout.addWidget(self.last_name, 1, 1)
        layout.addWidget(QLabel("Email:"), 2, 0)
        layout.addWidget(self.email, 2, 1)
        layout.addWidget(QLabel("Mobile Phone:"), 3, 0)
        layout.addWidget(self.mobile_phone, 3, 1)
        layout.addWidget(QLabel("City:"), 4, 0)
        layout.addWidget(self.city, 4, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 5, 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        self.payload = {
            "first_name": self.first_name.text().strip() or None,
            "last_name": self.last_name.text().strip() or None,
            "email": self.email.text().strip() or None,
            "mobile_phone": self.mobile_phone.text().strip() or None,
            "address_city": self.city.text().strip() or None,
        }
        self.accept()


class AppointmentDialog(QDialog):
    def __init__(
        self,
        title: str,
        patient_id: int,
        staff_id: int,
        appointment: Optional[dict] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.payload: Optional[dict] = None
        appointment = appointment or {}

        initial_datetime = QDateTime.currentDateTime()
        appointment_raw = str(appointment.get("appointment_date", "") or "")
        for fmt in ("yyyy-MM-ddTHH:mm:ss", "yyyy-MM-ddTHH:mm", "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm"):
            parsed = QDateTime.fromString(appointment_raw, fmt)
            if parsed.isValid():
                initial_datetime = parsed
                break

        layout = QGridLayout()
        self.appointment_date = QDateEdit()
        self.appointment_date.setCalendarPopup(True)
        self.appointment_date.setDate(initial_datetime.date())
        self.appointment_time = QTimeEdit()
        self.appointment_time.setDisplayFormat("HH:mm")
        self.appointment_time.setTime(initial_datetime.time())
        self.duration_minutes = QLineEdit(str(appointment.get("duration_minutes", "")))
        self.reason = QLineEdit(appointment.get("reason", ""))
        self.notes = QLineEdit(appointment.get("notes", ""))
        self.location = QLineEdit(appointment.get("location", ""))

        layout.addWidget(QLabel("Date:"), 0, 0)
        layout.addWidget(self.appointment_date, 0, 1)
        layout.addWidget(QLabel("Time:"), 1, 0)
        layout.addWidget(self.appointment_time, 1, 1)
        layout.addWidget(QLabel("Duration (min):"), 2, 0)
        layout.addWidget(self.duration_minutes, 2, 1)
        layout.addWidget(QLabel("Reason:"), 3, 0)
        layout.addWidget(self.reason, 3, 1)
        layout.addWidget(QLabel("Notes:"), 4, 0)
        layout.addWidget(self.notes, 4, 1)
        layout.addWidget(QLabel("Location:"), 5, 0)
        layout.addWidget(self.location, 5, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 6, 0, 1, 2)

        self.patient_id = patient_id
        self.staff_id = staff_id
        self.setLayout(layout)

    def _on_submit(self) -> None:
        duration_text = self.duration_minutes.text().strip()
        reason = self.reason.text().strip()

        if not duration_text or not reason:
            QMessageBox.warning(self, "Validation Error", "Date, duration and reason are required.")
            return

        appointment_datetime = QDateTime(self.appointment_date.date(), self.appointment_time.time())
        if not appointment_datetime.isValid():
            QMessageBox.warning(self, "Validation Error", "Date and time must be valid.")
            return
        iso_datetime = appointment_datetime.toString("yyyy-MM-ddTHH:mm:ss")

        if not duration_text.isdigit() or int(duration_text) <= 0:
            QMessageBox.warning(self, "Validation Error", "Duration must be a positive number of minutes.")
            return

        self.payload = {
            "patient_id": self.patient_id,
            "staff_id": self.staff_id,
            "appointment_date": iso_datetime,
            "duration_minutes": int(duration_text),
            "reason": reason,
            "notes": self.notes.text().strip() or None,
            "location": self.location.text().strip() or None,
        }
        self.accept()


class AppointmentsWindow(QDialog):
    def __init__(self, api_client: ApiClient, patient: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.patient = patient
        self.appointments: List[dict] = []
        patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
        self.setWindowTitle(f"Appointments - {patient_name or 'Patient'}")
        self.resize(900, 450)

        layout = QVBoxLayout()
        header = QLabel(
            f"Patient ID: {patient.get('id', '-')}  |  "
            f"{patient.get('first_name', '-')} {patient.get('last_name', '-')}"
        )
        layout.addWidget(header)
        self.appointments_table = QTableWidget(0, 5)
        self.appointments_table.setHorizontalHeaderLabels(["ID", "Date & Time", "Duration", "Reason", "Location"])
        self.appointments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.appointments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.appointments_table.setSelectionMode(QTableWidget.SingleSelection)
        self.appointments_table.verticalHeader().setVisible(False)
        self.appointments_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        self.appointments_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.appointments_table.customContextMenuRequested.connect(self._open_context_menu)
        header_widget = self.appointments_table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(3, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.appointments_table)

        top_controls = QHBoxLayout()
        top_controls.addStretch()
        create_button = QPushButton()
        _apply_create_icon(create_button)
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_appointments)
        top_controls.addWidget(create_button)
        top_controls.addWidget(refresh_button)
        layout.addLayout(top_controls)

        controls = QHBoxLayout()
        delete_button = QPushButton("Delete")
        controls.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

        self.setLayout(layout)
        self.refresh_appointments()

    def refresh_appointments(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected patient does not have a valid id.")
            return
        try:
            appointments = self.api_client.list_appointments(patient_id=patient_id)
            self._render_appointments(appointments)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load appointments: {str(exc)}")

    def _render_appointments(self, appointments: List[dict]) -> None:
        self.appointments = appointments
        self.appointments_table.clearContents()
        self.appointments_table.setRowCount(len(appointments))

        for row_index, appointment in enumerate(appointments):
            id_item = QTableWidgetItem(str(appointment.get("id", "-")))
            id_item.setData(Qt.ItemDataRole.UserRole, appointment)
            self.appointments_table.setItem(row_index, 0, id_item)
            self.appointments_table.setItem(row_index, 1, QTableWidgetItem(str(appointment.get("appointment_date") or "-")))
            self.appointments_table.setItem(row_index, 2, QTableWidgetItem(str(appointment.get("duration_minutes") or "-")))
            self.appointments_table.setItem(row_index, 3, QTableWidgetItem(str(appointment.get("reason") or "-")))
            self.appointments_table.setItem(row_index, 4, QTableWidgetItem(str(appointment.get("location") or "-")))

    def _selected_appointment(self) -> Optional[dict]:
        row = self.appointments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select an appointment first.")
            return None
        item = self.appointments_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected row does not contain an appointment.")
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            QMessageBox.warning(self, "Warning", "Selected row does not contain an appointment.")
            return None
        return data

    def _open_context_menu(self, pos) -> None:
        row = self.appointments_table.indexAt(pos).row()
        if row < 0:
            return
        self.appointments_table.setCurrentCell(row, 0)

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.appointments_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.delete_selected_appointment()

    def open_create_dialog(self) -> None:
        patient_id = self.patient.get("id")
        staff_id = self.patient.get("staff_id")
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return
        dialog = AppointmentDialog("Create Appointment", patient_id=patient_id, staff_id=staff_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_appointment(dialog.payload)
                QMessageBox.information(self, "Success", "Appointment created successfully.")
                self.refresh_appointments()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        appointment = self._selected_appointment()
        if not appointment:
            return
        patient_id = self.patient.get("id")
        staff_id = self.patient.get("staff_id")
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return
        dialog = AppointmentDialog(
            "Update Appointment",
            patient_id=patient_id,
            staff_id=staff_id,
            appointment=appointment,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_appointment(int(appointment["id"]), dialog.payload)
                QMessageBox.information(self, "Success", "Appointment updated successfully.")
                self.refresh_appointments()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_appointment(self) -> None:
        appointment = self._selected_appointment()
        if not appointment:
            return
        prompt = f"Delete appointment ID {appointment.get('id', '-') }?"
        if QMessageBox.question(self, "Confirm Delete", prompt) != QMessageBox.Yes:
            return
        try:
            self.api_client.delete_appointment(int(appointment["id"]))
            QMessageBox.information(self, "Success", "Appointment deleted successfully.")
            self.refresh_appointments()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))


class LabRecordDialog(QDialog):
    def __init__(
        self,
        title: str,
        patient_id: int,
        staff_id: int,
        labrecord: Optional[dict] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.payload: Optional[dict] = None
        labrecord = labrecord or {}

        layout = QGridLayout()
        self.test_type = QLineEdit(labrecord.get("test_type", ""))
        self.test_name = QLineEdit(labrecord.get("test_name", ""))
        self.test_date = QLineEdit(_iso_datetime_to_locale_text(labrecord.get("test_date", "")))
        self.test_date.setPlaceholderText(LOCALE_DATETIME_FORMAT)
        self.result_input = QLineEdit(labrecord.get("result", ""))
        self.notes = QLineEdit(labrecord.get("notes", ""))

        layout.addWidget(QLabel("Test Type:"), 0, 0)
        layout.addWidget(self.test_type, 0, 1)
        layout.addWidget(QLabel("Test Name:"), 1, 0)
        layout.addWidget(self.test_name, 1, 1)
        layout.addWidget(QLabel("Test Date:"), 2, 0)
        layout.addWidget(self.test_date, 2, 1)
        layout.addWidget(QLabel("Result:"), 3, 0)
        layout.addWidget(self.result_input, 3, 1)
        layout.addWidget(QLabel("Notes:"), 4, 0)
        layout.addWidget(self.notes, 4, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 5, 0, 1, 2)

        self.patient_id = patient_id
        self.staff_id = staff_id
        self.setLayout(layout)

    def _on_submit(self) -> None:
        test_type = self.test_type.text().strip()
        test_name = self.test_name.text().strip()
        test_date = self.test_date.text().strip()
        if not test_type or not test_name or not test_date:
            QMessageBox.warning(self, "Validation Error", "Test type, test name and test date are required.")
            return
        iso_datetime = _locale_or_iso_to_iso_datetime(test_date)
        if iso_datetime is None:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Test date must match locale format ({LOCALE_DATETIME_FORMAT}) or ISO datetime format.",
            )
            return

        self.payload = {
            "patient_id": self.patient_id,
            "staff_id": self.staff_id,
            "test_type": test_type,
            "test_name": test_name,
            "test_date": iso_datetime,
            "result": self.result_input.text().strip() or None,
            "notes": self.notes.text().strip() or None,
        }
        self.accept()


class FilterLabRecordsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filter Lab Records")
        self.payload: Optional[dict] = None

        layout = QGridLayout()
        self.test_type = QLineEdit()
        self.test_name = QLineEdit()
        self.result_input = QLineEdit()

        layout.addWidget(QLabel("Test Type:"), 0, 0)
        layout.addWidget(self.test_type, 0, 1)
        layout.addWidget(QLabel("Test Name:"), 1, 0)
        layout.addWidget(self.test_name, 1, 1)
        layout.addWidget(QLabel("Result:"), 2, 0)
        layout.addWidget(self.result_input, 2, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 3, 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        self.payload = {
            "test_type": self.test_type.text().strip() or None,
            "test_name": self.test_name.text().strip() or None,
            "result": self.result_input.text().strip() or None,
        }
        self.accept()


class LabRecordsWindow(QDialog):
    def __init__(self, api_client: ApiClient, patient: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.patient = patient
        self.all_records: List[dict] = []

        self.setWindowTitle("Lab Records")
        self.resize(900, 450)

        layout = QVBoxLayout()
        header = QLabel(
            f"Patient ID: {patient.get('id', '-')}  |  "
            f"{patient.get('first_name', '-')} {patient.get('last_name', '-')}"
        )
        layout.addWidget(header)
        self.records_table = QTableWidget(0, 5)
        self.records_table.setHorizontalHeaderLabels(["ID", "Test Type", "Test Name", "Test Date", "Result"])
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setSelectionMode(QTableWidget.SingleSelection)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        self.records_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self._open_context_menu)
        header_widget = self.records_table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(2, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.records_table)

        top_controls = QHBoxLayout()
        top_controls.addStretch()
        create_button = QPushButton()
        _apply_create_icon(create_button)
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_records)
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_filter_dialog)
        top_controls.addWidget(create_button)
        top_controls.addWidget(refresh_button)
        top_controls.addWidget(filter_button)
        layout.addLayout(top_controls)

        controls = QHBoxLayout()
        controls.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

        self.setLayout(layout)
        self.refresh_records()

    def refresh_records(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected patient does not have a valid id.")
            return
        try:
            self.all_records = self.api_client.list_labrecords(patient_id=patient_id)
            self._render_records(self.all_records)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load lab records: {str(exc)}")

    def _render_records(self, records: List[dict]) -> None:
        self.records_table.clearContents()
        self.records_table.setRowCount(len(records))

        for row_index, record in enumerate(records):
            id_item = QTableWidgetItem(str(record.get("id", "-")))
            id_item.setData(Qt.ItemDataRole.UserRole, record)
            self.records_table.setItem(row_index, 0, id_item)
            self.records_table.setItem(row_index, 1, QTableWidgetItem(str(record.get("test_type") or "-")))
            self.records_table.setItem(row_index, 2, QTableWidgetItem(str(record.get("test_name") or "-")))
            self.records_table.setItem(row_index, 3, QTableWidgetItem(str(record.get("test_date") or "-")))
            self.records_table.setItem(row_index, 4, QTableWidgetItem(str(record.get("result") or "-")))

    def _selected_record(self) -> Optional[dict]:
        row = self.records_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a lab record first.")
            return None
        item = self.records_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected row does not contain a lab record.")
            return None
        record = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(record, dict):
            QMessageBox.warning(self, "Warning", "Selected row does not contain a lab record.")
            return None
        return record

    def _open_context_menu(self, pos) -> None:
        row = self.records_table.indexAt(pos).row()
        if row < 0:
            return
        self.records_table.setCurrentCell(row, 0)

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.records_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.delete_selected_record()

    def open_create_dialog(self) -> None:
        patient_id = self.patient.get("id")
        staff_id = self.patient.get("staff_id")
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return
        dialog = LabRecordDialog("Create Lab Record", patient_id=patient_id, staff_id=staff_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_labrecord(dialog.payload)
                QMessageBox.information(self, "Success", "Lab record created successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        record = self._selected_record()
        if not record:
            return
        patient_id = self.patient.get("id")
        staff_id = self.patient.get("staff_id")
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return
        dialog = LabRecordDialog(
            "Update Lab Record",
            patient_id=patient_id,
            staff_id=staff_id,
            labrecord=record,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_labrecord(int(record["id"]), dialog.payload)
                QMessageBox.information(self, "Success", "Lab record updated successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_record(self) -> None:
        record = self._selected_record()
        if not record:
            return
        if QMessageBox.question(self, "Confirm Delete", f"Delete lab record ID {record.get('id', '-')}?") != QMessageBox.Yes:
            return
        try:
            self.api_client.delete_labrecord(int(record["id"]))
            QMessageBox.information(self, "Success", "Lab record deleted successfully.")
            self.refresh_records()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def _matches_filter(self, record: dict, criteria: dict) -> bool:
        def contains(value: str, query: str) -> bool:
            return query.lower() in (value or "").lower()

        if criteria.get("test_type") and not contains(record.get("test_type", ""), criteria["test_type"]):
            return False
        if criteria.get("test_name") and not contains(record.get("test_name", ""), criteria["test_name"]):
            return False
        if criteria.get("result") and not contains(record.get("result", ""), criteria["result"]):
            return False
        return True

    def open_filter_dialog(self) -> None:
        dialog = FilterLabRecordsDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered = [record for record in self.all_records if self._matches_filter(record, dialog.payload)]
            self._render_records(filtered)


class MedicalInformationDialog(QDialog):
    def __init__(self, title: str, patient_id: int, record: Optional[dict] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.payload: Optional[dict] = None
        record = record or {}

        layout = QGridLayout()
        self.primary_condition = QLineEdit(record.get("primary_condition", ""))
        self.chronicillnesses = QLineEdit(record.get("chronicillnesses", ""))
        self.allergies = QLineEdit(record.get("allergies", ""))
        self.surgeries = QLineEdit(record.get("surgeries", ""))
        self.immunization = QLineEdit(record.get("immunization", ""))
        self.last_updated = QLineEdit(_iso_datetime_to_locale_text(record.get("last_updated", "")))
        self.last_updated.setPlaceholderText(LOCALE_DATETIME_FORMAT)

        layout.addWidget(QLabel("Primary Condition:"), 0, 0)
        layout.addWidget(self.primary_condition, 0, 1)
        layout.addWidget(QLabel("Chronic Illnesses:"), 1, 0)
        layout.addWidget(self.chronicillnesses, 1, 1)
        layout.addWidget(QLabel("Allergies:"), 2, 0)
        layout.addWidget(self.allergies, 2, 1)
        layout.addWidget(QLabel("Surgeries:"), 3, 0)
        layout.addWidget(self.surgeries, 3, 1)
        layout.addWidget(QLabel("Immunization:"), 4, 0)
        layout.addWidget(self.immunization, 4, 1)
        layout.addWidget(QLabel("Last Updated:"), 5, 0)
        layout.addWidget(self.last_updated, 5, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 6, 0, 1, 2)

        self.patient_id = patient_id
        self.setLayout(layout)

    def _on_submit(self) -> None:
        last_updated = self.last_updated.text().strip()
        if not last_updated:
            QMessageBox.warning(self, "Validation Error", "Last updated is required.")
            return
        iso_datetime = _locale_or_iso_to_iso_datetime(last_updated)
        if iso_datetime is None:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Last updated must match locale format ({LOCALE_DATETIME_FORMAT}) or ISO datetime format.",
            )
            return

        self.payload = {
            "patient_id": self.patient_id,
            "primary_condition": self.primary_condition.text().strip() or None,
            "chronicillnesses": self.chronicillnesses.text().strip() or None,
            "allergies": self.allergies.text().strip() or None,
            "surgeries": self.surgeries.text().strip() or None,
            "immunization": self.immunization.text().strip() or None,
            "last_updated": iso_datetime,
        }
        self.accept()


class FilterMedicalInformationDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filter Medical Information")
        self.payload: Optional[dict] = None

        layout = QGridLayout()
        self.primary_condition = QLineEdit()
        self.chronicillnesses = QLineEdit()
        self.allergies = QLineEdit()

        layout.addWidget(QLabel("Primary Condition:"), 0, 0)
        layout.addWidget(self.primary_condition, 0, 1)
        layout.addWidget(QLabel("Chronic Illnesses:"), 1, 0)
        layout.addWidget(self.chronicillnesses, 1, 1)
        layout.addWidget(QLabel("Allergies:"), 2, 0)
        layout.addWidget(self.allergies, 2, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 3, 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        self.payload = {
            "primary_condition": self.primary_condition.text().strip() or None,
            "chronicillnesses": self.chronicillnesses.text().strip() or None,
            "allergies": self.allergies.text().strip() or None,
        }
        self.accept()


class MedicalInformationWindow(QDialog):
    def __init__(self, api_client: ApiClient, patient: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.patient = patient
        self.all_records: List[dict] = []

        self.setWindowTitle("Medical Information")
        self.resize(900, 450)

        layout = QVBoxLayout()
        header = QLabel(
            f"Patient ID: {patient.get('id', '-')}  |  "
            f"{patient.get('first_name', '-')} {patient.get('last_name', '-')}"
        )
        layout.addWidget(header)
        self.records_table = QTableWidget(0, 4)
        self.records_table.setHorizontalHeaderLabels(["ID", "Primary Condition", "Allergies", "Last Updated"])
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setSelectionMode(QTableWidget.SingleSelection)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        self.records_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self._open_context_menu)
        header_widget = self.records_table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.records_table)

        top_controls = QHBoxLayout()
        top_controls.addStretch()
        create_button = QPushButton()
        _apply_create_icon(create_button)
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_records)
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_filter_dialog)
        top_controls.addWidget(create_button)
        top_controls.addWidget(refresh_button)
        top_controls.addWidget(filter_button)
        layout.addLayout(top_controls)

        controls = QHBoxLayout()
        controls.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

        self.setLayout(layout)
        self.refresh_records()

    def refresh_records(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected patient does not have a valid id.")
            return
        try:
            self.all_records = self.api_client.list_medicalinformation(patient_id=patient_id)
            self._render_records(self.all_records)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load medical information: {str(exc)}")

    def _render_records(self, records: List[dict]) -> None:
        self.records_table.clearContents()
        self.records_table.setRowCount(len(records))

        for row_index, record in enumerate(records):
            id_item = QTableWidgetItem(str(record.get("id", "-")))
            id_item.setData(Qt.ItemDataRole.UserRole, record)
            self.records_table.setItem(row_index, 0, id_item)
            self.records_table.setItem(row_index, 1, QTableWidgetItem(str(record.get("primary_condition") or "-")))
            self.records_table.setItem(row_index, 2, QTableWidgetItem(str(record.get("allergies") or "-")))
            self.records_table.setItem(row_index, 3, QTableWidgetItem(str(record.get("last_updated") or "-")))

    def _selected_record(self) -> Optional[dict]:
        row = self.records_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a medical information record first.")
            return None
        item = self.records_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected row does not contain a medical information record.")
            return None
        record = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(record, dict):
            QMessageBox.warning(self, "Warning", "Selected row does not contain a medical information record.")
            return None
        return record

    def _open_context_menu(self, pos) -> None:
        row = self.records_table.indexAt(pos).row()
        if row < 0:
            return
        self.records_table.setCurrentCell(row, 0)

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.records_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.delete_selected_record()

    def open_create_dialog(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Patient id is missing.")
            return
        dialog = MedicalInformationDialog("Create Medical Information", patient_id=patient_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_medicalinformation(dialog.payload)
                QMessageBox.information(self, "Success", "Medical information created successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        record = self._selected_record()
        if not record:
            return
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Patient id is missing.")
            return
        dialog = MedicalInformationDialog("Update Medical Information", patient_id=patient_id, record=record, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_medicalinformation(int(record["id"]), dialog.payload)
                QMessageBox.information(self, "Success", "Medical information updated successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_record(self) -> None:
        record = self._selected_record()
        if not record:
            return
        if QMessageBox.question(self, "Confirm Delete", f"Delete medical information ID {record.get('id', '-')}?") != QMessageBox.Yes:
            return
        try:
            self.api_client.delete_medicalinformation(int(record["id"]))
            QMessageBox.information(self, "Success", "Medical information deleted successfully.")
            self.refresh_records()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def _matches_filter(self, record: dict, criteria: dict) -> bool:
        def contains(value: str, query: str) -> bool:
            return query.lower() in (value or "").lower()

        if criteria.get("primary_condition") and not contains(record.get("primary_condition", ""), criteria["primary_condition"]):
            return False
        if criteria.get("chronicillnesses") and not contains(record.get("chronicillnesses", ""), criteria["chronicillnesses"]):
            return False
        if criteria.get("allergies") and not contains(record.get("allergies", ""), criteria["allergies"]):
            return False
        return True

    def open_filter_dialog(self) -> None:
        dialog = FilterMedicalInformationDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered = [record for record in self.all_records if self._matches_filter(record, dialog.payload)]
            self._render_records(filtered)


class MedicationDialog(QDialog):
    def __init__(self, title: str, patient_id: int, record: Optional[dict] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.payload: Optional[dict] = None
        record = record or {}

        layout = QGridLayout()
        self.drug_id = QLineEdit("" if record.get("drug_id") is None else str(record.get("drug_id")))
        self.dosage = QLineEdit(record.get("dosage", ""))
        self.frequency = QLineEdit(record.get("frequency", ""))
        self.route = QLineEdit(record.get("route", ""))
        self.start_date = QLineEdit(_iso_date_to_locale_text(record.get("start_date", "")))
        self.start_date.setPlaceholderText(LOCALE_DATE_FORMAT)
        self.end_date = QLineEdit(_iso_date_to_locale_text(record.get("end_date", "")))
        self.end_date.setPlaceholderText(f"{LOCALE_DATE_FORMAT} (optional)")
        self.notes = QLineEdit(record.get("notes", ""))

        layout.addWidget(QLabel("Drug ID:"), 0, 0)
        layout.addWidget(self.drug_id, 0, 1)
        layout.addWidget(QLabel("Dosage:"), 1, 0)
        layout.addWidget(self.dosage, 1, 1)
        layout.addWidget(QLabel("Frequency:"), 2, 0)
        layout.addWidget(self.frequency, 2, 1)
        layout.addWidget(QLabel("Route:"), 3, 0)
        layout.addWidget(self.route, 3, 1)
        layout.addWidget(QLabel("Start Date:"), 4, 0)
        layout.addWidget(self.start_date, 4, 1)
        layout.addWidget(QLabel("End Date:"), 5, 0)
        layout.addWidget(self.end_date, 5, 1)
        layout.addWidget(QLabel("Notes:"), 6, 0)
        layout.addWidget(self.notes, 6, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 7, 0, 1, 2)

        self.patient_id = patient_id
        self.setLayout(layout)

    def _on_submit(self) -> None:
        dosage = self.dosage.text().strip()
        frequency = self.frequency.text().strip()
        start_date = self.start_date.text().strip()

        if not dosage or not frequency or not start_date:
            QMessageBox.warning(self, "Validation Error", "Dosage, frequency and start date are required.")
            return

        start_date_iso = _locale_or_iso_to_iso_date(start_date)
        if start_date_iso is None:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Start date must match locale format ({LOCALE_DATE_FORMAT}) or ISO format (YYYY-MM-DD).",
            )
            return

        end_date = self.end_date.text().strip()
        if end_date:
            end_date_iso = _locale_or_iso_to_iso_date(end_date)
            if end_date_iso is None:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    f"End date must match locale format ({LOCALE_DATE_FORMAT}) or ISO format (YYYY-MM-DD).",
                )
                return
        else:
            end_date_iso = None

        drug_id_raw = self.drug_id.text().strip()
        if drug_id_raw and not drug_id_raw.isdigit():
            QMessageBox.warning(self, "Validation Error", "Drug ID must be numeric.")
            return

        self.payload = {
            "patient_id": self.patient_id,
            "drug_id": int(drug_id_raw) if drug_id_raw else None,
            "dosage": dosage,
            "frequency": frequency,
            "route": self.route.text().strip() or None,
            "start_date": start_date_iso,
            "end_date": end_date_iso,
            "notes": self.notes.text().strip() or None,
        }
        self.accept()


class FilterMedicationDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filter Medications")
        self.payload: Optional[dict] = None

        layout = QGridLayout()
        self.dosage = QLineEdit()
        self.frequency = QLineEdit()
        self.route = QLineEdit()

        layout.addWidget(QLabel("Dosage:"), 0, 0)
        layout.addWidget(self.dosage, 0, 1)
        layout.addWidget(QLabel("Frequency:"), 1, 0)
        layout.addWidget(self.frequency, 1, 1)
        layout.addWidget(QLabel("Route:"), 2, 0)
        layout.addWidget(self.route, 2, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons, 3, 0, 1, 2)

        self.setLayout(layout)

    def _on_submit(self) -> None:
        self.payload = {
            "dosage": self.dosage.text().strip() or None,
            "frequency": self.frequency.text().strip() or None,
            "route": self.route.text().strip() or None,
        }
        self.accept()


class MedicationsWindow(QDialog):
    def __init__(self, api_client: ApiClient, patient: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.patient = patient
        self.all_records: List[dict] = []

        self.setWindowTitle("Medications")
        self.resize(900, 450)

        layout = QVBoxLayout()
        header = QLabel(
            f"Patient ID: {patient.get('id', '-')}  |  "
            f"{patient.get('first_name', '-')} {patient.get('last_name', '-')}"
        )
        layout.addWidget(header)
        self.records_table = QTableWidget(0, 5)
        self.records_table.setHorizontalHeaderLabels(["ID", "Dosage", "Frequency", "Start Date", "End Date"])
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setSelectionMode(QTableWidget.SingleSelection)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        self.records_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self._open_context_menu)
        header_widget = self.records_table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.records_table)

        top_controls = QHBoxLayout()
        top_controls.addStretch()
        create_button = QPushButton()
        _apply_create_icon(create_button)
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_records)
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_filter_dialog)
        top_controls.addWidget(create_button)
        top_controls.addWidget(refresh_button)
        top_controls.addWidget(filter_button)
        layout.addLayout(top_controls)

        controls = QHBoxLayout()
        controls.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        controls.addWidget(close_button)
        layout.addLayout(controls)

        self.setLayout(layout)
        self.refresh_records()

    def refresh_records(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Selected patient does not have a valid id.")
            return
        try:
            self.all_records = self.api_client.list_medications(patient_id=patient_id)
            self._render_records(self.all_records)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load medications: {str(exc)}")

    def _render_records(self, records: List[dict]) -> None:
        self.records_table.clearContents()
        self.records_table.setRowCount(len(records))

        for row_index, record in enumerate(records):
            id_item = QTableWidgetItem(str(record.get("id", "-")))
            id_item.setData(Qt.ItemDataRole.UserRole, record)
            self.records_table.setItem(row_index, 0, id_item)
            self.records_table.setItem(row_index, 1, QTableWidgetItem(str(record.get("dosage") or "-")))
            self.records_table.setItem(row_index, 2, QTableWidgetItem(str(record.get("frequency") or "-")))
            self.records_table.setItem(row_index, 3, QTableWidgetItem(str(record.get("start_date") or "-")))
            self.records_table.setItem(row_index, 4, QTableWidgetItem(str(record.get("end_date") or "-")))

    def _selected_record(self) -> Optional[dict]:
        row = self.records_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a medication first.")
            return None
        item = self.records_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected row does not contain a medication.")
            return None
        record = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(record, dict):
            QMessageBox.warning(self, "Warning", "Selected row does not contain a medication.")
            return None
        return record

    def _open_context_menu(self, pos) -> None:
        row = self.records_table.indexAt(pos).row()
        if row < 0:
            return
        self.records_table.setCurrentCell(row, 0)

        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.records_table.viewport().mapToGlobal(pos))
        if selected_action == delete_action:
            self.delete_selected_record()

    def open_create_dialog(self) -> None:
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Patient id is missing.")
            return
        dialog = MedicationDialog("Create Medication", patient_id=patient_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_medication(dialog.payload)
                QMessageBox.information(self, "Success", "Medication created successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        record = self._selected_record()
        if not record:
            return
        patient_id = self.patient.get("id")
        if patient_id is None:
            QMessageBox.warning(self, "Warning", "Patient id is missing.")
            return
        dialog = MedicationDialog("Update Medication", patient_id=patient_id, record=record, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_medication(int(record["id"]), dialog.payload)
                QMessageBox.information(self, "Success", "Medication updated successfully.")
                self.refresh_records()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_record(self) -> None:
        record = self._selected_record()
        if not record:
            return
        if QMessageBox.question(self, "Confirm Delete", f"Delete medication ID {record.get('id', '-')}?") != QMessageBox.Yes:
            return
        try:
            self.api_client.delete_medication(int(record["id"]))
            QMessageBox.information(self, "Success", "Medication deleted successfully.")
            self.refresh_records()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def _matches_filter(self, record: dict, criteria: dict) -> bool:
        def contains(value: str, query: str) -> bool:
            return query.lower() in (value or "").lower()

        if criteria.get("dosage") and not contains(record.get("dosage", ""), criteria["dosage"]):
            return False
        if criteria.get("frequency") and not contains(record.get("frequency", ""), criteria["frequency"]):
            return False
        if criteria.get("route") and not contains(record.get("route", ""), criteria["route"]):
            return False
        return True

    def open_filter_dialog(self) -> None:
        dialog = FilterMedicationDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered = [record for record in self.all_records if self._matches_filter(record, dialog.payload)]
            self._render_records(filtered)


class PatientWindow(QMainWindow):
    def __init__(self, api_client: ApiClient) -> None:
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Patient Management")
        self.resize(900, 600)

        self.staff_id: Optional[int] = None
        self.all_patients: List[dict] = []
        self.patients: List[dict] = []
        self._staff_title_suffix: str = ""

        self._build_ui()
        self.refresh_patients()

    def _build_ui(self) -> None:
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        self.title_label = QLabel("Patient Management")
        title_font = self.title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        main_layout.addWidget(self.title_label)

        top_controls = QHBoxLayout()
        top_controls.addStretch()
        create_button = QPushButton()
        _apply_create_icon(create_button)
        create_button.setToolTip("Create")
        create_button.clicked.connect(self.open_create_dialog)
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_patients)
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self.open_filter_dialog)
        top_controls.addWidget(create_button)
        top_controls.addWidget(refresh_button)
        top_controls.addWidget(filter_button)
        main_layout.addLayout(top_controls)

        self.patient_table = QTableWidget(0, 5)
        self.patient_table.setHorizontalHeaderLabels(["ID", "First Name", "Last Name", "Mobile", "Email"])
        self.patient_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.patient_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patient_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patient_table.verticalHeader().setVisible(False)
        self.patient_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.patient_table.customContextMenuRequested.connect(self._open_context_menu)
        self.patient_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        header = self.patient_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        main_layout.addWidget(self.patient_table)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def _ensure_staff_id(self) -> bool:
        if self.staff_id is not None:
            return True
        try:
            me = self.api_client.get_me()
            staff = me.get("staff") or {}
            staff_id = staff.get("id")
            if staff_id is None:
                raise RuntimeError("Current user is not linked to a staff record.")
            self.staff_id = int(staff_id)
            position = str(staff.get("position", "") or "").strip()
            # capitilize first letter in position if it exists            
            if position:
                position = position[:1].upper() + position[1:]
            first_name = str(staff.get("first_name", "") or "").strip()
            last_name = str(staff.get("last_name", "") or "").strip()
            full_name = " ".join(part for part in [first_name, last_name] if part).strip()
            detail_parts = [part for part in [position, full_name] if part]
            self._staff_title_suffix = f" - {' | '.join(detail_parts)}" if detail_parts else ""
            self.title_label.setText(f"Patient Management{self._staff_title_suffix}")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to determine staff id: {str(exc)}")
            return False

    def refresh_patients(self) -> None:
        if not self._ensure_staff_id():
            return
        try:
            self.all_patients = self.api_client.list_patients(staff_id=self.staff_id)
            self._render_patients(self.all_patients)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load patients: {str(exc)}")

    def _render_patients(self, patients: List[dict]) -> None:
        self.patients = patients
        self.patient_table.clearContents()
        self.patient_table.setRowCount(len(patients))

        for row_index, patient in enumerate(patients):
            values = [
                str(patient.get("id", "-")),
                str(patient.get("first_name", "-") or "-"),
                str(patient.get("last_name", "-") or "-"),
                str(patient.get("mobile_phone", "-") or "-"),
                str(patient.get("email", "-") or "-"),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if col_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, patient)
                self.patient_table.setItem(row_index, col_index, item)

    def _get_selected_patient(self) -> Optional[dict]:
        row = self.patient_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a patient first.")
            return None
        item = self.patient_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected patient row is invalid.")
            return None
        patient = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(patient, dict):
            QMessageBox.warning(self, "Warning", "Selected row does not contain a patient.")
            return None
        return patient

    def _open_context_menu(self, pos) -> None:
        row = self.patient_table.indexAt(pos).row()
        if row < 0:
            return
        self.patient_table.setCurrentCell(row, 0)

        menu = QMenu(self)
        open_menu = QMenu("Open", menu)
        menu.addMenu(open_menu)
        appointments_action = open_menu.addAction("Appointments")
        labrecords_action = open_menu.addAction("Lab Records")
        medicalinformation_action = open_menu.addAction("Medical Information")
        medications_action = open_menu.addAction("Medications")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec_(self.patient_table.viewport().mapToGlobal(pos))
        if selected_action == appointments_action:
            self.open_appointments_window()
        elif selected_action == labrecords_action:
            self.open_labrecords_window()
        elif selected_action == medicalinformation_action:
            self.open_medicalinformation_window()
        elif selected_action == medications_action:
            self.open_medications_window()
        elif selected_action == delete_action:
            self.delete_selected_patient()

    def open_create_dialog(self) -> None:
        if not self._ensure_staff_id():
            return
        staff_id = self.staff_id
        if staff_id is None:
            return
        dialog = PatientDialog("Create Patient", staff_id=staff_id, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.create_patient(dialog.payload)
                QMessageBox.information(self, "Success", "Patient created successfully.")
                self.refresh_patients()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        if not self._ensure_staff_id():
            return
        staff_id = self.staff_id
        if staff_id is None:
            return
        patient = self._get_selected_patient()
        if not patient:
            return

        dialog = PatientDialog("Update Patient", staff_id=staff_id, patient=patient, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            try:
                self.api_client.update_patient(patient["id"], dialog.payload)
                QMessageBox.information(self, "Success", "Patient updated successfully.")
                self.refresh_patients()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_patient(self) -> None:
        patient = self._get_selected_patient()
        if not patient:
            return

        prompt = f"Delete patient {patient.get('first_name', '')} {patient.get('last_name', '')}?"
        if QMessageBox.question(self, "Confirm Delete", prompt) != QMessageBox.Yes:
            return

        try:
            self.api_client.delete_patient(patient["id"])
            QMessageBox.information(self, "Success", "Patient deleted successfully.")
            self.refresh_patients()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def open_appointments_window(self) -> None:
        patient = self._get_selected_patient()
        if not patient:
            return

        dialog = AppointmentsWindow(self.api_client, patient, self)
        dialog.exec_()

    def open_labrecords_window(self) -> None:
        patient = self._get_selected_patient()
        if not patient:
            return

        dialog = LabRecordsWindow(self.api_client, patient, self)
        dialog.exec_()

    def open_medicalinformation_window(self) -> None:
        patient = self._get_selected_patient()
        if not patient:
            return

        dialog = MedicalInformationWindow(self.api_client, patient, self)
        dialog.exec_()

    def open_medications_window(self) -> None:
        patient = self._get_selected_patient()
        if not patient:
            return

        dialog = MedicationsWindow(self.api_client, patient, self)
        dialog.exec_()

    def _matches_filter(self, patient: dict, criteria: dict) -> bool:
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

    def open_filter_dialog(self) -> None:
        dialog = FilterPatientsDialog(self)
        if dialog.exec_() == QDialog.Accepted and dialog.payload:
            filtered = [
                patient for patient in self.all_patients if self._matches_filter(patient, dialog.payload)
            ]
            self._render_patients(filtered)
