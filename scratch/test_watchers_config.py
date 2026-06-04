import os
import sys
import unittest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.governance import validate_watcher_config


class TestWatchersConfig(unittest.TestCase):

    def test_validate_valid_payload_defaults(self):
        payload = {
            "id": "watcher-1",
            "source_id": 42,
            "name": "Test Watcher",
            "interval_minutes": 30
        }
        res = validate_watcher_config(payload)
        self.assertEqual(res["id"], "watcher-1")
        self.assertEqual(res["source_id"], 42)
        self.assertEqual(res["name"], "Test Watcher")
        self.assertEqual(res["interval_minutes"], 30)
        self.assertFalse(res["enabled"])
        self.assertEqual(res["max_runs_per_day"], 24)
        self.assertEqual(res["cost_limit_usd"], 1.0)

    def test_validate_valid_payload_custom(self):
        payload = {
            "id": "watcher-custom",
            "source_id": "100",
            "name": "Custom Watcher",
            "interval_minutes": "45",
            "enabled": True,
            "max_runs_per_day": "48",
            "cost_limit_usd": "2.5"
        }
        res = validate_watcher_config(payload)
        self.assertEqual(res["id"], "watcher-custom")
        self.assertEqual(res["source_id"], 100)
        self.assertEqual(res["name"], "Custom Watcher")
        self.assertEqual(res["interval_minutes"], 45)
        self.assertTrue(res["enabled"])
        self.assertEqual(res["max_runs_per_day"], 48)
        self.assertEqual(res["cost_limit_usd"], 2.5)

    def test_validate_invalid_payload_type(self):
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config("not-a-dict")
        self.assertIn("must be a dictionary", str(ctx.exception))

    def test_validate_missing_id(self):
        payload = {"source_id": 1, "name": "Test", "interval_minutes": 30}
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config(payload)
        self.assertIn("id' is required", str(ctx.exception))

    def test_validate_invalid_source_id(self):
        # Missing
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config({"id": "w1", "name": "T", "interval_minutes": 30})
        self.assertIn("source_id' is required", str(ctx.exception))
        
        # Invalid format / value
        payloads = [
            {"id": "w1", "source_id": "not-int", "name": "T", "interval_minutes": 30},
            {"id": "w1", "source_id": -5, "name": "T", "interval_minutes": 30},
            {"id": "w1", "source_id": 0, "name": "T", "interval_minutes": 30}
        ]
        for p in payloads:
            with self.assertRaises(ValueError) as ctx:
                validate_watcher_config(p)
            self.assertIn("source_id' must be a positive integer", str(ctx.exception))

    def test_validate_missing_name(self):
        payload = {"id": "w1", "source_id": 1, "interval_minutes": 30}
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config(payload)
        self.assertIn("name' is required", str(ctx.exception))

    def test_validate_invalid_interval(self):
        # Missing
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config({"id": "w1", "source_id": 1, "name": "T"})
        self.assertIn("interval_minutes' is required", str(ctx.exception))
        
        # Less than 15 minutes (rate limit safety)
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config({"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 10})
        self.assertIn("must be at least 15 minutes", str(ctx.exception))
        
        # Non-integer
        with self.assertRaises(ValueError) as ctx:
            validate_watcher_config({"id": "w1", "source_id": 1, "name": "T", "interval_minutes": "abc"})
        self.assertIn("must be a valid integer", str(ctx.exception))

    def test_validate_invalid_max_runs(self):
        payloads = [
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "max_runs_per_day": 0},
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "max_runs_per_day": 100},
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "max_runs_per_day": "abc"}
        ]
        for p in payloads:
            with self.assertRaises(ValueError) as ctx:
                validate_watcher_config(p)
            self.assertIn("max_runs_per_day' must be an integer between 1 and 96", str(ctx.exception))

    def test_validate_invalid_cost_limit(self):
        payloads = [
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "cost_limit_usd": -1.0},
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "cost_limit_usd": 15.0},
            {"id": "w1", "source_id": 1, "name": "T", "interval_minutes": 30, "cost_limit_usd": "abc"}
        ]
        for p in payloads:
            with self.assertRaises(ValueError) as ctx:
                validate_watcher_config(p)
            self.assertIn("cost_limit_usd' must be a float between 0.0 and 10.0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
