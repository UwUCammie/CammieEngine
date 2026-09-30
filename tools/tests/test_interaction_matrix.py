"""Inventory planning guarantees for serialized interaction smoke batches."""

from __future__ import annotations

from pathlib import Path
import json
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_interaction_matrix as interaction
from run_example_full_playthrough import process_timeout_for_ready_window
from run_interaction_matrix import build_interaction_plan


def ready_row(index: int, owner: str, *, group: str = "Psych Engine",
              difficulty: str = "normal") -> dict:
    return {
        "group": group,
        "package": f"package-{owner}",
        "song": f"song-{index}",
        "variant": "default",
        "difficulty": difficulty,
        "runtimeChart": f"assets/data/song-{index}/song-{index}-{difficulty}.json",
        "runtimeOwner": f"assets/imported_mods/{owner}",
        "runtimeChartPresent": True,
        "runtimeOwnerRootPresent": True,
        "ownerMatched": True,
        "sourceVariantImported": True,
        "sourceNoteCountMatched": True,
        "sourceGameplayNoteCountMatched": None,
    }


class InteractionMatrixTest(unittest.TestCase):
    def test_pause_execution_uses_shared_ready_window_timeout(self):
        rows = [ready_row(0, "owner-a")]
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            local_root = scratch / "repo"
            (local_root / ".tools").mkdir(parents=True)
            runtime = scratch / "runtime"
            runtime.mkdir()
            output = scratch / "receipt.jsonl"
            logs = scratch / "logs"
            args = SimpleNamespace(
                binary=scratch / "bin" / "Funkin", runtime_root=runtime,
                mode="pause", timeout_seconds=120, output=output,
            )

            def fake_run_case(_binary, case, duration_ms, **kwargs):
                self.assertEqual(duration_ms, 25000)
                self.assertEqual(kwargs.get("timeout_seconds"),
                                 process_timeout_for_ready_window(25))
                log = logs / f"{case.id}.process.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text(
                    'OFFSCREEN_INPUT|{"key":"Escape","delivered":true}\n'
                    'OFFSCREEN_INPUT|{"key":"Return","delivered":true}\n'
                    'RUNTIME_SMOKE|{"event":"pause_open","musicPlaying":false,"musicTimeMs":5000}\n'
                    'RUNTIME_SMOKE|{"event":"pause_resume","musicPlaying":true,"musicTimeMs":5000}\n',
                    encoding="utf-8",
                )
                return {"status": "passed", "returncode": 0, "timed_out": False}

            with patch.object(interaction, "ROOT", local_root), \
                    patch.object(interaction, "LOG_ROOT", logs), \
                    patch.object(interaction, "_preflight_blockers", return_value={}), \
                    patch.object(interaction, "run_case", side_effect=fake_run_case):
                self.assertEqual(interaction._execute(args, rows), 0)

            result_rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(result_rows[-1]["passed"], 1)

    def test_case_ids_and_receipts_preserve_each_matrix_route_and_difficulty(self):
        first = ready_row(0, "owner-a", difficulty="easy")
        second = ready_row(1, "owner-a", difficulty="hard")
        second["runtimeChart"] = first["runtimeChart"]
        plan = build_interaction_plan([first, second], "pause")

        self.assertEqual(plan["summary"]["plannedRows"], 2)
        self.assertEqual([row["matrixIndex"] for row in plan["receipts"]], [0, 1])
        ids = [row["case"]["id"] for row in plan["receipts"]]
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual(plan["receipts"][0]["case"]["difficulty"], "easy")
        self.assertEqual(plan["receipts"][1]["case"]["difficulty"], "hard")

    def test_cross_owner_cycle_covers_each_ready_row_once_as_source_and_target(self):
        rows = [ready_row(index, owner, group=group, difficulty=difficulty)
                for index, (owner, group, difficulty) in enumerate((
                    ("a", "V-Slice", "normal"),
                    ("b", "Psych Engine", "hard"),
                    ("c", "Codename Engine", "buck"),
                    ("a", "V-Slice", "easy"),
                    ("b", "Psych source archive", "normal"),
                    ("c", "Modding Plus", "hard"),
                ))]
        # V-Slice source-row parity is the engine-routed gameplay count. Its
        # raw count may include source rows that do not route to strumlines.
        for row in rows:
            if row["group"] == "V-Slice":
                row["sourceNoteCountMatched"] = False
                row["sourceGameplayNoteCountMatched"] = True

        plan = build_interaction_plan(rows, "switch")
        receipts = plan["receipts"]
        planned = [row for row in receipts if row["status"] == "planned"]
        source_indices = {row["matrixIndex"] for row in planned}
        target_indices = {row["nextMatrixIndex"] for row in planned}
        owners = {row["matrixIndex"]: row["identity"]["runtimeOwner"] for row in planned}
        self.assertTrue(plan["summary"]["crossOwnerCycle"])
        self.assertEqual(len(planned), len(rows))
        self.assertEqual(source_indices, set(range(len(rows))))
        self.assertEqual(target_indices, source_indices)
        for receipt in planned:
            self.assertNotEqual(owners[receipt["matrixIndex"]],
                                owners[receipt["nextMatrixIndex"]])
        self.assertEqual(set(plan["summary"]["executionOrder"]), source_indices)
        self.assertFalse(plan["summary"]["nativeLaunched"])

    def test_runtime_preflight_blocker_keeps_a_feasible_switch_cycle(self):
        rows = [ready_row(index, owner) for index, owner in enumerate(
            ("a", "a", "b", "b", "c", "c"))]
        plan = build_interaction_plan(rows, "switch", external_blockers={
            0: "runtime preflight: selected instrumental missing",
        })

        self.assertEqual(plan["summary"]["plannedRows"], 5)
        self.assertEqual(plan["summary"]["blockedRows"], 1)
        self.assertTrue(plan["summary"]["crossOwnerCycle"])
        self.assertEqual(plan["receipts"][0]["status"], "blocked")
        self.assertIn("runtime preflight: selected instrumental missing",
                      plan["receipts"][0]["blockers"])
        self.assertEqual(set(plan["summary"]["executionOrder"]), {1, 2, 3, 4, 5})

    def test_inventory_gaps_are_kept_as_blocked_row_receipts(self):
        missing_route = ready_row(0, "a")
        missing_route["runtimeChartPresent"] = False
        missing_route["runtimeChart"] = None
        unmatched_variant = ready_row(1, "b")
        unmatched_variant["sourceVariantImported"] = False
        unmatched_count = ready_row(2, "c")
        unmatched_count["sourceNoteCountMatched"] = False
        plan = build_interaction_plan([missing_route, unmatched_variant, unmatched_count], "pause")

        self.assertEqual(plan["summary"]["plannedRows"], 0)
        self.assertEqual(plan["summary"]["blockedRows"], 3)
        self.assertEqual([row["matrixIndex"] for row in plan["receipts"]], [0, 1, 2])
        self.assertTrue(any("runtimeChartPresent" in item
                            for item in plan["receipts"][0]["blockers"]))
        self.assertTrue(any("sourceVariantImported" in item
                            for item in plan["receipts"][1]["blockers"]))
        self.assertTrue(any("sourceNoteCountMatched" in item
                            for item in plan["receipts"][2]["blockers"]))

    def test_switch_plan_blocks_when_owner_cycle_cannot_be_cross_owner(self):
        rows = [ready_row(index, owner) for index, owner in enumerate(("a", "a", "a", "b"))]
        plan = build_interaction_plan(rows, "switch")
        self.assertEqual(plan["summary"]["plannedRows"], 0)
        self.assertEqual(plan["summary"]["blockedRows"], 4)
        self.assertIn("cannot form a fully cross-owner cycle", plan["summary"]["cycleError"])
        self.assertTrue(all(receipt["nextMatrixIndex"] is None for receipt in plan["receipts"]))


if __name__ == "__main__":
    unittest.main()
