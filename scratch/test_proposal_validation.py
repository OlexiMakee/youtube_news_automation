import unittest
import tempfile
import json
from pathlib import Path
from scripts.memory.validate_memory import validate_proposals_file

class TestProposalValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_proposal(self):
        valid_row = {
            "id": 123456789,
            "ts": 123456789,
            "role": "admin",
            "type": "feature",
            "status": "active",
            "desc": "Valid proposal description",
            "workflow": "product",
            "role_tier": "admin",
            "priority": "high",
            "el": "some_element",
            "src": "some_source"
        }
        proposals_file = self.temp_path / "proposals.jsonl"
        with open(proposals_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_row) + "\n")

        errors = validate_proposals_file(proposals_file)
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {errors}")

    def test_missing_required_fields(self):
        invalid_row = {
            "id": 123456789,
            "ts": 123456789,
            "role": "admin",
            "type": "feature",
            "status": "active"
            # "desc" is missing
        }
        proposals_file = self.temp_path / "proposals.jsonl"
        with open(proposals_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(invalid_row) + "\n")

        errors = validate_proposals_file(proposals_file)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("missing required field 'desc'" in err for err in errors))

    def test_invalid_values(self):
        invalid_row = {
            "id": 123456789,
            "ts": 123456789,
            "role": "invalid_role",
            "type": "invalid_type",
            "status": "invalid_status",
            "desc": "" # empty
        }
        proposals_file = self.temp_path / "proposals.jsonl"
        with open(proposals_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(invalid_row) + "\n")

        errors = validate_proposals_file(proposals_file)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("invalid role" in err for err in errors))
        self.assertTrue(any("invalid type" in err for err in errors))
        self.assertTrue(any("invalid status" in err for err in errors))
        self.assertTrue(any("'desc' must be a non-empty string" in err for err in errors))

    def test_invalid_optional_values(self):
        invalid_row = {
            "id": 123456789,
            "ts": 123456789,
            "role": "admin",
            "type": "bug",
            "status": "active",
            "desc": "Valid description",
            "workflow": "invalid_workflow",
            "role_tier": "invalid_role_tier"
        }
        proposals_file = self.temp_path / "proposals.jsonl"
        with open(proposals_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(invalid_row) + "\n")

        errors = validate_proposals_file(proposals_file)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("invalid workflow" in err for err in errors))
        self.assertTrue(any("invalid role_tier" in err for err in errors))

    def test_invalid_json(self):
        proposals_file = self.temp_path / "proposals.jsonl"
        with open(proposals_file, "w", encoding="utf-8") as f:
            f.write("{invalid json}\n")

        errors = validate_proposals_file(proposals_file)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("invalid JSON" in err for err in errors))

if __name__ == "__main__":
    unittest.main()
