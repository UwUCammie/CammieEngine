"""Focused coverage for the bounded native foreign extra-strumline model."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR_ROOT = Path(os.environ.get(
    "HXC_DONOR_ROOT",
    "/run/media/cammie/External Storage/FNF-Example-Mods",
))
DOKI = DONOR_ROOT / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc"
DOKI_CHART = DONOR_ROOT / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/dokidoggle/dokidoggle-chart.json"


def extract_class(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated class: {marker}")


def hx_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class ExtraStrumlineAdapterTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Main.hx"
            path.write_text(source, newline='\n')
            command = [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                       "-main", "Main", "--interp"]
            return subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=300)

    def test_source_exposes_owned_lifecycle_and_no_song_branch(self):
        source = (ROOT / "source/ExtraStrumlineAdapter.hx").read_text()
        for marker in (
            "CompatSongDifficultyView",
            "ExtraStrumlineAdapter",
            "applyNoteData",
            "processNotes",
            "hitNote",
            "missNote",
            "clean",
            "handleSkippedNotes",
            "vwooshNotes",
            "onNoteIncoming",
            "setNoteSpacing",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("if (song ==", source.lower())
        self.assertNotIn("switch (song", source.lower())

    def test_flattened_chart_view_copies_side_direction_and_sustain(self):
        source = (ROOT / "source/ExtraStrumlineAdapter.hx").read_text()
        note_data = extract_class(source, "class CompatSongNoteData")
        chart_view = extract_class(source, "class CompatSongDifficultyView")
        fixture = f'''{note_data}
{chart_view}
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var firstRows:Array<Dynamic> = [];
    var firstHead:Array<Dynamic> = [1000, 0, 0];
    var firstHold:Array<Dynamic> = [1200, 4, 300, "normal"];
    firstRows.push(firstHead);
    firstRows.push(firstHold);
    var secondRows:Array<Dynamic> = [];
    var secondHead:Array<Dynamic> = [1400, 1, 0];
    var secondHold:Array<Dynamic> = [1600, 5, 100];
    secondRows.push(secondHead);
    secondRows.push(secondHold);
    var sections:Array<Dynamic> = [];
    sections.push({{mustHitSection: true, sectionNotes: firstRows}});
    sections.push({{mustHitSection: false, sectionNotes: secondRows}});
    var chart:Dynamic = {{
      song: "doki", bpm: 150, speed: 2.6, preferredNoteAmount: 4, notes: sections
    }};
    var view = new CompatSongDifficultyView(chart);
    if (view.notes.length != 4) fail("flatten count: " + view.notes.length);
    if (view.notes[0].getStrumlineIndex() != 0 || view.notes[0].getDirection() != 0)
      fail("player ownership");
    if (view.notes[1].getStrumlineIndex() != 1 || view.notes[1].sustainLength != 300)
      fail("opponent ownership/sustain");
    if (view.notes[2].getStrumlineIndex() != 1 || view.notes[3].getStrumlineIndex() != 0)
      fail("inverted section ownership");
    view.sections[0].sectionNotes[0][0] = 7777;
    if (chart.notes[0].sectionNotes[0][0] != 1000) fail("sections retained donor row");
    chart.notes[0].sectionNotes[0][0] = 9999;
    if (view.notes[0].strumTime != 1000) fail("view retained donor row");
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Main.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file() and DOKI.is_file() and DOKI_CHART.is_file(),
                         "portable Haxe or mounted DokiDoggle HXC unavailable")
    def test_donor_is_read_only_and_extra_lifecycle_calls_are_present(self):
        before = {
            DOKI: hashlib.sha256(DOKI.read_bytes()).hexdigest(),
            DOKI_CHART: hashlib.sha256(DOKI_CHART.read_bytes()).hexdigest(),
        }
        donor = DOKI.read_text(errors="ignore")
        for call in (
            "new Strumline",
            "applyNoteData",
            "extraStrumline.notes",
            "extraStrumline.holdNotes",
            "hitNote",
            "clean",
            "handleSkippedNotes",
        ):
            self.assertIn(call, donor)
        chart = json.loads(DOKI_CHART.read_text())
        extra = chart.get("notes", {}).get("extra", [])
        self.assertGreater(len(extra), 0)
        self.assertTrue(all({"t", "d", "l"}.issubset(note) for note in extra))
        self.assertTrue(all(4 <= int(note["d"]) <= 7 for note in extra))
        for path, digest in before.items():
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())

    @unittest.skipUnless(HAXE.is_file() and DOKI.is_file(),
                         "portable Haxe or mounted DokiDoggle HXC unavailable")
    def test_donor_generated_hscript_routes_and_executes_extra_lifecycle(self):
        """The real donor must lower to the bounded adapter contract.

        The small executable probe mirrors the donor's reachable extra-line
        callbacks.  It uses stubs only for the HXC host objects, so the test
        verifies generated-HScript dispatch without launching the game or
        copying/rewriting donor assets.
        """
        donor = DOKI.read_text(errors="ignore")
        before = hashlib.sha256(DOKI.read_bytes()).hexdigest()
        probe = r'''class DokiDoggleSong extends Song {
  var extraStrumline;
  function onSongLoaded(event) { summonExtraStrumline(); }
  function summonExtraStrumline() {
    var extraNoteData:Array<SongNoteData> = [];
    var animChart = PlayState.instance.currentSong.getDifficulty('extra');
    for (notes in animChart.notes) extraNoteData.push(notes);
    var noteStylePlayer:NoteStyle = NoteStyleRegistry.instance.fetchEntry(
      PlayState.instance.playerStrumline.noteStyle.id);
    extraStrumline = new Strumline(noteStylePlayer, false);
    extraStrumline.onNoteIncoming.add(PlayState.instance.onStrumlineNoteIncoming);
    PlayState.instance.add(extraStrumline);
    extraStrumline.applyNoteData(extraNoteData);
  }
  function onUpdate(event:UpdateScriptEvent) {
    if (extraStrumline != null) processNotes(event);
  }
  function processNotes(elapsed:Float) {
    for (note in extraStrumline.notes.members) {
      var result = GRhythmUtil.processWindow(note, false);
      if (result.botplayHit) extraStrumline.hitNote(note);
    }
    for (holdNote in extraStrumline.holdNotes.members) {
      if (holdNote.hitNote && !holdNote.missedNote && holdNote.sustainLength > 0)
        extraStrumline.playNoteHoldCover(holdNote.holdNoteSprite);
    }
  }
  function onSongRetry(event) {
    extraStrumline.vwooshNotes();
    extraStrumline.clean();
    extraStrumline.handleSkippedNotes();
  }
}'''
        main = f'''import hscript.Interp;
import hscript.Parser;

class ProbeNoteList {{
  public var members:Array<Dynamic>;
  public function new(?values:Array<Dynamic>) members = values == null ? [] : values;
}}
class ProbeSignal {{
  public var added:Int = 0;
  public function new() {{}}
  public function add(callback:Dynamic):Void added++;
}}
class ProbeStrumline {{
  public static var last:ProbeStrumline;
  public var notes:ProbeNoteList;
  public var holdNotes:ProbeNoteList;
  public var noteStyle:Dynamic;
  public var onNoteIncoming:ProbeSignal;
  public var applyCalls:Int = 0;
  public var hitCalls:Int = 0;
  public var coverCalls:Int = 0;
  public var vwooshCalls:Int = 0;
  public var cleanCalls:Int = 0;
  public var skippedCalls:Int = 0;
  public function new(style:Dynamic, botplay:Bool) {{
    last = this; noteStyle = style; notes = new ProbeNoteList();
    holdNotes = new ProbeNoteList(); onNoteIncoming = new ProbeSignal();
  }}
  public function applyNoteData(values:Array<Dynamic>):Void {{
    applyCalls++; notes.members = values;
    holdNotes.members = [{{hitNote:true, missedNote:false, sustainLength:1,
      holdNoteSprite:{{}}}}];
  }}
  public function hitNote(note:Dynamic):Void hitCalls++;
  public function playNoteHoldCover(note:Dynamic):Void coverCalls++;
  public function vwooshNotes():Void vwooshCalls++;
  public function clean():Void cleanCalls++;
  public function handleSkippedNotes():Void skippedCalls++;
}}
class ProbeRhythm {{
  public static function processWindow(note:Dynamic, player:Bool):Dynamic
    return {{botplayHit:true}};
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function hasBad(result:Dynamic):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-module-body"
        || finding.code == "unsupported-hxc-api"
        || finding.code == "unsupported-hxc-symbol") return true;
    return false;
  }}
  static function main() {{
    var donor = HxcCompat.analyze({hx_string(donor)}, {hx_string(str(DOKI))});
    if (!donor.moduleSafe || !donor.moduleInitializationSafe || hasBad(donor))
      fail("Doki extra-line path remained unsafe: " + donor.moduleSafetyReasons.join(","));
    var generated = donor.generatedHscript;
    for (symbol in ["getDifficulty('extra')", "applyNoteData", "onNoteIncoming",
      "processNotes", "hitNote", "holdNotes", "playNoteHoldCover", "songRetry",
      "vwooshNotes", "clean", "handleSkippedNotes"])
      if (generated.indexOf(symbol) < 0) fail("generated Doki symbol missing: " + symbol);
    if (generated.indexOf("new ExtraStrumlineAdapter") < 0
      || generated.indexOf("new Strumline") >= 0)
      fail("extra-line constructor was not explicitly routed around the native class: " + generated);
    new Parser().parseString(generated);

    var result = HxcCompat.analyze({hx_string(probe)}, "scripts/songs/doki-probe.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe || hasBad(result))
      fail("probe remained unsafe: " + result.moduleSafetyReasons.join(","));
    var state:Dynamic = {{
      currentSong: {{getDifficulty:function(name:String):Dynamic
        return {{notes:[{{id:1}}]}}}},
      playerStrumline: {{noteStyle:{{id:"normal"}}}},
      onStrumlineNoteIncoming:function(note:Dynamic){{}},
      add:function(value:Dynamic){{}}
    }};
    var interp = new Interp();
    // HXC constructor lowering must bypass HScript's native Type.resolveClass
    // lookup for the engine's unrelated Strumline class.
    interp.variables.set("PlayState", {{instance:state}});
    interp.variables.set("ExtraStrumlineAdapter", ProbeStrumline);
    interp.variables.set("NoteStyleRegistry", {{instance:{{fetchEntry:function(id:String):Dynamic
      return {{id:id}}}}}});
    interp.variables.set("ExtraStrumlineNoteStyleRegistry", {{instance:{{fetchEntry:function(id:String):Dynamic
      return {{id:id}}}}}});
    interp.variables.set("GRhythmUtil", ProbeRhythm);
    interp.variables.set("ExtraStrumlineRhythm", ProbeRhythm);
    interp.execute(new Parser().parseString(result.generatedHscript));
    var summon:Dynamic = interp.variables.get("summonExtraStrumline");
    if (summon == null) fail("summonExtraStrumline was not emitted");
    Reflect.callMethod(null, summon, []);
    var line = ProbeStrumline.last;
    if (line == null || line.applyCalls != 1 || line.notes.members.length != 1
      || line.onNoteIncoming.added != 1)
      fail("extra-line construction dispatch");
    Reflect.callMethod(null, interp.variables.get("update"), [0.016]);
    if (line.hitCalls != 1 || line.coverCalls != 1)
      fail("extra-line note/hold dispatch: " + line.hitCalls + "/" + line.coverCalls);
    Reflect.callMethod(null, interp.variables.get("songRetry"), [null]);
    if (line.vwooshCalls != 1 || line.cleanCalls != 1 || line.skippedCalls != 1)
      fail("extra-line retry dispatch");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plugin = (ROOT / "source/PluginManager.hx").read_text()
        for binding in (
            'interp.variables.set("Strumline", ExtraStrumlineAdapter);',
            'interp.variables.set("HxcHealthIconAdapter", HxcHealthIconAdapter);',
            'interp.variables.set("NoteStyleRegistry", ExtraStrumlineNoteStyleRegistry);',
            'interp.variables.set("GRhythmUtil", ExtraStrumlineRhythm);',
        ):
            self.assertIn(binding, plugin)
        self.assertIn("onStrumlineNoteIncoming", (ROOT / "source/PlayState.hx").read_text())
        self.assertEqual(before, hashlib.sha256(DOKI.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
