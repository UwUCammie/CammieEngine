"""Pin and exercise the shared FunkinModchart compatibility layer."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class CodenameModchartTest(unittest.TestCase):
    def test_haxelib_pin_and_narrow_build_macros(self):
        project = ET.parse(ROOT / "Project.xml").getroot()
        libraries = [node.attrib for node in project.findall("haxelib")]
        self.assertIn({"name": "funkin-modchart", "version": "1.2.5"}, libraries)
        flags = [node.attrib for node in project.findall("haxeflag")
                 if node.attrib.get("name") == "--macro"]
        values = [node.get("value") for node in flags]
        self.assertIn("modchart.backend.macros.Macro.includeFiles()", values)
        self.assertNotIn("CodenameModchartBuild.setup()", values)
        self.assertIn("inst funkin-modchart 1.2.5", (ROOT / "run.sh").read_text())

        dependency_macros = ROOT / ".haxelib/funkin-modchart/1,2,5/extraParams.hxml"
        if dependency_macros.exists():
            params = dependency_macros.read_text()
            self.assertIn("flixel.FlxBasic", params)
            self.assertIn("flixel.graphics.tile.FlxDrawTrianglesItem", params)

    def test_adapter_uses_native_timing_lines_and_render_groups(self):
        adapter = (ROOT / "source/modchart/backend/standalone/adapters/cammie/Cammie.hx").read_text()
        for contract in (
            "implements IAdapter", "CodenameModchartClock.beatAtTime",
            "Conductor.bpmChangeMap", "PlayState.effectiveScrollSpeed * 0.45",
            "ps.getCodenameInputLine(player)", "note.codenameOrigin.lineIndex",
            "note.codenameInputLine == null", "note.wasGoodHit",
            "note.isSustainNote ? 2 : 1", "ps.opponentStrumline",
            "ps.playerStrumline", "ps.camHUD", "sourceStrumline",
            "_fmVisible", "funkin-modchart-unsupported",
        ):
            self.assertIn(contract, adapter, contract)
        self.assertIn("PlayState.SONG", adapter)
        self.assertIn("Reflect.field(ps, 'codenameInputLines')", adapter)
        self.assertIn("Reflect.field(ps, 'unspawnNotes')", adapter)
        self.assertIn("Reflect.field(ps, 'grpNoteSplashes')", adapter)
        self.assertIn("catch (error:Dynamic)", adapter)
        self.assertIn("onModchartingDispose()", adapter)
        self.assertIn("Manager.instance = null", adapter)
        self.assertNotIn("D-Sides", adapter)
        self.assertNotIn("songName ==", adapter)

        splash = (ROOT / "source/NoteSplash.hx").read_text()
        strumline = (ROOT / "source/Strumline.hx").read_text()
        self.assertIn("public var direction:Int", splash)
        self.assertIn("public var sourceStrumline:Null<Strumline>", splash)
        self.assertIn("direction = c;", splash)
        self.assertIn("newsplash.sourceStrumline = this;", strumline)

    def test_piecewise_song_clock_executes_bpm_change_boundaries(self):
        fixture = r'''
class Main {
    static function check(actual:Float, expected:Float, label:String):Void {
        if (Math.abs(actual - expected) > 0.000001)
            throw label + ": expected " + expected + ", got " + actual;
    }
    static function main():Void {
        var map:Array<Dynamic> = [
            {stepTime:8, songTime:1000.0, bpm:60.0},
            {stepTime:14, songTime:2500.0, bpm:180.0}
        ];
        check(CodenameModchartClock.beatAtTime(500, 120, map), 1, "initial segment");
        check(CodenameModchartClock.beatAtTime(1000, 120, map), 2, "change boundary");
        check(CodenameModchartClock.beatAtTime(2000, 120, map), 3, "middle segment");
        check(CodenameModchartClock.beatAtTime(3000, 120, map), 5, "second change");
        check(CodenameModchartClock.crochetAtTime(3000, 120, map), 1000.0 / 3.0, "current crochet");
        var rejected = false;
        try CodenameModchartClock.beatAtTime(1500, 120, [
            {stepTime:12, songTime:1500.0, bpm:90.0},
            {stepTime:8, songTime:1000.0, bpm:60.0}
        ]) catch (_:Dynamic) rejected = true;
        if (!rejected) throw "unsorted BPM map was accepted";
    }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work},
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
