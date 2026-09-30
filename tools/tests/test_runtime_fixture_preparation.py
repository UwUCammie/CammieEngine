"""Source-only contracts for retained runtime-smoke fixture preparation."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = ROOT / "tmp"
PREPARER_PATH = ROOT / "tools" / "prepare_runtime_smoke_fixture.py"
AUDIT_PATH = ROOT / "tools" / "audit_mounted_auto_import.py"
MATRIX_PATH = ROOT / "tools" / "run_runtime_smoke_matrix.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_chart(root: Path, folder: str, chart: str) -> Path:
    path = root / "assets" / "data" / folder / f"{chart}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "song": {
                    "song": folder,
                    "notes": [],
                    "player1": "bf",
                    "player2": "dad",
                    "stage": "stage",
                }
            }
        ),
        encoding="utf-8",
    )
    return path


class RuntimeFixturePreparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = _load("runtime_fixture_audit", AUDIT_PATH)
        cls.preparer = _load("runtime_fixture_preparer", PREPARER_PATH)
        cls.matrix = _load("runtime_fixture_matrix", MATRIX_PATH)

    def test_destination_validation_is_project_tmp_only(self):
        valid = self.audit.validate_runtime_smoke_destination(
            ROOT / "tmp" / "runtime-smoke" / "contract"
        )
        self.assertEqual(valid.parent.name, "runtime-smoke")
        with self.assertRaises(ValueError):
            self.audit.validate_runtime_smoke_destination(Path("/tmp/runtime-smoke-outside"))
        with self.assertRaises(ValueError):
            self.audit.validate_runtime_smoke_destination(ROOT)

    def test_native_import_never_launches_without_offscreen_display(self):
        class NoDisplay:
            @staticmethod
            def offscreen_command(_command):
                raise RuntimeError("xvfb-run is required for off-screen native smoke")

        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder)
            with patch.object(self.preparer.subprocess, "Popen") as launch:
                with redirect_stdout(StringIO()):
                    status = self.preparer._run_native_import(
                        root / "Funkin", root, root / "donor", root / "report",
                        "Auto", 1, root / "regression", NoDisplay(),
                    )
            self.assertEqual(status, 2)
            launch.assert_not_called()

    def test_audit_dry_run_does_not_create_destination(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            donor = Path(folder) / "selected-donor"
            donor.mkdir()
            destination = ROOT / "tmp" / "runtime-smoke" / "audit-dry-run-contract"
            if destination.exists():
                self.fail(f"test destination unexpectedly exists: {destination}")
            environment = {**os.environ, "TMPDIR": str(TMP_ROOT)}
            result = subprocess.run(
                [
                    sys.executable,
                    str(AUDIT_PATH),
                    str(donor),
                    "--prepare-runtime-smoke",
                    "--output-root",
                    str(destination),
                    "--dry-run",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["runtime_smoke_prepare"]["transaction"], "ModuleFunctions.importSong")
            self.assertFalse(destination.exists())

    def test_preparer_dry_run_validates_both_sources_without_writing(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            selected = folder_path / "selected"
            regression = folder_path / "regression"
            selected.mkdir()
            regression.mkdir()
            for case in self.preparer._external_regression_cases(self.matrix):
                _write_chart(regression, case.folder, case.chart)
            destination = ROOT / "tmp" / "runtime-smoke" / "preparer-dry-run-contract"
            command = [
                sys.executable,
                str(PREPARER_PATH),
                str(selected),
                "--regression-source",
                str(regression),
                "--output-root",
                str(destination),
                "--structural-only",
                "--dry-run",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP_ROOT)},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["runtime_smoke_structural_prepare"]["selected_expected"], 96)
            self.assertEqual(
                set(payload["runtime_smoke_structural_prepare"]["named_cases"]),
                {case.id for case in self.preparer._external_regression_cases(self.matrix)},
            )
            self.assertFalse(destination.exists())

    def test_native_dry_run_builds_full_import_command_without_launch(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            donor = folder_path / "donor"
            donor.mkdir()
            runtime = folder_path / "runtime"
            (runtime / "assets").mkdir(parents=True)
            report = ROOT / "tmp" / "runtime-smoke" / "native-dry-run-contract"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARER_PATH),
                    str(donor),
                    "--binary",
                    "/bin/true",
                    "--runtime-root",
                    str(runtime),
                    "--output-root",
                    str(report),
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP_ROOT)},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)["native_runtime_import_prepare"]
            self.assertEqual(payload["command"][1], "--smoke-import-source")
            self.assertIn("--smoke-import-type", payload["command"])
            self.assertFalse(report.exists())

    def test_native_preparation_rejects_donor_runtime_overlap(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            binary = root / "Funkin"
            binary.write_bytes(b"not-a-game")
            binary.chmod(0o755)
            report = ROOT / "tmp" / "runtime-smoke" / "overlap-contract"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARER_PATH),
                    str(root),
                    "--binary",
                    str(binary),
                    "--runtime-root",
                    str(root),
                    "--output-root",
                    str(report),
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP_ROOT)},
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("overlap", result.stderr)
            self.assertFalse(report.exists())

    def test_native_postflight_rejects_markers_and_requires_hxc_dependencies(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")
            for case in self.matrix.SMOKE_MATRIX[:6]:
                song_dir = data_root / case.folder
                song_dir.mkdir(parents=True)
                (song_dir / f"{case.chart}.json").write_text(
                    json.dumps(
                        {"song": {"player1": "bf", "player2": "dad", "gf": "gf", "stage": "stage", "uiType": "normal"}}
                    ),
                    encoding="utf-8",
                )
                if case.id == "family-vslice":
                    root = runtime / "assets" / "imported_mods" / case.id
                    root.mkdir(parents=True)
                    (root / "adapter.hscript").write_text("function start() {}", encoding="utf-8")
                    manifest = {"roots": [{"path": f"assets/imported_mods/{case.id}"}]}
                else:
                    # Ordinary legacy representatives may legitimately have no
                    # executable companion script.  Their chart/dependency
                    # checks still run, but an empty manifest is not a gap.
                    manifest = {"roots": []}
                (song_dir / "compatScripts.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
            self.assertEqual(self.preparer._native_asset_diagnostics(runtime, self.matrix), [])
            marker = runtime / "assets" / "songs" / "dokidoggle" / "Inst.ogg"
            marker.parent.mkdir(parents=True)
            marker.write_bytes(b"AUDIT_MEDIA_SOURCE_SIZE=123")
            diagnostics = self.preparer._native_asset_diagnostics(runtime, self.matrix)
            self.assertTrue(any("marker instrumental" in item for item in diagnostics))
            (runtime / "assets" / "imported_mods" / "family-vslice" / "adapter.hscript").unlink()
            diagnostics = self.preparer._native_asset_diagnostics(runtime, self.matrix)
            self.assertTrue(any("no non-empty generated/script adapter" in item for item in diagnostics))

    def test_native_postflight_allows_empty_compat_namespace_for_native_representative(self):
        """Native/Kade charts may have a provenance manifest without scripts."""
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")
            for case in self.matrix.SMOKE_MATRIX[:6]:
                song_dir = data_root / case.folder
                song_dir.mkdir(parents=True)
                (song_dir / f"{case.chart}.json").write_text(
                    json.dumps(
                        {"song": {"player1": "bf", "player2": "dad", "gf": "gf", "stage": "stage", "uiType": "normal"}}
                    ),
                    encoding="utf-8",
                )
                if case.id == "family-vslice":
                    # V-Slice is the selected HXC probe and must retain its
                    # generated executable adapter in the postflight gate.
                    root = runtime / "assets" / "imported_mods" / case.id
                    root.mkdir(parents=True)
                    (root / "adapter.hscript").write_text("function start() {}", encoding="utf-8")
                    manifest = {"roots": [{"path": f"assets/imported_mods/{case.id}"}]}
                else:
                    # This is valid output when a legacy donor has no foreign
                    # script tree: the manifest records a destination
                    # namespace, but no namespace directory is materialized.
                    manifest = {
                        "roots": [
                            {"path": f"assets/imported_mods/{case.id}-empty"}
                        ]
                    }
                (song_dir / "compatScripts.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
            self.assertEqual(self.preparer._native_asset_diagnostics(runtime, self.matrix), [])

    def test_native_postflight_uses_native_stage_and_manifest_owned_hxc_visuals(self):
        """Psych stages and FPS Plus HXC visuals follow their real loaders."""
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")

            for case in self.matrix.SMOKE_MATRIX[:6]:
                song_dir = data_root / case.folder
                song_dir.mkdir(parents=True)
                payload = {
                    "song": {
                        "player1": "bf",
                        "player2": "dad",
                        "gf": "gf",
                        "stage": "stage",
                        "uiType": "normal",
                    }
                }
                if case.id == "family-psych":
                    payload["song"]["stage"] = "Haven"
                if case.id == "family-fps-plus":
                    payload["song"].update(
                        {
                            "player2": "WhitBonkers",
                            "gf": "GfStandingScared",
                            "stage": "alleyBalls",
                        }
                    )
                (song_dir / f"{case.chart}.json").write_text(
                    json.dumps(payload), encoding="utf-8"
                )
                if case.id == "family-vslice":
                    compat_root = runtime / "assets" / "imported_mods" / "vslice"
                    compat_root.mkdir(parents=True)
                    (compat_root / "adapter.hscript").write_text(
                        "function start() {}", encoding="utf-8"
                    )
                    manifest = {
                        "selectedRoot": "assets/imported_mods/vslice",
                        "roots": [
                            {"engine": "V-Slice", "path": "assets/imported_mods/vslice"}
                        ],
                    }
                elif case.id == "family-fps-plus":
                    compat_root = runtime / "assets" / "imported_mods" / "fps"
                    chars_root = compat_root / "scripts" / "characters"
                    stages_root = compat_root / "scripts" / "stages"
                    chars_root.mkdir(parents=True)
                    stages_root.mkdir(parents=True)
                    (chars_root / "WhitBonkers.hxc").write_text(
                        'class WhitBonkers extends CharacterInfoBase { '
                        'info.spritePath = "characters/WhittyCrazy"; }',
                        encoding="utf-8",
                    )
                    (chars_root / "GfStandingScared.hxc").write_text(
                        'class GfStandingScared extends CharacterInfoBase { '
                        'info.spritePath = "characters/GF_Standing_Sway"; }',
                        encoding="utf-8",
                    )
                    (stages_root / "alleyBalls.hxc").write_text(
                        "class alleyBalls extends BaseStage { "
                        "var bg = new BGSprite('alley/BallisticBackground'); }",
                        encoding="utf-8",
                    )
                    manifest = {
                        "selectedRoot": "assets/imported_mods/fps",
                        "roots": [
                            {"engine": "FPS Plus", "path": "assets/imported_mods/fps"}
                        ],
                    }
                    images = runtime / "assets" / "images"
                    for relative in (
                        "characters/WhittyCrazy.png",
                        "characters/WhittyCrazy.xml",
                        "characters/GF_Standing_Sway.png",
                        "characters/GF_Standing_Sway.xml",
                        "alley/BallisticBackground.png",
                        "alley/BallisticBackground.xml",
                    ):
                        asset = images / relative
                        asset.parent.mkdir(parents=True, exist_ok=True)
                        asset.write_bytes(b"asset")
                else:
                    manifest = {"roots": []}
                (song_dir / "compatScripts.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )

            psych_stages = runtime / "assets" / "stages"
            psych_stages.mkdir(parents=True)
            (psych_stages / "Haven.lua").write_text("function onCreate() end", encoding="utf-8")
            (psych_stages / "Haven.json").write_text("{}", encoding="utf-8")
            self.assertEqual(self.preparer._native_asset_diagnostics(runtime, self.matrix), [])

    def test_native_postflight_does_not_require_adapter_for_non_vslice_manifest(self):
        """A Modding Plus namespace may contain only donor plugin classes."""
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")
            for case in self.matrix.SMOKE_MATRIX[:6]:
                song_dir = data_root / case.folder
                song_dir.mkdir(parents=True)
                (song_dir / f"{case.chart}.json").write_text(
                    json.dumps(
                        {
                            "song": {
                                "player1": "bf",
                                "player2": "dad",
                                "gf": "gf",
                                "stage": "stage",
                                "uiType": "normal",
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                if case.id == "family-vslice":
                    root = runtime / "assets" / "imported_mods" / "vslice"
                    root.mkdir(parents=True)
                    (root / "adapter.hscript").write_text("function start() {}", encoding="utf-8")
                    manifest = {
                        "selectedRoot": "assets/imported_mods/vslice",
                        "roots": [{"engine": "V-Slice", "path": "assets/imported_mods/vslice"}],
                    }
                elif case.id == "family-modding-plus":
                    root = runtime / "assets" / "imported_mods" / "modding-plus"
                    (root / "scripts" / "plugin_classes").mkdir(parents=True)
                    (root / "scripts" / "plugin_classes" / "RunningTankman.hx").write_text(
                        "class RunningTankman {}", encoding="utf-8"
                    )
                    manifest = {
                        "selectedRoot": "assets/imported_mods/modding-plus",
                        "roots": [
                            {"engine": "Modding Plus", "path": "assets/imported_mods/modding-plus"}
                        ],
                    }
                else:
                    manifest = {"roots": []}
                (song_dir / "compatScripts.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
            self.assertEqual(self.preparer._native_asset_diagnostics(runtime, self.matrix), [])

    def test_native_postflight_rejects_escaping_compat_namespace(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")
            for case in self.matrix.SMOKE_MATRIX[:6]:
                song_dir = data_root / case.folder
                song_dir.mkdir(parents=True)
                (song_dir / f"{case.chart}.json").write_text(
                    json.dumps(
                        {"song": {"player1": "bf", "player2": "dad", "gf": "gf", "stage": "stage", "uiType": "normal"}}
                    ),
                    encoding="utf-8",
                )
                (song_dir / "compatScripts.json").write_text(
                    json.dumps({"roots": [{"path": "../../outside"}]}),
                    encoding="utf-8",
                )
            diagnostics = self.preparer._native_asset_diagnostics(runtime, self.matrix)
            self.assertTrue(any("escapes runtime" in item for item in diagnostics))

    def test_native_postflight_reports_malformed_chart_without_throwing(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            runtime = Path(folder) / "runtime"
            data_root = runtime / "assets" / "data"
            chars = runtime / "assets" / "images" / "custom_chars"
            stages = runtime / "assets" / "images" / "custom_stages"
            ui = runtime / "assets" / "images" / "custom_ui" / "ui_packs"
            for path in (data_root, chars, stages, ui):
                path.mkdir(parents=True)
            (chars / "custom_chars.jsonc").write_text(
                '{"bf":{},"dad":{},"gf":{}}', encoding="utf-8"
            )
            (stages / "custom_stages.json").write_text('{"stage":"stage"}', encoding="utf-8")
            (ui / "ui.json").write_text('{"normal":{}}', encoding="utf-8")
            for case in self.matrix.SMOKE_MATRIX[:6]:
                chart = data_root / case.folder / f"{case.chart}.json"
                chart.parent.mkdir(parents=True)
                payload = [] if case.id == "family-vslice" else {"song": {}}
                chart.write_text(json.dumps(payload), encoding="utf-8")
            diagnostics = self.preparer._native_asset_diagnostics(runtime, self.matrix)
            self.assertTrue(any("invalid representative chart object" in item for item in diagnostics))

    def test_named_overlay_copies_exact_data_and_leaves_donor_unchanged(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            donor = folder_path / "donor"
            destination = folder_path / "overlay"
            donor.mkdir()
            selected_cases = self.preparer._external_regression_cases(self.matrix)[:2]
            source_files = []
            for case in selected_cases:
                chart = _write_chart(donor, case.folder, case.chart)
                sidecar = chart.parent / "modchart.hscript"
                sidecar.write_text("trace('fixture');\n", encoding="utf-8")
                source_files.extend([chart, sidecar])
            before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files}
            copied, owners = self.preparer._copy_named_regressions(
                donor,
                destination,
                selected_cases,
                self.matrix,
            )
            self.assertGreaterEqual(copied, 4)
            self.assertEqual(set(owners), {case.id for case in selected_cases})
            for case in selected_cases:
                self.assertTrue(
                    (destination / "assets" / "data" / case.folder / f"{case.chart}.json").is_file()
                )
            self.assertEqual(
                before,
                {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
            )

    def test_matrix_manifest_routes_selected_and_named_roots(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder)
            selected = root / "selected"
            regressions = root / "regressions" / "modding-plus-fnf"
            (selected / "assets").mkdir(parents=True)
            (regressions / "assets").mkdir(parents=True)
            case_roots = {
                case.id: (
                    "regressions/modding-plus-fnf"
                    if case.id in {entry.id for entry in self.preparer._external_regression_cases(self.matrix)}
                    else "selected"
                )
                for case in self.matrix.SMOKE_MATRIX
            }
            (root / self.matrix.PREPARED_MANIFEST).write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "native-runtime-smoke-fixture",
                        "selected_root": "selected",
                        "case_roots": case_roots,
                        "runtime_matrix_eligible": True,
                    }
                ),
                encoding="utf-8",
            )
            roots = self.matrix.load_prepared_fixture(root)
            self.assertEqual(roots["family-vslice"], selected.resolve())
            self.assertEqual(roots["chaos"], regressions.resolve())
            self.assertNotEqual(roots["chaos"], roots["family-vslice"])

    def test_structural_manifest_is_rejected_as_non_launchable(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder)
            (root / "selected" / "assets").mkdir(parents=True)
            (root / self.matrix.PREPARED_MANIFEST).write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "kind": "native-runtime-smoke-structural-fixture",
                        "selected_root": "selected",
                        "case_roots": {},
                        "runtime_matrix_eligible": False,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "structural-only"):
                self.matrix.load_prepared_fixture(root)


if __name__ == "__main__":
    unittest.main()
