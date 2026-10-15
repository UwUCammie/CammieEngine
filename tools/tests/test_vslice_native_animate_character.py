"""A V-Slice character that points at base-game Animate art the package does
not ship uses the engine's own implementation of that base character."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"

MAIN = '''import haxe.Json;
import sys.io.File;
class Main {
 static function main() {
  var input:Array<Dynamic> = cast Json.parse(File.getContent(Sys.args()[0]));
  var output:Array<Dynamic> = [];
  for (item in input) {
   var data:Dynamic = CoolUtil.parseJson(File.getContent(item.definition));
   var c:Dynamic = VSliceImporter.convertCharacter(data,item.contentRoot,item.reference,true,item.definition);
   output.push({name:c.name,supported:c.supported,hscript:c.hscript,assets:c.assets,
    diagnostics:c.diagnostics,registryEntry:c.registryEntry});
  }
  File.saveContent(Sys.args()[1],Json.stringify(output));
 }
}'''


def convert(items, runtime):
    with tempfile.TemporaryDirectory(prefix="vslice-native-animate-", dir=ROOT / "tmp") as scratch:
        tmp = Path(scratch)
        cool = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
        start = cool.index("public static function parseJson(")
        end = cool.index("\n\tpublic static function stringifyJson(", start)
        (tmp / "CoolUtil.hx").write_text("import tjson.TJSON;\nclass CoolUtil {\n" + cool[start:end] + "\n}\n")
        (tmp / "Main.hx").write_text(MAIN)
        input_path, output_path = tmp / "input.json", tmp / "output.json"
        input_path.write_text(json.dumps(items))
        completed = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(tmp), "-cp", str(TJSON),
                                    "--run", "Main", str(input_path), str(output_path)],
                                   cwd=runtime, capture_output=True, text=True, timeout=180)
        if completed.returncode:
            raise AssertionError(completed.stdout + completed.stderr)
        return json.loads(output_path.read_text())


class VSliceNativeAnimateCharacterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "tmp").mkdir(parents=True, exist_ok=True)

    def make_runtime(self, base):
        runtime = base / "runtime"
        chars = runtime / "assets/images/custom_chars"
        for like in ("bf", "pico"):
            (chars / like / "portraits").mkdir(parents=True)
            (chars / like / "char.png").write_bytes(b"png")
            (chars / like / "char.xml").write_text("<TextureAtlas/>")
            (chars / like / "dead.png").write_bytes(b"png")
            (chars / like / "icons.png").write_bytes(b"png")
            (chars / (like + ".hscript")).write_text(
                "function init(char) {\n    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', "
                "hscriptPath + 'char.xml');\n    char.animation.addByPrefix('idle', '" + like + " idle', 24, false);\n}\n")
        (chars / "custom_chars.jsonc").write_text(json.dumps({
            "bf": {"like": "bf", "icons": [0, 1, 2, 3], "colors": ["#149DFF"]},
            "pico": {"like": "pico", "icons": [0, 1, 2, 3], "colors": ["#B7D855"]}}))
        return runtime

    def definition(self, donor, name, data):
        path = donor / "data/characters" / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return {"reference": name, "definition": str(path), "contentRoot": str(donor)}

    def test_missing_base_animate_export_uses_native_character(self):
        with tempfile.TemporaryDirectory(prefix="vslice-native-animate-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            runtime = self.make_runtime(base)
            donor = base / "donor"
            animations = [{"name": "idle", "prefix": "Idle", "animType": "framelabel"},
                          {"name": "singLEFT", "prefix": "Left"},
                          {"name": "intro", "prefix": "intro", "assetPath": "shared:characters/hero/extra"}]
            items = [
                self.definition(donor, "hero", {"name": "Hero", "assetPath": "shared:characters/bf",
                                                "renderType": "multianimateatlas", "animations": animations}),
                # An export folder inside the base character's library folder.
                self.definition(donor, "rival", {"name": "Rival",
                                                 "assetPath": "shared:characters/pico/basic-animations",
                                                 "renderType": "animateatlas", "animations": animations[:2],
                                                 "healthbar_colors": [16, 32, 48]}),
                # A package-owned path never borrows an engine character.
                self.definition(donor, "stranger", {"name": "Stranger", "assetPath": "characters/stranger",
                                                    "renderType": "animateatlas", "animations": animations[:2]}),
            ]
            hero, rival, stranger = convert(items, runtime)

            self.assertTrue(hero["supported"], hero["diagnostics"])
            self.assertIn("addByPrefix('idle', 'bf idle'", hero["hscript"])
            self.assertNotIn("AnimateAtlasUtil", hero["hscript"])
            character_assets = [item for item in hero["assets"] if item["kind"] == "character"]
            self.assertEqual(sorted(item["destination"] for item in character_assets),
                             ["char.png", "char.xml", "dead.png"])
            for item in character_assets:
                self.assertEqual(item["source"].replace("\\", "/").rsplit("/", 1)[0],
                                 "assets/images/custom_chars/bf")
            self.assertEqual(hero["registryEntry"]["nativeIconIdentity"], "bf")
            self.assertEqual(hero["registryEntry"]["like"], "hero")
            self.assertEqual(hero["registryEntry"]["colors"], ["#149DFF"])
            codes = [item["code"] for item in hero["diagnostics"]]
            self.assertIn("native-base-character", codes)
            self.assertNotIn("missing-asset", codes)

            self.assertTrue(rival["supported"], rival["diagnostics"])
            self.assertIn("addByPrefix('idle', 'pico idle'", rival["hscript"])
            self.assertEqual(rival["registryEntry"]["nativeIconIdentity"], "pico")
            self.assertEqual(rival["registryEntry"]["colors"], ["#102030"],
                             "an authored bar colour wins over the native character's")

            self.assertFalse(stranger["supported"])
            self.assertIn("missing-asset", [item["code"] for item in stranger["diagnostics"]])
            self.assertEqual([item for item in stranger["assets"] if item["kind"] == "character"], [])

    def test_shipped_animate_export_is_still_converted(self):
        with tempfile.TemporaryDirectory(prefix="vslice-native-animate-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            runtime = self.make_runtime(base)
            donor = base / "donor"
            export = donor / "shared/images/characters/bf"
            export.mkdir(parents=True)
            (export / "Animation.json").write_text("{}")
            (export / "spritemap1.json").write_text("{}")
            (export / "spritemap1.png").write_bytes(b"png")
            item = self.definition(donor, "hero", {"name": "Hero", "assetPath": "shared:characters/bf",
                                                   "renderType": "animateatlas",
                                                   "animations": [{"name": "idle", "prefix": "Idle"}]})
            hero = convert([item], runtime)[0]
            self.assertIn("AnimateAtlasUtil.folder", hero["hscript"])
            self.assertNotIn("native-base-character", [entry["code"] for entry in hero["diagnostics"]])


if __name__ == "__main__":
    unittest.main()
