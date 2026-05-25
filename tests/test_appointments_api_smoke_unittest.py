import os
import tempfile
import unittest
from unittest.mock import patch

from application import app
from database import update_database as db


class TestAppointmentsApiSmoke(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(prefix="appt_api_smoke_", suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        self.db_path_patcher = patch("database.update_database.get_db_path", return_value=self.db_path)
        self.db_path_patcher.start()
        db.setup_database(self.db_path)

        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["user"] = {
                "id": 1,
                "username": "admin",
                "display_name": "Administrator",
                "role": "admin",
            }

    def tearDown(self):
        self.db_path_patcher.stop()
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def _create_appointment(self, **overrides):
        payload = {
            "appointment_date": "2099-01-01",
            "start_time": "10:00",
            "end_time": "10:30",
            "contact_name": "Nguyen Van A",
            "appointment_reason": "Demo Bamboo",
            "description": "Ghi chu",
            "source": "dashboard",
            "status": "pending",
            "assignee": "Admin",
        }
        payload.update(overrides)
        return self.client.post("/api/dashboard/appointments", json=payload)

    def test_month_endpoint_requires_login(self):
        anon_client = app.test_client()
        response = anon_client.get("/api/dashboard/appointments/month?year=2099&month=1")
        self.assertEqual(response.status_code, 401)

    def test_create_list_update_delete_flow(self):
        create_response = self._create_appointment()
        self.assertEqual(create_response.status_code, 201)
        create_payload = create_response.get_json()
        self.assertTrue(create_payload["ok"])
        appointment_id = int(create_payload["item"]["id"])

        month_response = self.client.get("/api/dashboard/appointments/month?year=2099&month=1")
        self.assertEqual(month_response.status_code, 200)
        month_payload = month_response.get_json()
        self.assertEqual(len(month_payload["items"]), 1)

        day_response = self.client.get("/api/dashboard/appointments/day?date=2099-01-01")
        self.assertEqual(day_response.status_code, 200)
        day_payload = day_response.get_json()
        self.assertEqual(len(day_payload["items"]), 1)

        update_response = self.client.put(
            f"/api/dashboard/appointments/{appointment_id}",
            json={"status": "confirmed", "assignee": "Manager"},
        )
        self.assertEqual(update_response.status_code, 200)
        update_payload = update_response.get_json()
        self.assertEqual(update_payload["item"]["status"], "confirmed")
        self.assertEqual(update_payload["item"]["assignee"], "Manager")
        self.assertTrue(str(update_payload["item"].get("confirmed_at") or "").strip())

        delete_response = self.client.delete(f"/api/dashboard/appointments/{appointment_id}")
        self.assertEqual(delete_response.status_code, 200)
        delete_payload = delete_response.get_json()
        self.assertTrue(delete_payload["ok"])

        month_after_delete = self.client.get("/api/dashboard/appointments/month?year=2099&month=1")
        self.assertEqual(len(month_after_delete.get_json()["items"]), 0)

    def test_create_missing_required_content_returns_400(self):
        response = self._create_appointment(appointment_reason="", description="")
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])

    def test_create_conflict_returns_400(self):
        first = self._create_appointment()
        self.assertEqual(first.status_code, 201)

        second = self._create_appointment(
            contact_name="Nguyen Van B",
            start_time="10:20",
            end_time="10:40",
        )
        self.assertEqual(second.status_code, 400)
        payload = second.get_json()
        self.assertIn("Khung giờ đã có lịch hẹn", payload["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
