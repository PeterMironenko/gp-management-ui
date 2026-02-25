from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QDate, QDateTime, QLocale, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDateEdit,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from apiclient import ApiClient
from patientwindow import AppointmentDialog
from patientwindow import PatientWindow


SYSTEM_LOCALE = QLocale.system()
LOCALE_DATETIME_FORMAT = SYSTEM_LOCALE.dateTimeFormat(QLocale.ShortFormat)


def _apply_refresh_icon(button: QPushButton) -> None:
    refresh_icon = QIcon.fromTheme("view-refresh")
    if not refresh_icon.isNull():
        button.setIcon(refresh_icon)
    else:
        button.setText("⟳")


def _parse_datetime(value: str) -> Optional[QDateTime]:
    if not value:
        return None
    for fmt in (
        "yyyy-MM-ddTHH:mm:ss",
        "yyyy-MM-ddTHH:mm",
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
    ):
        dt = QDateTime.fromString(value, fmt)
        if dt.isValid():
            return dt
    return None


class AppointmentsTab(QWidget):
    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.staff_id: Optional[int] = None
        self.all_appointments: List[dict] = []
        self.staff_patients: List[dict] = []
        self._staff_title_suffix: str = ""

        self._build_ui()
        self.refresh_today_appointments()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        self.title_label = QLabel("Appointments")
        title_font = self.title_label.font()
        title_font.setPointSize(13)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        top_controls = QHBoxLayout()
        top_controls.addWidget(QLabel("From:"))
        self.from_date_edit = QDateEdit()
        self.from_date_edit.setCalendarPopup(True)
        self.from_date_edit.setDate(QDate.currentDate())
        top_controls.addWidget(self.from_date_edit)

        top_controls.addWidget(QLabel("To:"))
        self.to_date_edit = QDateEdit()
        self.to_date_edit.setCalendarPopup(True)
        self.to_date_edit.setDate(QDate.currentDate())
        top_controls.addWidget(self.to_date_edit)

        query_button = QPushButton("Query")
        query_button.clicked.connect(self._apply_date_range_filter)
        top_controls.addWidget(query_button)

        top_controls.addStretch()
        refresh_button = QPushButton()
        _apply_refresh_icon(refresh_button)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_today_appointments)
        top_controls.addWidget(refresh_button)

        create_button = QPushButton("+")
        create_button.setToolTip("Create appointment")
        create_button.clicked.connect(self.open_create_dialog)
        top_controls.addWidget(create_button)
        layout.addLayout(top_controls)

        self.appointments_table = QTableWidget(0, 5)
        self.appointments_table.setHorizontalHeaderLabels(["ID", "Date & Time", "Patient", "Duration", "Reason"])
        self.appointments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.appointments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.appointments_table.setSelectionMode(QTableWidget.SingleSelection)
        self.appointments_table.verticalHeader().setVisible(False)
        self.appointments_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.appointments_table.customContextMenuRequested.connect(self._open_context_menu)
        self.appointments_table.cellDoubleClicked.connect(lambda _row, _col: self.open_update_dialog())
        header = self.appointments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.appointments_table)

        self.setLayout(layout)

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
            # capitalize first letter in position string if it's not empty
            if position:
                position = position[:1].upper() + position[1:]
            first_name = str(staff.get("first_name", "") or "").strip()
            last_name = str(staff.get("last_name", "") or "").strip()
            full_name = " ".join(part for part in [first_name, last_name] if part).strip()
            detail_parts = [part for part in [position, full_name] if part]
            self._staff_title_suffix = f" - {' | '.join(detail_parts)}" if detail_parts else ""
            self.title_label.setText(f"Appointments{self._staff_title_suffix}")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to determine staff id: {str(exc)}")
            return False

    def refresh_today_appointments(self) -> None:
        if not self._ensure_staff_id():
            return
        staff_id = self.staff_id
        if staff_id is None:
            return

        try:
            patients = self.api_client.list_patients(staff_id=staff_id)
            self.staff_patients = patients
            all_items: List[dict] = []

            for patient in patients:
                appointments = self.api_client.list_appointments(patient_id=patient.get("id"))
                for appointment in appointments:
                    dt = _parse_datetime(appointment.get("appointment_date", ""))
                    if dt is None:
                        continue

                    all_items.append(
                        {
                            "appointment": appointment,
                            "patient": patient,
                            "datetime": dt,
                        }
                    )

            all_items.sort(key=lambda item: item["datetime"])
            self.all_appointments = all_items
            self._apply_date_range_filter()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load appointments: {str(exc)}")

    def _selected_row_data(self) -> Optional[dict]:
        row = self.appointments_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select an appointment first.")
            return None
        item = self.appointments_table.item(row, 0)
        if item is None:
            QMessageBox.warning(self, "Warning", "Selected row is invalid.")
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

    def _choose_patient_for_create(self) -> Optional[dict]:
        if not self.staff_patients:
            QMessageBox.warning(self, "Warning", "No patients available for this staff member.")
            return None

        if len(self.staff_patients) == 1:
            return self.staff_patients[0]

        labels = [
            f"{patient.get('id', '-')}: {patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            for patient in self.staff_patients
        ]
        choice, ok = QInputDialog.getItem(self, "Select Patient", "Patient:", labels, 0, False)
        if not ok or not choice:
            return None

        selected_id_text = choice.split(":", 1)[0].strip()
        try:
            selected_id = int(selected_id_text)
        except ValueError:
            return None

        for patient in self.staff_patients:
            if int(patient.get("id", -1)) == selected_id:
                return patient
        return None

    def open_create_dialog(self) -> None:
        patient = self._choose_patient_for_create()
        if not patient:
            return

        patient_id = patient.get("id")
        staff_id = patient.get("staff_id") or self.staff_id
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return

        dialog = AppointmentDialog("Create Appointment", patient_id=int(patient_id), staff_id=int(staff_id), parent=self)
        if dialog.exec_() == dialog.Accepted and dialog.payload:
            try:
                self.api_client.create_appointment(dialog.payload)
                QMessageBox.information(self, "Success", "Appointment created successfully.")
                self.refresh_today_appointments()
            except Exception as exc:
                QMessageBox.critical(self, "Create Failed", str(exc))

    def open_update_dialog(self) -> None:
        selected = self._selected_row_data()
        if not selected:
            return

        appointment = selected["appointment"]
        patient = selected["patient"]
        patient_id = patient.get("id")
        staff_id = patient.get("staff_id") or appointment.get("staff_id")
        if patient_id is None or staff_id is None:
            QMessageBox.warning(self, "Warning", "Patient id or staff id is missing.")
            return

        dialog = AppointmentDialog(
            "Update Appointment",
            patient_id=int(patient_id),
            staff_id=int(staff_id),
            appointment=appointment,
            parent=self,
        )
        if dialog.exec_() == dialog.Accepted and dialog.payload:
            try:
                self.api_client.update_appointment(int(appointment["id"]), dialog.payload)
                QMessageBox.information(self, "Success", "Appointment updated successfully.")
                self.refresh_today_appointments()
            except Exception as exc:
                QMessageBox.critical(self, "Update Failed", str(exc))

    def delete_selected_appointment(self) -> None:
        selected = self._selected_row_data()
        if not selected:
            return

        appointment = selected["appointment"]
        appointment_id = appointment.get("id")
        if appointment_id is None:
            QMessageBox.warning(self, "Warning", "Selected appointment has no valid id.")
            return

        if QMessageBox.question(self, "Confirm Delete", f"Delete appointment ID {appointment_id}?") != QMessageBox.Yes:
            return

        try:
            self.api_client.delete_appointment(int(appointment_id))
            QMessageBox.information(self, "Success", "Appointment deleted successfully.")
            self.refresh_today_appointments()
        except Exception as exc:
            QMessageBox.critical(self, "Delete Failed", str(exc))

    def _apply_date_range_filter(self) -> None:
        from_date = self.from_date_edit.date()
        to_date = self.to_date_edit.date()

        if from_date > to_date:
            QMessageBox.warning(self, "Invalid Range", "From date must be earlier than or equal to To date.")
            return

        rows = [
            row
            for row in self.all_appointments
            if from_date <= row["datetime"].date() <= to_date
        ]
        self._render_appointments(rows, from_date, to_date)

    def _render_appointments(self, rows: List[dict], from_date: QDate, to_date: QDate) -> None:
        self.appointments_table.clearContents()
        self.appointments_table.clearSpans()
        self.appointments_table.setRowCount(0)

        if not rows:
            from_text = SYSTEM_LOCALE.toString(from_date, QLocale.ShortFormat)
            to_text = SYSTEM_LOCALE.toString(to_date, QLocale.ShortFormat)
            self.appointments_table.setRowCount(1)
            empty_item = QTableWidgetItem(f"No appointments between {from_text} and {to_text}.")
            empty_item.setFlags(Qt.ItemIsEnabled)
            self.appointments_table.setItem(0, 0, empty_item)
            self.appointments_table.setSpan(0, 0, 1, 5)
            return

        self.appointments_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            appointment = row["appointment"]
            patient = row["patient"]
            dt: QDateTime = row["datetime"]

            dt_text = SYSTEM_LOCALE.toString(dt, LOCALE_DATETIME_FORMAT)
            patient_name = f"{patient.get('first_name', '-')} {patient.get('last_name', '-')}"
            duration_text = str(appointment.get("duration_minutes", "-"))

            row_values = [
                str(appointment.get("id", "-")),
                dt_text,
                patient_name,
                duration_text,
                str(appointment.get("reason", "-") or "-"),
            ]
            for col, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.appointments_table.setItem(index, col, item)


class StaffDashboardWindow(QMainWindow):
    def __init__(self, api_client: ApiClient) -> None:
        super().__init__()
        self.api_client = api_client
        self.setWindowTitle("Staff Dashboard")
        self.resize(1100, 700)

        tabs = QTabWidget(self)

        self.today_tab = AppointmentsTab(api_client, self)
        tabs.addTab(self.today_tab, "Appointments")

        self.patient_window = PatientWindow(api_client)
        patient_tab = self.patient_window.takeCentralWidget()
        if patient_tab is None:
            patient_tab = QWidget()
        tabs.addTab(patient_tab, "Patients")

        self.setCentralWidget(tabs)
