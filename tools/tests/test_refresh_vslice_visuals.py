"""Scoped, reviewed V-Slice script regeneration leaves user files recoverable."""

import importlib.util
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("refresh_vslice_visuals", ROOT / "tools/refresh_vslice_visuals.py")
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


class RefreshVSliceVisualsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "tmp").mkdir(parents=True, exist_ok=True)

    def test_scoped_plan_and_hash_checked_recoverable_apply(self):
        with tempfile.TemporaryDirectory(prefix="vslice-refresh-test-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            donor, runtime = base / "donor", base / "runtime"
            (donor / "data/stages").mkdir(parents=True)
            (donor / "images/stages").mkdir(parents=True)
            (runtime / "assets/data/one").mkdir(parents=True)
            (runtime / "assets/images/custom_stages/arena").mkdir(parents=True)
            definition = donor / "data/stages/arena.json"
            definition.write_text(json.dumps({
                "version": "1.0.0", "name": "arena", "cameraZoom": 0.8,
                "characters": {"bf": {"zIndex": 300}, "dad": {"zIndex": 200}, "gf": {"zIndex": 100}},
                "props": [{"name": "cover", "zIndex": 210, "position": [20, 30],
                           "scale": [1.5, 1.5], "assetPath": "stages/cover", "animType": "none"}],
            }), newline='\n')
            (donor / "images/stages/cover.png").write_bytes(b"fixture-png")
            owner = refresh.namespace_for(donor)
            (runtime / "assets/data/one/compatScripts.json").write_text(json.dumps({
                "version": 1, "selectedRoot": owner, "roots": [{"engine": "V-Slice", "path": owner}]
            }), newline='\n')
            (runtime / "assets/data/one/one.json").write_text(json.dumps({"song": {
                "song": "one", "stage": "arena", "player1": "bf", "player2": "dad", "gf": "gf"
            }}), newline='\n')
            target = runtime / "assets/images/custom_stages/arena.hscript"
            generated = refresh.haxe_convert([{"kind": "stage", "reference": "arena",
                "definition": str(definition), "contentRoot": str(donor)}], runtime)[0]
            self.assertIn("stage.setZIndex(vSliceProp_cover_0, 210);", generated["hscript"])
            mapping = generated["assets"][0]
            (runtime / "assets/images/custom_stages/arena" / mapping["destination"]).write_bytes(b"fixture-png")
            old = generated["hscript"].replace("    stage.setZIndex(vSliceProp_cover_0, 210);\n", "")
            target.write_text(old, newline='\n')
            options = runtime / "assets/data/options.json"
            options.write_bytes(b'{"custom":"keep"}')
            plan = refresh.make_plan(donor, runtime)
            self.assertEqual([(item["kind"], item["reference"]) for item in plan["candidates"]],
                             [("stage", "arena")])
            self.assertIn("+    stage.setZIndex(vSliceProp_cover_0, 210);", plan["candidates"][0]["diff"])
            plan_path = base / "reviewed-plan.json"
            plan_path.write_text(json.dumps(plan), newline='\n')
            # This fixture only replaces its private runtime. Keep real flock
            # behavior but isolate lock files from the user's game/build.
            (base / "source").symlink_to(ROOT / "source", target_is_directory=True)
            (base / ".tools").mkdir()
            with patch.object(refresh, "ROOT", base):
                backup = refresh.apply_plan(plan, plan_path)
                try:
                    self.assertEqual(target.read_text(), generated["hscript"])
                    self.assertEqual((backup / target.relative_to(runtime)).read_text(), old)
                    self.assertEqual(options.read_bytes(), b'{"custom":"keep"}')
                    with self.assertRaisesRegex(ValueError, "target path or bytes changed"):
                        refresh.apply_plan(plan, plan_path)
                finally:
                    shutil.rmtree(backup)

    def test_other_owner_collision_blocks_plan(self):
        with tempfile.TemporaryDirectory(prefix="vslice-refresh-test-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            donor, runtime = base / "donor", base / "runtime"
            (donor / "data/stages").mkdir(parents=True)
            (donor / "data/stages/arena.json").write_text(json.dumps({"name": "arena", "props": []}), newline='\n')
            for song, owner in (("one", refresh.namespace_for(donor)), ("two", "assets/imported_mods/v-slice-other-123")):
                target = runtime / "assets/data" / song
                target.mkdir(parents=True)
                (target / "compatScripts.json").write_text(json.dumps({"selectedRoot": owner, "roots": [{"engine": "V-Slice", "path": owner}]}), newline='\n')
                (target / (song + ".json")).write_text(json.dumps({"song": {"stage": "arena"}}), newline='\n')
            plan = refresh.make_plan(donor, runtime)
            self.assertEqual(plan["candidates"], [])
            self.assertIn("ID referenced by another manifest owner", [item["reason"] for item in plan["skipped"]])

    def test_converter_keeps_proven_native_base_atlas_and_animations(self):
        # A compatibility stub returning no native candidates used to plan a
        # destructive rewrite of a real character. Exercise the current
        # EngineCompat lookup, registry and atlas prefix proof together.
        with tempfile.TemporaryDirectory(prefix="vslice-refresh-test-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            donor, runtime = base / "donor", base / "runtime"
            (donor / "data/characters").mkdir(parents=True)
            (runtime / "assets/images/custom_chars/bf").mkdir(parents=True)
            definition = donor / "data/characters/hero.json"
            definition.write_text(json.dumps({"name": "hero", "assetPath": "characters/bf",
                "renderType": "sparrow", "animations": [
                    {"name": "idle", "prefix": "BF idle dance", "frameRate": 24},
                    {"name": "singUP", "prefix": "BF NOTE UP", "frameRate": 24}]}), newline='\n')
            (runtime / "assets/images/custom_chars/custom_chars.jsonc").write_text(json.dumps({
                "bf": {"like": "bf", "icons": [0, 0, 0, 0]}}), newline='\n')
            (runtime / "assets/images/custom_chars/bf/char.png").write_bytes(b"fixture-png")
            (runtime / "assets/images/custom_chars/bf/char.xml").write_text(
                '<TextureAtlas><SubTexture name="BF idle dance0000"/>'
                '<SubTexture name="BF NOTE UP0000"/></TextureAtlas>', newline='\n')
            converted = refresh.haxe_convert([{"kind": "character", "reference": "hero",
                "definition": str(definition), "contentRoot": str(donor)}], runtime)[0]
            script = converted["hscript"]
            self.assertIn('assets/images/custom_chars/bf/', script)
            self.assertIn('addByPrefix("idle", "BF idle dance"', script)
            self.assertIn('addByPrefix("singUP", "BF NOTE UP"', script)
            self.assertNotIn('vSliceNativeRoot = ""', script)


if __name__ == "__main__":
    unittest.main()
