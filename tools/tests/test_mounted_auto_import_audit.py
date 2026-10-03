"""Mounted end-to-end coverage for Auto's isolated song writer audit."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import importlib.util
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class CodenameDiscoveryFixtureTest(unittest.TestCase):
    def test_diagnostic_fixture_uses_production_codename_discovery(self):
        path = ROOT / "tools/diagnose_example_auto_import.py"
        spec = importlib.util.spec_from_file_location("diagnose_example_auto_import", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixture = module.build_fixture()
        self.assertIn("root.engine == ImportEngine.CODENAME", fixture)
        self.assertIn("discoverCodenameSongImports(root)", fixture)
        self.assertIn("static function discoverCodenameSongsFromBase", fixture)


class AutoImportAuditFixtureTest(unittest.TestCase):
    def test_owner_qualified_targets_mark_chart_identity_collision(self):
        path = ROOT / "tools/audit_mounted_auto_import.py"
        spec = importlib.util.spec_from_file_location("audit_mounted_auto_import", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixture = module.haxe_fixture((ROOT / "source/ModuleFunctions.hx").read_text())
        target_planner = module.extract_method(
            fixture, "public static function auditImportTarget"
        )
        self.assertEqual(
            target_planner.count("Reflect.setField(song, 'ownerQualifiedCollision', true)"),
            2,
            target_planner,
        )

    def test_nmv_audit_expectations_apply_source_chart_and_title_rules(self):
        path = ROOT / "tools/audit_mounted_auto_import.py"
        spec = importlib.util.spec_from_file_location("audit_mounted_auto_import", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fixture = module.haxe_fixture((ROOT / "source/ModuleFunctions.hx").read_text())
        self.assertIn("NightmareVisionChartCompat.convert(sourceChart, chartPath)", fixture)
        self.assertIn("songData.engine != ImportEngine.NIGHTMARE_VISION", fixture)
        self.assertIn("sourceSelectableDifficulties:Array<String>", fixture)
        self.assertIn('"NightmareVisionDifficultyCompat.hx"', path.read_text())


@unittest.skipUnless(DONOR.is_dir(), "the external example-mod fixture is not mounted")
class MountedAutoImportAuditTest(unittest.TestCase):
    def test_large_mounted_tools_use_project_local_temp(self):
        for relative in (
            "tools/audit_mounted_auto_import.py",
            "tools/diagnose_example_auto_import.py",
        ):
            source = (ROOT / relative).read_text()
            self.assertIn('ROOT / "tmp"', source, relative)
            self.assertIn("TemporaryDirectory(", source, relative)
        diagnostic = (ROOT / "tools/diagnose_example_auto_import.py").read_text()
        self.assertIn('alias_root = cpp_target / "aliases"', diagnostic)
        self.assertIn('Path("aliases") / name', diagnostic)
        self.assertNotIn('Path("/tmp")', diagnostic)
        self.assertNotIn('cwd=Path("/tmp")', diagnostic)

    def test_codename_roots_use_read_only_discovery_path(self):
        result = subprocess.run(
            ["python3", str(ROOT / "tools/audit_mounted_auto_import.py"),
             str(DONOR), "--discover-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        counts = re.findall(r"ROOT_CANDIDATES\|Codename Engine\|([0-9]+)", output)
        self.assertTrue(counts, "audit reported no Codename roots: " + output)
        self.assertTrue(any(int(count) > 0 for count in counts), output)
        self.assertRegex(output, r"ENGINE\|Codename Engine\|[1-9][0-9]*")

    def test_selected_songs_materialize_and_are_freeplay_visible(self):
        result = subprocess.run(
            ["python3", str(ROOT / "tools/audit_mounted_auto_import.py"), str(DONOR)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        # The mounted donor set changes as mods are added and removed; assert
        # the audit's structural invariants instead of fixed inventory counts.
        self.assertRegex(output, r"ROOTS=[1-9][0-9]*\|CANDIDATES=[1-9][0-9]*\|SELECTED=[1-9][0-9]*")
        imported = re.search(
            r"IMPORTED=(?P<imported>[1-9][0-9]*)\|DUPLICATES=[0-9]+\|FAILED=0\|MANIFESTS=(?P=imported)\|FREEPLAY_VISIBLE=(?P=imported)",
            output,
        )
        self.assertIsNotNone(imported, output)
        self.assertRegex(
            output,
            r"INSTRUMENTALS_VALIDATED=(?P<validated>[1-9][0-9]*)\|BOUNDED_MEDIA_FIXTURES=(?P=validated)",
        )
        # The writer audit must prove chart semantics, not merely that a JSON
        # file appeared.  Native charts use the source payload with only the
        # documented centralized normalization; V-Slice uses the captured
        # conversion output.  The source snapshot also covers skipped
        # duplicate candidates and V-Slice metadata/chart pairs.
        self.assertRegex(
            output,
            r"CHART_SEMANTICS=[1-9][0-9]*\|NATIVE_CHARTS=[1-9][0-9]*\|VSLICE_CHARTS=[1-9][0-9]*",
        )
        self.assertRegex(output, r"NOTE_ROWS_CHECKED=[1-9][0-9]*\|EVENT_PAYLOADS_CHECKED=[1-9][0-9]*")
        self.assertRegex(output, r"DIFFICULTY_SETS_CHECKED=[1-9][0-9]*\|GAMEPLAY_METADATA_CHECKED=[1-9][0-9]*")
        self.assertRegex(output, r"DONOR_SOURCE_FILES=([1-9][0-9]*)\|DONOR_SOURCE_BYTES_UNCHANGED=\1")
        self.assertIn("CHART_SEMANTIC_ERRORS=0", output)
        visual = re.search(
            r"VSLICE_VISUAL_CONVERSIONS=([1-9][0-9]*)"
            r"\|SUPPORTED_ASSET_MAPPINGS=([1-9][0-9]*)"
            r"\|VISUAL_SOURCES_VALIDATED=([1-9][0-9]*)"
            r"\|VISUAL_SOURCE_FILES=([1-9][0-9]*)"
            r"\|VISUAL_SCRIPTS_PARSED=([1-9][0-9]*)"
            r"\|VISUAL_PLAN_ERRORS=0",
            output,
        )
        self.assertIsNotNone(visual, output)
        self.assertEqual(visual.group(2), visual.group(3), output)
        self.assertIn(
            f"VSLICE_VISUAL_SOURCE_FILES_UNCHANGED={visual.group(4)}", output
        )
        # Engine coverage follows the mounted donor set; instead of pinning
        # per-family counts, assert the audit's structural invariants: every
        # reported family is non-empty, the families with importable donors in
        # the current library are covered, and the per-family totals account
        # for every imported song.  Codename roots use the production chart
        # converter here; the remaining Legacy/Kade donors ship modern
        # songs/<song>/charts layouts with no legacy-importable songs, and the
        # FPS Plus donor left the library.
        engines: dict = {}
        for line in output.splitlines():
            engine = re.search(r"ENGINE\|([^|]+)\|([0-9]+)$", line)
            if engine:
                engines[engine.group(1)] = int(engine.group(2))
        self.assertTrue(engines, "audit reported no engine families: " + output)
        for engine, count in sorted(engines.items()):
            self.assertGreater(count, 0, f"engine family {engine} reported empty")
        for family in (
            "V-Slice",
            "Codename Engine",
            "Psych Engine",
            "Modding Plus",
        ):
            self.assertIn(family, engines, f"engine family {family} not covered")
        self.assertEqual(
            sum(engines.values()),
            int(imported.group("imported")),
            f"per-engine totals do not cover every imported song: {sorted(engines.items())}",
        )
