import json
import os
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from scripts.analytics.cli import cli
from scripts.analytics.method_review_proposals import (
    append_lifecycle_event,
    build_proposal_candidates,
    generate_method_review_proposals,
)


class TestMethodReviewProposals(unittest.TestCase):
    def test_build_candidates_filters_to_repeated_actionable_methods(self):
        review = {
            "ranked_methods": [
                {
                    "method_id": "rss_stdlib",
                    "source_type": "rss",
                    "runs": 5,
                    "recommendation": "promote_to_reusable_function",
                    "success_rate": 1.0,
                    "avg_error_count": 0,
                    "score": 3.2,
                },
                {
                    "method_id": "html_probe",
                    "source_type": "html",
                    "runs": 2,
                    "recommendation": "investigate_or_retire",
                    "success_rate": 0.0,
                    "avg_error_count": 4,
                    "score": 0.0,
                },
            ]
        }

        candidates = build_proposal_candidates(review, min_runs_for_proposal=3)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].proposal_type, "feature")
        self.assertIn("rss_stdlib", candidates[0].proposal_key)

    def test_generate_dry_run_does_not_write_proposals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "review.json"
            proposals = root / "agent_proposals" / "admin_proposals.jsonl"
            snapshot.write_text(json.dumps(_review_payload()), encoding="utf-8")

            result = generate_method_review_proposals(
                snapshot_path=str(snapshot),
                proposals_path=str(proposals),
                write=False,
            )

            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["created_count"], 0)
            self.assertFalse(proposals.exists())

    def test_generate_write_dedupes_existing_proposals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "review.json"
            proposals = root / "agent_proposals" / "admin_proposals.jsonl"
            snapshot.write_text(json.dumps(_review_payload()), encoding="utf-8")

            first = generate_method_review_proposals(
                snapshot_path=str(snapshot),
                proposals_path=str(proposals),
                write=True,
            )
            second = generate_method_review_proposals(
                snapshot_path=str(snapshot),
                proposals_path=str(proposals),
                write=True,
            )

            self.assertEqual(first["created_count"], 1)
            self.assertEqual(second["created_count"], 0)
            self.assertEqual(second["skipped_existing_count"], 1)
            rows = proposals.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rows), 1)

    def test_lifecycle_event_shape_matches_memory_validator_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "memory" / "events.jsonl"

            event = append_lifecycle_event(
                str(events),
                created_count=2,
                snapshot_path="data/data_access_method_review.json",
                proposals_path="agent_proposals/admin_proposals.jsonl",
            )

            self.assertEqual(event["status"], "accepted")
            row = json.loads(events.read_text(encoding="utf-8"))
            for field in ["timestamp", "event", "node_id", "claim", "validator", "status"]:
                self.assertIn(field, row)

    def test_cli_method_proposals_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "review.json"
            proposals = root / "proposals.jsonl"
            snapshot.write_text(json.dumps(_review_payload()), encoding="utf-8")
            runner = CliRunner()

            result = runner.invoke(
                cli,
                [
                    "method-proposals",
                    "--snapshot-path",
                    str(snapshot),
                    "--proposals-path",
                    str(proposals),
                ],
            )

            self.assertEqual(result.exit_code, 0)
            payload = json.loads(result.output)
            self.assertEqual(payload["candidate_count"], 1)
            self.assertFalse(proposals.exists())


def _review_payload():
    return {
        "ranked_methods": [
            {
                "method_id": "rss_stdlib",
                "source_type": "rss",
                "runs": 5,
                "recommendation": "promote_to_reusable_function",
                "success_rate": 1.0,
                "avg_error_count": 0,
                "score": 3.2,
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
