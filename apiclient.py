"""HTTP API client used by the gp-management-ui desktop application.

This module provides a thin wrapper around backend REST endpoints and
normalizes error handling for UI workflows.
"""

import requests
import jwt
from typing import List


class ApiClient:
    """Client for authentication and CRUD operations against the GP backend API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        """Initialize the API client.

        Args:
            base_url: Backend API base URL.
        """
        self.base_url = base_url.rstrip("/")
        self.access_token: str = ""
        self.is_admin: bool = False
        self.user_id: int | None = None

    def _headers(self, needs_auth: bool = False) -> dict:
        """Build request headers.

        Args:
            needs_auth: Whether to include the bearer token.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {"Content-Type": "application/json"}
        if needs_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    @staticmethod
    def _clean_optional_fields(data: dict | None) -> dict:
        """Remove empty or null optional fields from a payload.

        Args:
            data: Raw payload dictionary.

        Returns:
            Sanitized payload dictionary.
        """
        if not data:
            return {}
        return {
            key: value
            for key, value in data.items()
            if value is not None and (not isinstance(value, str) or len(value.strip()) > 0)
        }

    # --- Auth ---
    def register(self, username: str, password: str) -> None:
        """Register a new user account.

        Args:
            username: New username.
            password: New password.

        Raises:
            RuntimeError: If registration fails.
        """
        url = f"{self.base_url}/register"
        resp = requests.post(
            url,
            json={"username": username, "password": password},
            headers=self._headers(),
        )
        if resp.status_code not in (200, 201):
            message = None
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                message = resp.json().get("message")
            raise RuntimeError(message or f"Registration failed: {resp.status_code}")

    def login(self, username: str, password: str) -> None:
        """Authenticate the user and cache token-derived identity metadata.

        Args:
            username: Account username.
            password: Account password.

        Raises:
            RuntimeError: If login fails or token is missing.
        """
        url = f"{self.base_url}/login"
        print("headers:", self._headers())
        resp = requests.post(url, json={"username": username, "password": password}, headers=self._headers())
        if resp.status_code != 200:
            raise RuntimeError(resp.json().get("message", f"Login failed: {resp.status_code}"))
        data = resp.json()
        self.access_token = data.get("access_token")
        payload = jwt.decode(self.access_token, options={"verify_signature": False})
        self.is_admin = payload.get("is_admin", False)
        sub = payload.get("sub")
        try:
            self.user_id = int(sub) if sub is not None else None
        except (TypeError, ValueError):
            self.user_id = None

        print("Access token received:", self.access_token)
        if  len(self.access_token) == 0:
            raise RuntimeError("No access token received from server.")

    # --- User management ---
    def list_positions(self) -> List[dict]:
        """Fetch available staff positions."""
        url = f"{self.base_url}/position"
        resp = requests.get(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load positions: {resp.status_code}")
        return resp.json()

    def list_users(self) -> List[dict]:
        """Fetch all users."""
        url = f"{self.base_url}/user"
        resp = requests.get(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load users: {resp.status_code}")
        return resp.json()

    def get_user(self, user_id: int) -> dict:
        """Fetch a single user by id."""
        url = f"{self.base_url}/user/{user_id}"
        resp = requests.get(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to get user: {resp.status_code}")
        return resp.json()

    def get_me(self) -> dict:
        """Fetch the currently authenticated user profile."""
        url = f"{self.base_url}/me"
        resp = requests.get(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to get current user: {resp.status_code}")
        return resp.json()

    def get_current_staff_id(self) -> int:
        """Return current user's linked staff id.

        Raises:
            RuntimeError: If user is not linked to a staff record.
        """
        user = self.get_me()
        staff = user.get("staff") or {}
        staff_id = staff.get("id")
        if staff_id is None:
            raise RuntimeError("Current user is not linked to a staff record.")
        return int(staff_id)

    # --- Patient management ---
    def list_patients(self, staff_id: int | None = None) -> List[dict]:
        """Fetch patients, optionally scoped by staff id."""
        url = f"{self.base_url}/patient"
        params = {"staff_id": staff_id} if staff_id is not None else None
        resp = requests.get(url, headers=self._headers(needs_auth=True), params=params)
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load patients: {resp.status_code}")
        return resp.json()

    def create_patient(self, patient_data: dict) -> dict:
        """Create a new patient record."""
        url = f"{self.base_url}/patient"
        payload = self._clean_optional_fields(patient_data)
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create patient: {resp.status_code}")
        return resp.json()

    def update_patient(self, patient_id: int, patient_data: dict) -> dict:
        """Update an existing patient record."""
        url = f"{self.base_url}/patient/{patient_id}"
        payload = self._clean_optional_fields(patient_data)
        if "staff_id" in patient_data and patient_data.get("staff_id") is None:
            payload["staff_id"] = None
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update patient: {resp.status_code}")
        return resp.json()

    def delete_patient(self, patient_id: int) -> None:
        """Delete a patient by id."""
        url = f"{self.base_url}/patient/{patient_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete patient: {resp.status_code}")

    def list_appointments(self, patient_id: int | None = None) -> List[dict]:
        """Fetch appointments, optionally filtered by patient id."""
        url = f"{self.base_url}/appointment"
        params = {"patient_id": patient_id} if patient_id is not None else None
        resp = requests.get(url, headers=self._headers(needs_auth=True), params=params)
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load appointments: {resp.status_code}")
        return resp.json()

    def create_appointment(self, appointment_data: dict) -> dict:
        """Create an appointment."""
        url = f"{self.base_url}/appointment"
        payload = self._clean_optional_fields(appointment_data)
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create appointment: {resp.status_code}")
        return resp.json()

    def update_appointment(self, appointment_id: int, appointment_data: dict) -> dict:
        """Update an appointment."""
        url = f"{self.base_url}/appointment/{appointment_id}"
        payload = self._clean_optional_fields(appointment_data)
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update appointment: {resp.status_code}")
        return resp.json()

    def delete_appointment(self, appointment_id: int) -> None:
        """Delete an appointment by id."""
        url = f"{self.base_url}/appointment/{appointment_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete appointment: {resp.status_code}")

    # --- Drug management ---
    def list_drugs(self) -> List[dict]:
        """Fetch all drugs."""
        url = f"{self.base_url}/drug"
        resp = requests.get(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load drugs: {resp.status_code}")
        return resp.json()

    def create_drug(self, drug_data: dict) -> dict:
        """Create a drug record."""
        url = f"{self.base_url}/drug"
        payload = self._clean_optional_fields(drug_data)
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create drug: {resp.status_code}")
        return resp.json()

    def update_drug(self, drug_id: int, drug_data: dict) -> dict:
        """Update a drug record."""
        url = f"{self.base_url}/drug/{drug_id}"
        payload = self._clean_optional_fields(drug_data)
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update drug: {resp.status_code}")
        return resp.json()

    def delete_drug(self, drug_id: int) -> None:
        """Delete a drug record by id."""
        url = f"{self.base_url}/drug/{drug_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete drug: {resp.status_code}")

    # --- Lab record management ---
    def list_labrecords(self, patient_id: int | None = None) -> List[dict]:
        """Fetch lab records, optionally filtered by patient id."""
        url = f"{self.base_url}/labrecord"
        params = {"patient_id": patient_id} if patient_id is not None else None
        resp = requests.get(url, headers=self._headers(needs_auth=True), params=params)
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load lab records: {resp.status_code}")
        return resp.json()

    def create_labrecord(self, labrecord_data: dict) -> dict:
        """Create a lab record."""
        url = f"{self.base_url}/labrecord"
        payload = self._clean_optional_fields(labrecord_data)
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create lab record: {resp.status_code}")
        return resp.json()

    def update_labrecord(self, labrecord_id: int, labrecord_data: dict) -> dict:
        """Update a lab record."""
        url = f"{self.base_url}/labrecord/{labrecord_id}"
        payload = self._clean_optional_fields(labrecord_data)
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update lab record: {resp.status_code}")
        return resp.json()

    def delete_labrecord(self, labrecord_id: int) -> None:
        """Delete a lab record by id."""
        url = f"{self.base_url}/labrecord/{labrecord_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete lab record: {resp.status_code}")

    # --- Medical information management ---
    def list_medicalinformation(self, patient_id: int | None = None) -> List[dict]:
        """Fetch medical information records, optionally filtered by patient id."""
        url = f"{self.base_url}/medicalinformation"
        params = {"patient_id": patient_id} if patient_id is not None else None
        resp = requests.get(url, headers=self._headers(needs_auth=True), params=params)
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load medical information: {resp.status_code}")
        return resp.json()

    def create_medicalinformation(self, medicalinformation_data: dict) -> dict:
        """Create a medical information record."""
        url = f"{self.base_url}/medicalinformation"
        payload = self._clean_optional_fields(medicalinformation_data)
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create medical information: {resp.status_code}")
        return resp.json()

    def update_medicalinformation(self, medicalinformation_id: int, medicalinformation_data: dict) -> dict:
        """Update a medical information record."""
        url = f"{self.base_url}/medicalinformation/{medicalinformation_id}"
        payload = self._clean_optional_fields(medicalinformation_data)
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update medical information: {resp.status_code}")
        return resp.json()

    def delete_medicalinformation(self, medicalinformation_id: int) -> None:
        """Delete a medical information record by id."""
        url = f"{self.base_url}/medicalinformation/{medicalinformation_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete medical information: {resp.status_code}")

    # --- Medication management ---
    def list_medications(self, patient_id: int | None = None) -> List[dict]:
        """Fetch medications, optionally filtered by patient id."""
        url = f"{self.base_url}/medication"
        params = {"patient_id": patient_id} if patient_id is not None else None
        resp = requests.get(url, headers=self._headers(needs_auth=True), params=params)
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to load medications: {resp.status_code}")
        return resp.json()

    def create_medication(self, medication_data: dict) -> dict:
        """Create a medication record."""
        url = f"{self.base_url}/medication"
        payload = self._clean_optional_fields(medication_data)
        if "staff_id" in medication_data and medication_data.get("staff_id") is None:
            payload["staff_id"] = None
        if "is_approved" in medication_data and medication_data.get("is_approved") is None:
            payload["is_approved"] = None
        resp = requests.post(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create medication: {resp.status_code}")
        return resp.json()

    def update_medication(self, medication_id: int, medication_data: dict) -> dict:
        """Update a medication record."""
        url = f"{self.base_url}/medication/{medication_id}"
        payload = self._clean_optional_fields(medication_data)
        if "staff_id" in medication_data and medication_data.get("staff_id") is None:
            payload["staff_id"] = None
        if "is_approved" in medication_data and medication_data.get("is_approved") is None:
            payload["is_approved"] = None
        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update medication: {resp.status_code}")
        return resp.json()

    def delete_medication(self, medication_id: int) -> None:
        """Delete a medication record by id."""
        url = f"{self.base_url}/medication/{medication_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete medication: {resp.status_code}")

    def delete_user(self, user_id: int) -> None:
        """Delete a user by id."""
        url = f"{self.base_url}/user/{user_id}"
        resp = requests.delete(url, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to delete user: {resp.status_code}")
    
    def create_user(self, username: str, password: str, staff_data: dict | None = None) -> dict:
        """Create a user, optionally with linked staff profile fields."""
        url = f"{self.base_url}/register"
        payload = {"username": username, "password": password}
        payload.update(self._clean_optional_fields(staff_data))
        resp = requests.post(url, json=payload, headers=self._headers())
        if resp.status_code not in (200, 201):
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to create user: {resp.status_code}")
        return resp.json()

    def update_user(self, user_id: int, username: str | None = None, password: str | None = None, staff_data: dict | None = None) -> dict:
        """Update user credentials/profile fields."""
        url = f"{self.base_url}/user/{user_id}"
        payload: dict = {}
        if username is not None and len(username.strip()) > 0:
            payload["username"] = username
        if password is not None and len(password.strip()) > 0:
            payload["password"] = password
        payload.update(self._clean_optional_fields(staff_data))

        resp = requests.put(url, json=payload, headers=self._headers(needs_auth=True))
        if resp.status_code != 200:
            message = resp.json().get("message") if resp.headers.get("Content-Type", "").startswith("application/json") else None
            raise RuntimeError(message or f"Failed to update user: {resp.status_code}")
        return resp.json()

