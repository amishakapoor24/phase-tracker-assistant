import unittest
from unittest.mock import patch

from services import role_context_service


class FakeCollection:
    def __init__(self, records=None):
        self.records = records or []

    def find_one(self, query, projection=None):
        for item in self.records:
            if query.get("_id") == item.get("_id"):
                return item
            if query.get("email") == item.get("email"):
                return item
        return None

    def find(self, *args, **kwargs):
        return FakeCursor(self.records)

    def count_documents(self, *args, **kwargs):
        return 0


class FakeDB:
    def __init__(self):
        self.users = FakeCollection([
            {"_id": "student-1", "name": "Alice Student", "email": "alice@test.com", "role": "student", "house": "A"}
        ])
        self.progresses = FakeCollection([])
        self.approvalrequests = FakeCollection([])
        self.phases = FakeCollection([])
        self.houses = FakeCollection([])
        self.auditlogs = FakeCollection([])


class FakeCursor:
    def __init__(self, records):
        self.records = list(records)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.records)

    def __len__(self):
        return len(self.records)

    def __bool__(self):
        return bool(self.records)


class RoleSecurityTests(unittest.TestCase):
    def test_forged_admin_role_is_rejected(self):
        fake_db = FakeDB()
        forged_user = {"_id": "student-1", "email": "alice@test.com", "role": "admin", "name": "Alice Student"}

        with patch.object(role_context_service, "_get_database", return_value=fake_db):
            context = role_context_service.build_role_context(forged_user)

        self.assertIn("Student personal context", context)
        self.assertNotIn("Admin platform context", context)


if __name__ == "__main__":
    unittest.main()
