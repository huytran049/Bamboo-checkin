import os
import tempfile
import unittest

from database import update_database as db


class TestAppointmentsSmoke(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(prefix="appt_smoke_", suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        db.setup_database(self.db_path)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def test_create_list_delete_ok(self):
        item = db.create_appointment(
            appointment_date="2099-01-01",
            start_time="10:00",
            end_time="10:30",
            contact_name="Nguyen Van A",
            appointment_reason="Demo",
            description="Ghi chu",
            source="kiosk",
            status="pending",
            assignee="Admin",
            created_by="Admin",
            updated_by="Admin",
            db_path=self.db_path,
        )
        self.assertIsInstance(item, dict)
        self.assertTrue(item.get("id"))
        self.assertEqual(item.get("appointment_date"), "2099-01-01")

        items = db.list_appointments_for_date("2099-01-01", db_path=self.db_path)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("id"), item.get("id"))

        deleted = db.delete_appointment(int(item["id"]), db_path=self.db_path)
        self.assertTrue(deleted)
        items = db.list_appointments_for_date("2099-01-01", db_path=self.db_path)
        self.assertEqual(len(items), 0)

    def test_missing_reason_and_description_rejected(self):
        with self.assertRaises(ValueError):
            db.create_appointment(
                appointment_date="2099-01-01",
                start_time="10:00",
                end_time="10:10",
                contact_name="Nguyen Van A",
                appointment_reason="",
                description="",
                source="kiosk",
                status="pending",
                db_path=self.db_path,
            )

    def test_past_date_rejected(self):
        with self.assertRaises(ValueError):
            db.create_appointment(
                appointment_date="2000-01-01",
                start_time="10:00",
                end_time="10:10",
                contact_name="Nguyen Van A",
                appointment_reason="Demo",
                description="",
                source="kiosk",
                status="pending",
                db_path=self.db_path,
            )

    def test_conflict_time_rejected(self):
        db.create_appointment(
            appointment_date="2099-01-01",
            start_time="10:00",
            end_time="10:30",
            contact_name="Nguyen Van A",
            appointment_reason="Demo",
            description="",
            source="kiosk",
            status="pending",
            db_path=self.db_path,
        )
        with self.assertRaises(ValueError):
            db.create_appointment(
                appointment_date="2099-01-01",
                start_time="10:20",
                end_time="10:40",
                contact_name="Nguyen Van B",
                appointment_reason="Demo",
                description="",
                source="kiosk",
                status="pending",
                db_path=self.db_path,
            )

    def test_update_to_confirmed_sets_confirmed_fields(self):
        item = db.create_appointment(
            appointment_date="2099-01-01",
            start_time="10:00",
            end_time="10:20",
            contact_name="Nguyen Van A",
            appointment_reason="Demo",
            description="",
            source="dashboard",
            status="pending",
            created_by="Admin",
            updated_by="Admin",
            db_path=self.db_path,
        )
        updated = db.update_appointment(
            int(item["id"]),
            {"status": "confirmed", "updated_by": "Admin"},
            db_path=self.db_path,
        )
        self.assertEqual(updated.get("status"), "confirmed")
        self.assertTrue(str(updated.get("confirmed_at") or "").strip())
        self.assertTrue(str(updated.get("confirmed_by") or "").strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)

