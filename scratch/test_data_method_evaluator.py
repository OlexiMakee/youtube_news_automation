import json
import os
import tempfile
import unittest

from click.testing import CliRunner

from scripts.analytics.cli import cli
from scripts.analytics.data_method_evaluator import (
    analyze_log,
    append_experiment,
    make_experiment,
    rank_methods,
    to_markdown,
    write_review_snapshot,
)


class TestDataMethodEvaluator(unittest.TestCase):
    def setUp(self):
        fd, self.log_path = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self.log_path)

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.unlink(self.log_path)

    def test_make_experiment_blocks_tier_x(self):
        with self.assertRaises(ValueError):
            make_experiment(
                method_id="blocked",
                source_type="private",
                dataset="forbidden",
                policy_tier="X",
                status="success",
            )

    def test_rank_methods_promotes_reliable_method(self):
        rows = []
        for _ in range(5):
            rows.append(
                make_experiment(
                    method_id="rss_stdlib",
                    source_type="rss",
                    dataset="feed",
                    policy_tier="C",
                    status="success",
                    records_seen=100,
                    records_read=95,
                    duration_ms=1000,
                    error_count=0,
                    bytes_read=5000,
                )
            )
        rows.append(
            make_experiment(
                method_id="html_probe",
                source_type="html",
                dataset="page",
                policy_tier="E",
                status="failed",
                records_seen=100,
                records_read=0,
                duration_ms=5000,
                error_count=3,
            )
        )

        ranked = rank_methods(rows)

        self.assertEqual(ranked[0].method_id, "rss_stdlib")
        self.assertEqual(ranked[0].recommendation, "promote_to_reusable_function")
        self.assertEqual(ranked[-1].method_id, "html_probe")

    def test_log_analyze_and_markdown(self):
        append_experiment(
            make_experiment(
                method_id="manual_csv",
                source_type="csv",
                dataset="upload",
                policy_tier="C",
                status="partial",
                records_seen=10,
                records_read=8,
                duration_ms=500,
                error_count=1,
            ),
            log_path=self.log_path,
        )

        report = analyze_log(self.log_path)

        self.assertEqual(report["total_runs"], 1)
        self.assertEqual(report["ranked_methods"][0]["method_id"], "manual_csv")
        self.assertIn("Data Access Method Ranking", to_markdown(report))

        output_fd, output_path = tempfile.mkstemp()
        os.close(output_fd)
        os.unlink(output_path)
        try:
            write_review_snapshot(report, output_path=output_path)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(data["ranked_methods"][0]["method_id"], "manual_csv")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_cli_log_and_rank(self):
        runner = CliRunner()
        log_result = runner.invoke(
            cli,
            [
                "method-log",
                "--method-id", "rss_stdlib",
                "--source-type", "rss",
                "--dataset", "feed",
                "--policy-tier", "C",
                "--status", "success",
                "--records-seen", "12",
                "--records-read", "12",
                "--duration-ms", "300",
                "--log-path", self.log_path,
            ],
        )
        self.assertEqual(log_result.exit_code, 0)

        rank_result = runner.invoke(cli, ["method-rank", "--log-path", self.log_path])
        self.assertEqual(rank_result.exit_code, 0)
        data = json.loads(rank_result.output)
        self.assertEqual(data["ranked_methods"][0]["method_id"], "rss_stdlib")

    def test_cli_method_review_writes_snapshot(self):
        runner = CliRunner()
        output_fd, output_path = tempfile.mkstemp()
        os.close(output_fd)
        os.unlink(output_path)
        try:
            append_experiment(
                make_experiment(
                    method_id="rss_stdlib",
                    source_type="rss",
                    dataset="feed",
                    policy_tier="C",
                    status="success",
                    records_seen=12,
                    records_read=12,
                    duration_ms=300,
                ),
                log_path=self.log_path,
            )
            result = runner.invoke(
                cli,
                [
                    "method-review",
                    "--log-path", self.log_path,
                    "--output-path", output_path,
                ],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(os.path.exists(output_path))
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":
    unittest.main()
