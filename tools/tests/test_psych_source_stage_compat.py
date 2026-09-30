"""Psych source Haxe stage classes are identified for unsupported-behavior diagnostics."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychSourceStageCompatTest(unittest.TestCase):
    def test_resolves_only_stage_classes_selected_by_playstate_dispatch(self):
        fixture = r'''import PsychSourceStageCompat;
import sys.FileSystem;
import sys.io.File;

class PsychSourceStageCompatProbe {
  static function main() {
    var root = Sys.args()[0];
    var stage = PsychSourceStageCompat.resolve(root, "phillyStreets");
    if (stage == null || stage.className != "PhillyStreets")
      throw "Psych stage dispatch did not resolve its compiled class";
    if (stage.sourcePath != root + "/source/states/stages/PhillyStreets.hx")
      throw "compiled class path was not returned";
    if (stage.modulePath != "states.stages.PhillyStreets")
      throw "compiled class module was not derived from the selected owner's source path";
    if (PsychSourceStageCompat.resolve(root, "notDispatched") != null)
      throw "an unreferenced class file was treated as a stage implementation";
    if (PsychSourceStageCompat.resolve(root, "../PhillyStreets") != null)
      throw "unsafe stage ids must not become filesystem paths";
    if (PsychSourceStageCompat.knownSourceClass("phillyStreets") != "PhillyStreets"
        || PsychSourceStageCompat.knownSourceClass("phillyBlazin") != "PhillyBlazin")
      throw "runtime stage class index omitted a Psych source stage";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_root = Path(folder)
            stage_dir = source_root / "source/states/stages"
            stage_dir.mkdir(parents=True)
            (source_root / "source/states/PlayState.hx").write_text(
                "switch (curStage) {\n"
                "  case 'phillyStreets': new PhillyStreets();\n"
                "  case 'other': new OtherStage();\n"
                "}\n"
            )
            (stage_dir / "PhillyStreets.hx").write_text("class PhillyStreets {}\n")
            (stage_dir / "notDispatched.hx").write_text("class notDispatched {}\n")
            probe = source_root / "PsychSourceStageCompatProbe.hx"
            probe.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "PsychSourceStageCompatProbe", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_psych_archive_dispatch_resolves_philly_streets_class(self):
        archive = ROOT / "tmp/psych-archive-source/FNF-PsychEngine-main"
        self.assertTrue((archive / "source/states/PlayState.hx").is_file())
        fixture = r'''import PsychSourceStageCompat;
class PsychSourceArchiveProbe {
  static function main() {
    var root = Sys.args()[0];
    var stage = PsychSourceStageCompat.resolve(root, "phillyStreets");
    if (stage == null || stage.className != "PhillyStreets")
      throw "the inspected Psych archive dispatch was not classified as compiled behavior";
    if (stage.sourcePath.indexOf("PhillyStreets.hx") < 0)
      throw "compiled Psych stage source evidence is missing";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "PsychSourceArchiveProbe.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "PsychSourceArchiveProbe", str(archive)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_metadata_json_does_not_satisfy_stage_implementation_check(self):
        source = (ROOT / "source/ImportWorkflow.hx").read_text()
        marker = "static function psychStageImplementationFound("
        start = source.index(marker)
        end = source.index("\n\tstatic function chartBelongsToVSlice(", start)
        method = source[start:end]
        fixture = f'''import sys.FileSystem;
using StringTools;
class PsychStageImplementationProbe {{
  static function file(path:String):Bool return FileSystem.exists(path) && !FileSystem.isDirectory(path);
{method}
  static function main() {{
    var root = Sys.args()[0];
    if (psychStageImplementationFound([root + "/stages/phillyStreets.json"]))
      throw "Psych camera/start metadata was counted as an executable stage";
    if (!psychStageImplementationFound([root + "/stages/custom.lua"]))
      throw "Psych stage Lua implementation was missed";
    if (!psychStageImplementationFound([root + "/stages/native.hscript"]))
      throw "native HScript stage implementation was missed";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder)
            (fixture_path / "PsychStageImplementationProbe.hx").write_text(fixture)
            stage_root = fixture_path / "donor/stages"
            stage_root.mkdir(parents=True)
            (stage_root / "phillyStreets.json").write_text(
                '{"defaultZoom":0.77,"boyfriend":[1330,450]}'
            )
            (stage_root / "custom.lua").write_text("function onCreate() end")
            (stage_root / "native.hscript").write_text("function start() {}")
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "PsychStageImplementationProbe", str(stage_root.parent)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_forced_compiled_class_gap_stays_missing_even_when_candidate_exists(self):
        source = (ROOT / "source/ImportWorkflow.hx").read_text()
        marker = "static function dependency(result:ImportScanResult"
        start = source.index(marker)
        brace = source.index("{", start)
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    method = source[start : index + 1]
                    break
        else:
            self.fail("dependency method did not close")
        fixture = f'''import sys.FileSystem;
using StringTools;
typedef ImportScanDependency = {{ var kind:String; var reference:String; var found:Bool; var searched:Array<String>; var origin:String; }};
typedef ImportScanSong = {{ var dependencies:Array<ImportScanDependency>; var missing:Array<ImportScanDependency>; @:optional var diagnostics:Array<String>; }};
typedef ImportScanResult = {{ var missingDependencies:Int; }};
class EngineCompat {{
  public static var lastClassification:String = "";
  public static function resolveStageAlias(value:String):String return value;
  public static function resolveLegacyAssetPath(value:String):String return value;
  public static function planVisualFallback(kind:String, reference:String, origin:String,
      searched:Array<String>, impact:String, ?classification:String):Dynamic {{
    lastClassification = classification;
    return {{diagnostic: {{message: "fallback diagnostic"}}}};
  }}
}}
class DependencyProbe {{
  static function destinationBuiltinDependency(kind:String, reference:String):Bool return true;
  static function characterImplementationFound(candidates:Array<String>):Bool return false;
  static function exists(path:String):Bool return FileSystem.exists(path);
  static function addSongDiagnostic(song:ImportScanSong, message:String):Void {{
    if (song.diagnostics == null) song.diagnostics = [];
    song.diagnostics.push(message);
  }}
{method}
  static function main() {{
    var candidate = Sys.args()[0];
    var result:ImportScanResult = {{missingDependencies: 0}};
    var song:ImportScanSong = {{dependencies: [], missing: []}};
    dependency(result, song, "stage", "phillyStreets", "Psych source dispatcher",
      [candidate], false, true, "unsupported-engine-behavior", "compiled class unavailable");
    if (song.dependencies.length != 1 || song.dependencies[0].found
        || song.missing.length != 1 || result.missingDependencies != 1)
      throw "forced compiled-source gap was masked by an existing fallback candidate";
    if (EngineCompat.lastClassification != "unsupported-engine-behavior")
      throw "compiled-source gap lost its unsupported-behavior classification";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder)
            (fixture_path / "DependencyProbe.hx").write_text(fixture)
            candidate = fixture_path / "philly-streets.hscript"
            candidate.write_text("function start() {}")
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "DependencyProbe", str(candidate)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_source_class_diagnostics_are_wired_into_stage_scan(self):
        source = (ROOT / "source/ImportWorkflow.hx").read_text()
        inspect = source[source.index("static function inspectChart(") : source.index(
            "static function addRegistryAssets(", source.index("static function inspectChart(")
        )]
        psych_helpers = source[source.index("static function psychSourceStageForChart(") : source.index(
            "static function chartBelongsToVSlice(", source.index("static function psychSourceStageForChart(")
        )]
        self.assertIn("PsychSourceStageCompat.resolve", psych_helpers)
        self.assertIn("psychSourceStageForChart", inspect)
        self.assertIn("unsupported-engine-behavior", inspect)
        self.assertIn("sourcePath", inspect)
        self.assertIn("psychStageImplementationFound", inspect)
        self.assertIn("stage JSON metadata does not implement the compiled stage class", source)

        runtime = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("psychCompiledStageClassForCurrentSong", runtime)
        self.assertIn("compiled stage class behavior is not executed", runtime)


if __name__ == "__main__":
    unittest.main()
