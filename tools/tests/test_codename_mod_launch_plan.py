"""The Imported Mods catalog exposes only owner-scoped state scripts."""

import ast
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameModLaunchPlanTest(unittest.TestCase):
    def test_private_fnas_runner_holds_keys_across_input_polls(self):
        runner = (ROOT / "tmp/fnas-owner-ui-preview/run_owner_menu.py").read_text()
        tree = ast.parse(runner)
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "key")
        isolated = ast.Module(body=[function], type_ignores=[])
        calls = []
        sleeps = []

        class FakeSubprocess:
            DEVNULL = object()
            PIPE = object()

            @staticmethod
            def run(args, **kwargs):
                calls.append((args, kwargs))
                return SimpleNamespace(returncode=0)

        namespace = {"subprocess": FakeSubprocess,
                     "time": SimpleNamespace(sleep=sleeps.append)}
        exec(compile(isolated, "run_owner_menu.py", "exec"), namespace)
        namespace["key"]({"DISPLAY": ":71"}, "123", "shift+i")
        self.assertEqual([call[0][1] for call in calls],
                         ["windowfocus", "keydown", "keyup"])
        self.assertEqual(calls[1][0][-1], "shift+i")
        self.assertEqual(sleeps, [.25])

    def test_private_fnas_runner_uses_flattened_launch_plan_order(self):
        runner = (ROOT / "tmp/fnas-owner-ui-preview/run_owner_menu.py").read_text()
        tree = ast.parse(runner)
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "launch_rows")
        isolated = ast.Module(body=[function], type_ignores=[])
        namespace = {"Path": Path}
        exec(compile(isolated, "run_owner_menu.py", "exec"), namespace)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            runtime = Path(folder)
            for owner, scripts in (("zeta", ("Alpha",)),
                                   ("alpha", ("Zeta", "FnasMainState"))):
                states = runtime / "assets/imported_mods" / owner / "data/states"
                states.mkdir(parents=True)
                for script in scripts:
                    (states / f"{script}.hx").write_text("function create() {}")
            rows = namespace["launch_rows"]({"entries": [
                {"root": "assets/imported_mods/missing", "label": "Absent", "states": [
                    "data/states/Hidden.hx"]},
                {"root": "assets/imported_mods/zeta", "label": "Zeta", "states": [
                    "data/states/Alpha.hx"]},
                {"root": "assets/imported_mods/alpha", "label": "Alpha", "states": [
                    "data/states/Zeta.hx", "data/states/FnasMainState.hx"]},
            ]}, runtime)
        self.assertEqual([(row["label"], row["stateName"]) for row in rows], [
            ("Alpha", "FnasMainState"), ("Alpha", "Zeta"), ("Zeta", "Alpha")])
        selected = [index for index, row in enumerate(rows)
                    if row["root"] == "assets/imported_mods/alpha"
                    and row["relativePath"] == "data/states/FnasMainState.hx"]
        self.assertEqual(selected, [0])

    def test_private_fnas_runner_waits_for_visible_title_flash_and_menu_labels(self):
        runner = (ROOT / "tmp/fnas-owner-ui-preview/run_owner_menu.py").read_text()
        tree = ast.parse(runner)
        function_names = {"title_flash_state", "native_main_menu_visible",
                          "native_menu_luma_candidate", "native_menu_luma_stable",
                          "imported_mods_luma_candidate", "imported_mods_luma_stable"}
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in function_names]
        self.assertEqual({node.name for node in functions},
                         function_names)
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     "run_owner_menu.py", "exec"), namespace)
        state = namespace["title_flash_state"]
        self.assertEqual(state(.20, .20, False), "waiting")
        self.assertEqual(state(.70, .20, False), "flash")
        self.assertEqual(state(.25, .20, True), "settled")
        visible = namespace["native_main_menu_visible"]
        self.assertTrue(visible("Story Mode    Freeplay    Options"))
        self.assertFalse(visible("Press Enter to Begin"))
        candidate = namespace["native_menu_luma_candidate"]
        stable = namespace["native_menu_luma_stable"]
        self.assertTrue(candidate(.689))
        self.assertFalse(candidate(.099))
        self.assertFalse(candidate(.99))
        self.assertTrue(stable([.688, .701, .689]))
        self.assertFalse(stable([.99, .688, .701]))
        self.assertFalse(stable([.50, .70, .90]))
        chooser_candidate = namespace["imported_mods_luma_candidate"]
        chooser_stable = namespace["imported_mods_luma_stable"]
        self.assertTrue(chooser_candidate(.08))
        self.assertFalse(chooser_candidate(.689))
        self.assertFalse(chooser_candidate(.001))
        self.assertTrue(chooser_stable([.08, .09, .10]))
        self.assertFalse(chooser_stable([.69, .08, .09]))

    def test_multi_owner_entries_are_scoped_sorted_and_script_backed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            for root, names in (("alpha", ("Zeta", "Main")), ("beta", ("Menu",))):
                for name in names:
                    path = base / "assets/imported_mods" / root / "data/states" / (name + ".hx")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("function create() {}")
            (base / "assets/imported_mods/alpha/data/states/not-script.txt").write_text("ignored")
            catalog = {
                "version": 1,
                "entries": [
                    {"root": "assets/imported_mods/beta", "label": "Beta", "states": ["data/states/Menu.hx"]},
                    {"root": "assets/imported_mods/alpha", "label": "Alpha", "states": [
                        "data/states/Zeta.hx", "data/states/Main.hx", "data/states/Missing.hx"
                    ]},
                ],
            }
            import json

            (base / "catalog.json").write_text(json.dumps(catalog))
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var plan=CodenameModLaunchPlan.fromCatalog(sys.io.File.getContent("catalog.json"));
  if (!plan.valid || plan.entries.length!=3) throw "unexpected plan size";
  if (plan.entries[0].label!="Alpha" || plan.entries[0].stateName!="Main") throw "first row";
  if (plan.entries[1].label!="Alpha" || plan.entries[1].stateName!="Zeta") throw "second row";
  if (plan.entries[2].root!="assets/imported_mods/beta" || plan.entries[2].stateName!="Menu") throw "third owner";
  if (plan.diagnostics.length!=1 || plan.diagnostics[0].indexOf("Missing.hx")<0
      || plan.diagnostics[0].indexOf("missing")<0) throw "missing-state diagnostic";
 }
}''')
            process = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=base,
                text=True,
                capture_output=True,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
