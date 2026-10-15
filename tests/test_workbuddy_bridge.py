import importlib.util
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "workbuddy_bridge.py"
SPEC = importlib.util.spec_from_file_location("workbuddy_bridge", MODULE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


def sample_job():
    return {
        "schema_version": "1.0",
        "job_id": "A01-123456-20261015-abc123",
        "candidate_id": "A01",
        "supplier_url": "https://detail.1688.com/offer/123456.html",
        "canonical_offer_url": "https://detail.1688.com/offer/123456.html",
        "offer_id": "123456",
        "custom_item_prefix": "CS",
    }


def sample_result():
    job = sample_job()
    return {
        **job,
        "title": "测试商品",
        "status": "complete",
        "access_mode": "authenticated",
        "variant_axes": [{"name": "颜色", "values": ["黑色"]}],
        "skus": [
            {
                "sku_display_key": "黑色",
                "supplier_sku_code": None,
                "selected_options": [{"axis": "颜色", "label": "黑色"}],
                "purchasable": True,
                "stock_state": "in_stock",
                "price_tiers": [
                    {
                        "min_qty": 10,
                        "max_qty": None,
                        "unit_price_cny": 12.5,
                        "unit": "件",
                        "raw_text": "10件起 ¥12.50",
                    }
                ],
                "executable_tier": {
                    "min_qty": 10,
                    "max_qty": None,
                    "unit_price_cny": 12.5,
                    "unit": "件",
                    "raw_text": "10件起 ¥12.50",
                },
                "mandatory_charge_cny": 1.0,
                "measurement": {
                    "gross_weight_g": 420,
                    "length_mm": 300,
                    "width_mm": 200,
                    "height_mm": 80,
                    "scope": "single_unit_packed",
                    "source_type": "detail_image",
                    "source_location": "详情图包装参数",
                    "raw_text": "单件包装30×20×8cm，毛重0.42kg",
                    "confidence": "high",
                },
                "evidence": [
                    {
                        "field": "measurement",
                        "source_type": "detail_image",
                        "source_location": "详情图包装参数",
                        "raw_text": "单件包装30×20×8cm，毛重0.42kg",
                    }
                ],
                "warnings": [],
            }
        ],
        "domestic_freight": {
            "destination": "中国集货仓",
            "order_quantity": 10,
            "order_freight_lower_cny": 10,
            "order_freight_upper_cny": 20,
            "per_unit_lower_cny": 1,
            "per_unit_upper_cny": 2,
            "raw_text": "运费10-20元",
            "status": "bounded",
        },
        "missing_fields": [],
        "warnings": [],
        "fetched_at": "2026-10-15T01:00:00+00:00",
    }


class WorkBuddyBridgeTests(unittest.TestCase):
    def test_executable_override_runs_directly(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "codebuddy.exe"
            executable.write_bytes(b"test")
            resolved, command = bridge.locate_workbuddy_cli(str(executable))
            self.assertEqual(resolved, str(executable.resolve()))
            self.assertEqual(command, [str(executable.resolve())])

    def test_standalone_cli_is_preferred_to_embedded_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            standalone = Path(temp) / "codebuddy.exe"
            embedded = Path(temp) / "codebuddy"
            standalone.write_bytes(b"standalone")
            embedded.write_text("embedded", encoding="utf-8")
            with (
                mock.patch.object(bridge, "DEFAULT_STANDALONE_WORKBUDDY_CLI", standalone),
                mock.patch.object(bridge, "DEFAULT_EMBEDDED_WORKBUDDY_CLI", embedded),
                mock.patch.dict(bridge.os.environ, {"WORKBUDDY_CLI": ""}),
            ):
                resolved, command = bridge.locate_workbuddy_cli(None)
            self.assertEqual(resolved, str(standalone.resolve()))
            self.assertEqual(command, [str(standalone.resolve())])

    def test_canonical_offer_url(self):
        canonical, offer_id = bridge.canonical_offer_url(
            "https://detail.1688.com/offer/123456.html?spm=test"
        )
        self.assertEqual(canonical, "https://detail.1688.com/offer/123456.html")
        self.assertEqual(offer_id, "123456")

    def test_rejects_search_url(self):
        with self.assertRaises(ValueError):
            bridge.canonical_offer_url("https://s.1688.com/selloffer/offer_search.htm")

    def test_valid_result(self):
        errors, _ = bridge.validate_result(sample_result(), sample_job())
        self.assertEqual(errors, [])

    def test_normalizes_sku_display_key_from_exact_option_order(self):
        result = sample_result()
        result["skus"][0]["sku_display_key"] = "黑色款"
        notes = bridge.normalize_result_payload(result)
        self.assertEqual(result["skus"][0]["sku_display_key"], "黑色")
        self.assertEqual(len(notes), 1)
        errors, _ = bridge.validate_result(result, sample_job())
        self.assertEqual(errors, [])

    def test_attach_browser_evidence_rejects_credentials_and_binds_safe_page_text(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            bridge.ensure_runtime(runtime)
            job = sample_job()
            job_path = runtime / "jobs" / f"{job['job_id']}.json"
            bridge.write_json(job_path, job)
            evidence = {
                "schema_version": "1.0",
                "source": "codex_attached_browser",
                "captured_at": "2026-10-15T02:00:00+00:00",
                "access_mode": "authenticated",
                "canonical_offer_url": job["canonical_offer_url"],
                "offer_id": job["offer_id"],
                "page_title": "测试商品",
                "page_text": "商品规格 黑色 价格12.50元 库存100件 包装长30厘米宽20厘米高8厘米 毛重420克 国内运费10元" * 2,
            }
            source = runtime / "safe.json"
            bridge.write_json(source, evidence)
            args = Namespace(runtime_dir=str(runtime), job=str(job_path), evidence=str(source))
            attached = bridge.attach_browser_evidence(args)
            self.assertTrue(attached.exists())
            updated = bridge.read_json(job_path)
            self.assertEqual(updated["browser_evidence"]["access_mode"], "authenticated")

            evidence["cookie"] = "forbidden"
            bridge.write_json(source, evidence)
            with self.assertRaises(ValueError):
                bridge.attach_browser_evidence(args)

    def test_detects_duplicate_sku(self):
        result = sample_result()
        result["skus"].append(dict(result["skus"][0]))
        errors, _ = bridge.validate_result(result, sample_job())
        self.assertTrue(any("重复SKU" in item for item in errors))

    def test_rejects_option_outside_declared_axis(self):
        result = sample_result()
        result["skus"][0]["selected_options"][0]["label"] = "白色"
        result["skus"][0]["sku_display_key"] = "白色"
        errors, _ = bridge.validate_result(result, sample_job())
        self.assertTrue(any("选项不在规格轴" in item for item in errors))

    def test_allows_unexecutable_moq_when_explicitly_reported(self):
        result = sample_result()
        result["skus"][0]["executable_tier"] = None
        result["missing_fields"] = ["executable_tier"]
        errors, _ = bridge.validate_result(result, sample_job())
        self.assertEqual(errors, [])

    def test_extracts_wrapped_json_result(self):
        result = sample_result()
        stdout = json.dumps({"type": "result", "result": json.dumps(result, ensure_ascii=False)})
        extracted = bridge.extract_result_payload(stdout, result["job_id"])
        self.assertEqual(extracted["offer_id"], "123456")

    def test_auth_required_is_a_failed_job_not_a_success(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            bridge.ensure_runtime(runtime)
            job = sample_job()
            job_path = runtime / "jobs" / f"{job['job_id']}.json"
            bridge.write_json(job_path, job)
            completed = subprocess.CompletedProcess(
                args=["workbuddy"],
                returncode=0,
                stdout="Authentication required. Please use /login command to sign in",
                stderr="",
            )
            original_build = bridge.build_workbuddy_command
            original_run = bridge.subprocess.run
            try:
                bridge.build_workbuddy_command = lambda *args, **kwargs: (["workbuddy"], {})
                bridge.subprocess.run = lambda *args, **kwargs: completed
                _, success, message = bridge.run_job_file(
                    job_path, runtime, None, "auto", False
                )
            finally:
                bridge.build_workbuddy_command = original_build
                bridge.subprocess.run = original_run
            self.assertFalse(success)
            self.assertIn("需要用户登录", message)
            failure = bridge.read_json(runtime / "failed" / f"{job['job_id']}.json")
            self.assertEqual(failure["reason"], "workbuddy_auth_required")

    def test_candidate_file_is_promoted_even_when_cli_exit_is_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            bridge.ensure_runtime(runtime)
            job = sample_job()
            job_path = runtime / "jobs" / f"{job['job_id']}.json"
            bridge.write_json(job_path, job)

            def fake_run(*args, **kwargs):
                bridge.write_json(
                    runtime / "candidate-results" / f"{job['job_id']}.json",
                    sample_result(),
                )
                return subprocess.CompletedProcess(
                    args=["workbuddy"], returncode=1, stdout="", stderr="output overflow"
                )

            with (
                mock.patch.object(
                    bridge,
                    "build_workbuddy_command",
                    return_value=(["workbuddy"], {}),
                ),
                mock.patch.object(bridge.subprocess, "run", side_effect=fake_run),
            ):
                _, success, message = bridge.run_job_file(
                    job_path, runtime, None, "auto", False
                )

            self.assertTrue(success, message)
            promoted = bridge.read_json(runtime / "results" / f"{job['job_id']}.json")
            self.assertEqual(promoted["offer_id"], "123456")

    def test_collect_adds_label_fee_and_preserves_currency_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            bridge.ensure_runtime(runtime)
            job = sample_job()
            bridge.write_json(runtime / "jobs" / f"{job['job_id']}.json", job)
            bridge.write_json(runtime / "results" / f"{job['job_id']}.json", sample_result())
            output = runtime / "collected.json"
            args = Namespace(
                runtime_dir=str(runtime),
                output=str(output),
                include_partial=False,
            )
            self.assertEqual(bridge.collect_results(args), 0)
            collected = bridge.read_json(output)
            row = collected["rows"][0]
            self.assertEqual(row["custom_item_prefix"], "CS")
            self.assertEqual(row["source_status"], "complete")
            self.assertEqual(row["access_mode"], "authenticated")
            self.assertEqual(row["label_fee_cny"], 3.0)
            self.assertEqual(row["cost_price_lower_cny"], 17.5)
            self.assertEqual(row["cost_price_upper_cny"], 18.5)
            self.assertEqual(row["cost_price_display"], "¥17.50–¥18.50")
            self.assertEqual(row["length_mm"], 300)
            self.assertIsNone(row["suggested_price_rub"])

    def test_nonpacked_dimensions_do_not_enter_main_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            bridge.ensure_runtime(runtime)
            job = sample_job()
            result = sample_result()
            result["skus"][0]["measurement"]["scope"] = "product_only"
            bridge.write_json(runtime / "jobs" / f"{job['job_id']}.json", job)
            bridge.write_json(runtime / "results" / f"{job['job_id']}.json", result)
            output = runtime / "collected.json"
            args = Namespace(
                runtime_dir=str(runtime),
                output=str(output),
                include_partial=False,
            )
            bridge.collect_results(args)
            row = bridge.read_json(output)["rows"][0]
            self.assertIsNone(row["length_mm"])
            self.assertEqual(row["measurement_scope"], "product_only")


if __name__ == "__main__":
    unittest.main()
