"""The HXC runtime loader reuses translation metadata for one script load."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcLoaderMetadataHandoffTest(unittest.TestCase):
    def test_loader_uses_the_translation_result_for_script_and_registration(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        compatible = play_state[
            play_state.index("function getCompatibleHscript("):
            play_state.index("\n\tvar useCustomInput", play_state.index("function getCompatibleHscript("))
        ]
        loader = play_state[
            play_state.index("function loadHxcCompatScripts("):
            play_state.index("\n\t/** Load one sidecar-selected HXC cutscene", play_state.index("function loadHxcCompatScripts("))
        ]
        registration = play_state[
            play_state.index("function registerHxcCompanionModules("):
            play_state.index("\n\tfunction hxcModuleProxy", play_state.index("function registerHxcCompanionModules("))
        ]

        self.assertIn("HxcCompat.translate(FNFAssets.getText(normalized), normalized)", compatible)
        self.assertIn("Reflect.setField(metadataSink, 'result', converted)", compatible)
        self.assertIn("return converted.generatedHscript", compatible)
        self.assertIn("var metadataSink:Dynamic = {result: null};", loader)
        self.assertIn("null, metadataSink);", loader)
        self.assertIn("var translatedCompat:HxcCompatResult = cast Reflect.field(metadataSink, 'result');", loader)
        self.assertIn("translatedCompat.kind == 'note-kind'", loader)
        self.assertIn("registerHxcCompanionModules(scriptPath, scope, translatedCompat);", loader)
        self.assertIn("analysis.companionClassNames", registration)
        self.assertNotIn("HxcCompat.analyze", loader)
        self.assertNotIn("HxcCompat.analyze", registration)

    def test_translation_handoff_refreshes_note_and_companion_metadata(self):
        mixed_source = '''class DemoSong extends Song {
  function onCreate() {}
}
class OldOptions extends Module {
  var enabled = true;
}'''
        reloaded_source = '''class FreshNote extends NoteKind {
  function new() { super("fresh-kind", "", "warning", []); }
}'''
        path = "assets/imported_mods/demo/scripts/songs/demo.hxc"
        fixture = f'''import HxcCompat.HxcCompatResult;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var sink:Dynamic = {{result: null}};
    var first:HxcCompatResult = HxcCompat.translate({json.dumps(mixed_source)}, {json.dumps(path)});
    Reflect.setField(sink, "result", first);
    var firstScript:String = first.generatedHscript;
    var firstMetadata:HxcCompatResult = cast Reflect.field(sink, "result");
    if (firstScript == null || firstScript == "") fail("translation returned no script");
    if (firstMetadata != first || firstMetadata.companionClassNames == null
      || firstMetadata.companionClassNames.indexOf("OldOptions") < 0)
      fail("the generated script and companion registration did not share one translation");

    // A new load of the same path must replace its previous metadata.
    Reflect.setField(sink, "result", null);
    var second:HxcCompatResult = HxcCompat.translate({json.dumps(reloaded_source)}, {json.dumps(path)});
    Reflect.setField(sink, "result", second);
    var refreshed:HxcCompatResult = cast Reflect.field(sink, "result");
    if (refreshed != second || refreshed.kind != "note-kind"
      || refreshed.noteKinds.length != 1 || refreshed.noteKinds[0] != "fresh-kind")
      fail("reloaded source did not refresh note-kind metadata");
    if (refreshed.companionClassNames == null || refreshed.companionClassNames.indexOf("OldOptions") >= 0)
      fail("reloaded source retained a stale companion name");
  }}
}}'''
        task_tmp = ROOT / "tmp"
        task_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-metadata-handoff-", dir=task_tmp) as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            environment = os.environ.copy()
            environment["TMPDIR"] = str(task_tmp)
            for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY", "XDG_RUNTIME_DIR"):
                environment.pop(name, None)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
