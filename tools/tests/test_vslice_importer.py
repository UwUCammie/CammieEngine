"""Synthetic-fixture coverage for the standalone V-Slice converter."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
EXAMPLES = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def haxe_string(value: str) -> str:
    """Return a Haxe string literal using JSON's compatible escaping."""

    return json.dumps(str(value))


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class VSliceImporterTest(unittest.TestCase):
    def run_fixture(self, main_source: str, fixture_dir: Path, env=None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main_path = Path(folder) / "Main.hx"
            main_path.write_text(main_source)
            return subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=env,
            )

    def test_unrouted_rows_are_retained_and_survive_editor_save_without_gameplay_notes(self):
        charting = (ROOT / "source/ChartingState.hx").read_text()
        editor_methods = "\n".join(extract_method(charting, marker) for marker in (
            "function loadRawEditorNotes(", "function editorChartFileName(",
            "function editorSongData("))
        main = r'''import haxe.Json;
using StringTools;
class Song {
  public static function storageFolder(chart:Dynamic):String
    return Std.string(Reflect.field(chart, "compatStorageFolder"));
}
class FNFAssets {
  public static var chartText:String;
  public static function exists(_path:String):Bool return chartText != null;
  public static function getText(_path:String):String return chartText;
}
class CoolUtil { public static function parseJson(raw:String):Dynamic return Json.parse(raw); }
class DifficultyIcons { public static function getEndingFP(_difficulty:Int):String return "-normal"; }
class PlayState { public static var storyDifficulty:Int = 0; }
class Main {
  var _song:Dynamic;
''' + editor_methods + r'''
  public function new() {}
  static function fail(message:String):Void throw message;
  static function main():Void {
    var sourceRows:Array<Dynamic> = [
      {t:100, d:0, l:0, k:"normal"},
      {t:200, d:12, l:25, k:"normal", authored:{token:"first-extra"}},
      {t:"invalid", d:8, l:0, k:"normal", authored:{token:"second-extra"}},
      {t:350, d:-4, l:0, k:"normal", authored:{token:"negative-line"}},
      {t:400, d:2, l:0, k:"normal"}
    ];
    var source:Dynamic = {notes:{normal:sourceRows}};
    var metadata:Dynamic = {songName:"fixture", timeChanges:[{t:0, bpm:120}],
      playData:{difficulties:["normal"], characters:{player:"bf", opponent:"dad"}}};
    var converted = VSliceImporter.convertDifficulty(metadata, source, "fixture", "normal");
    var convertedSong:Dynamic = converted.chart.song;
    var retained:Array<Dynamic> = cast convertedSong.vSliceUnroutedNotes;
    if (retained == null || retained.length != 3) fail("unrouted source rows missing");
    if (Json.stringify(retained) != Json.stringify([sourceRows[1], sourceRows[2], sourceRows[3]]))
      fail("raw unrouted note payload/order changed");
    var playable = 0;
    for (section in (cast convertedSong.notes:Array<Dynamic>))
      playable += (cast section.sectionNotes:Array<Dynamic>).length;
    if (playable != 2) fail("unrouted rows entered gameplay notes");

    // Model the installed chart plus ChartingState's real selected-file load/save path.
    FNFAssets.chartText = Json.stringify(converted.chart);
    var loaded:Dynamic = Json.parse(FNFAssets.chartText).song;
    loaded.compatStorageFolder = "fixture-owner";
    loaded.compatChartFileName = "fixture-normal";
    var editor = new Main();
    editor._song = loaded;
    editor.loadRawEditorNotes();
    var saved = editor.editorSongData();
    var savedRows:Array<Dynamic> = cast saved.vSliceUnroutedNotes;
    if (savedRows == null || Json.stringify(savedRows) != Json.stringify(retained))
      fail("editor Quick Save lost raw unrouted rows");
    var savedPlayable = 0;
    for (section in (cast saved.notes:Array<Dynamic>))
      savedPlayable += (cast section.sectionNotes:Array<Dynamic>).length;
    if (savedPlayable != 2) fail("editor metadata was merged into playable note rows");
  }
}
'''
        result = self.run_fixture(main, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_health_icon_reference_maps_into_the_selected_owner_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            icon_folder = root / "images/icons"
            icon_folder.mkdir(parents=True)
            (icon_folder / "icon-our-harmony.png").write_bytes(b"donor-png")
            (icon_folder / "icon-our-harmony.xml").write_text("<TextureAtlas />")
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var mappings = VSliceImporter.hxcHealthIconMappings({haxe_string(str(root))}, "our-harmony");
    if (mappings == null || mappings.length != 2) fail("HXC icon bundle count");
    var png = false;
    var xml = false;
    for (mapping in mappings) {{
      if (mapping.destination == "images/icons/icon-our-harmony.png"
        && mapping.source.indexOf("icon-our-harmony.png") >= 0) png = true;
      if (mapping.destination == "images/icons/icon-our-harmony.xml"
        && mapping.source.indexOf("icon-our-harmony.xml") >= 0) xml = true;
    }}
    if (!png || !xml) fail("icon assets lost their owner namespace or atlas pair");
    if (VSliceImporter.hxcHealthIconMappings({haxe_string(str(root))}, "bf") != null)
      fail("native health icon should not create an imported asset");
    if (VSliceImporter.hxcHealthIconMappings({haxe_string(str(root))}, "missing-icon").length != 0)
      fail("missing health icon was guessed");
  }}
}}'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_safe_package_character_definitions_and_atlas_pairs_are_discovered(self):
        """Dynamic V-Slice character choices import from the selected package."""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            primary = root / "data/characters"
            secondary = root / "shared/characters"
            primary.mkdir(parents=True)
            secondary.mkdir(parents=True)
            (primary / "ghost-sketch.json").write_text("{}")
            (primary / "unsafe name.json").write_text("{}")
            (primary / "nested.json").mkdir()
            (secondary / "GHOST-SKETCH.json").write_text("{}")
            (secondary / "ghost.json").write_text("{}")

            media = root / "shared/images/characters/ghost"
            media.mkdir(parents=True)
            (media / "Libitina_tmp.png").write_bytes(b"ghost atlas")
            (media / "Libitina_tmp.xml").write_text("<TextureAtlas />")
            missing = root / "shared/images/characters/yuri"
            missing.mkdir(parents=True)
            (missing / "gore.xml").write_text("<TextureAtlas />")

            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var names = VSliceImporter.characterDefinitionNames([
      {haxe_string(str(primary))}, {haxe_string(str(secondary))},
      {haxe_string(str(root / "data/characters/absent"))}
    ]);
    if (names.length != 2) fail("safe definition count " + names.join(","));
    if (names[0] != "ghost-sketch" || names[1] != "ghost")
      fail("deterministic owner definitions " + names.join(","));
    var definition = {{assetPath:"characters/ghost/Libitina_tmp",
      animations:[{{name:"idle", prefix:"idle", fps:24, loop:true}}]}};
    var converted = VSliceImporter.convertCharacter(definition,
      {haxe_string(str(root))}, "ghost-sketch", false);
    if (Reflect.field(converted, "supported") != true) fail("paired primary atlas was marked incomplete");
    var png = false;
    var xml = false;
    for (mapping in converted.assets) {{
      if (mapping.destination == "char.png" && mapping.source.indexOf("Libitina_tmp.png") >= 0) png = true;
      if (mapping.destination == "char.xml" && mapping.source.indexOf("Libitina_tmp.xml") >= 0) xml = true;
    }}
    if (!png || !xml) fail("character PNG/XML sidecar pair was not mapped");
    var incomplete = VSliceImporter.convertCharacter({{assetPath:"characters/yuri/gore",
      animations:[{{name:"idle", prefix:"idle", fps:24}}]}},
      {haxe_string(str(root))}, "yuri-gore", false);
    if (Reflect.field(incomplete, "supported") == true) fail("definition without a PNG became playable");
    var diagnosed = false;
    for (finding in incomplete.diagnostics)
      if (finding.code == "missing-asset") diagnosed = true;
    if (!diagnosed) fail("missing donor media diagnostic was lost");
  }}
}}'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_primary_character_remains_playable_when_optional_death_atlas_is_absent(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            atlas = root / "shared/images/characters/hero"
            atlas.mkdir(parents=True)
            (atlas / "main.png").write_bytes(b"main atlas")
            (atlas / "main.xml").write_text('<TextureAtlas><SubTexture name="idle0000"/></TextureAtlas>')
            main = f'''class Main {{
  static function main() {{
    var data = {{assetPath:"characters/hero/main", animations:[
      {{name:"idle",prefix:"idle",fps:24}},
      {{name:"firstDeath",assetPath:"characters/hero/missing-death",prefix:"death",fps:24}}
    ]}};
    var result = VSliceImporter.convertCharacter(data, {haxe_string(str(root))}, "hero", false);
    if (Reflect.field(result, "supported") != true) throw "primary art was rejected";
    if (result.hscript.indexOf('addByPrefix("idle"') < 0) throw "playable animation lost";
    if (result.hscript.indexOf('addByPrefix("firstDeath"') >= 0) throw "missing death atlas registered";
    var diagnosed = false;
    for (finding in result.diagnostics)
      if (finding.code == "animation-asset-switch") diagnosed = true;
    if (!diagnosed) throw "missing death atlas was hidden";
  }}
}}'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_character_discovery_routes_supported_defs_to_owner_namespace(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        visuals = source[source.index("static function importVSliceVisuals("):]
        visuals = visuals[:visuals.index("\n\tstatic function ")]
        discovery = source[source.index("static function discoverVSliceSongImports("):]
        discovery = discovery[:discovery.index("\n\tstatic function ")]
        self.assertIn("VSliceImporter.characterDefinitionNames(", discovery)
        self.assertIn("vSliceDefinitionFolders(root, 'character')", discovery)
        self.assertIn("Reflect.field(conversion, 'supported') == true", discovery)
        self.assertIn("var characterAssetRoot = songData.engine == ImportEngine.V_SLICE", visuals)
        self.assertIn("CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine)", visuals)
        self.assertIn("importVSliceCharacterConversion(converted, result, characterAssetRoot", visuals)
        self.assertIn("Reflect.field(conversion, 'supported') == false", source)

    def test_converted_events_keep_payloads_and_avoid_native_sort(self):
        # hxcpp's native Array.sort corrupted the converted event groups into
        # bare [time, 0] rows, silently dropping every imported V-Slice event
        # payload (camera work, character swaps, lyrics). Pin both the sorted
        # output shape and the hand-rolled sort that avoids the corruption.
        source = (ROOT / "source/VSliceImporter.hx").read_text()
        convert_events = source[source.index("static function convertEvents"):]
        convert_events = convert_events[:convert_events.index("\n\tstatic function ")]
        self.assertNotIn(".sort(", convert_events.replace("// hxcpp's native Array.sort", ""))
        metadata = {
            "version": "2.2.0",
            "songName": "Sort Probe",
            "playData": {"difficulties": ["normal"], "stage": "stage"},
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 2.0},
            "notes": {"normal": []},
            "events": [
                {"t": 300, "e": "FocusCamera", "v": {"x": 5, "y": -6, "char": 1}},
                {"t": 100, "e": "FocusCamera", "v": {"x": 1, "y": 2, "char": 0}},
                {"t": 100, "e": "ZoomCamera", "v": {"mode": "stage"}},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "meta.json"
            chart_path = fixture / "chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convert(Json.parse(sys.io.File.getContent({haxe_string(str(metadata_path))})),
      Json.parse(sys.io.File.getContent({haxe_string(str(chart_path))})), {haxe_string(str(fixture))});
    var events:Array<Dynamic> = result.charts[0].chart.song.events;
    if (events.length != 2) fail("grouped event count " + events.length);
    if (events[0][0] != 100) fail("events are not sorted by time");
    if (events[0][1].length != 2) fail("same-time events did not merge into one group");
    if (events[0][1][0][0] != "FocusCamera") fail("authored kind not preserved");
    if (events[1][0] != 300) fail("second group time");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v2_difficulties_identity_notes_tempo_events_and_diagnostics(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Synthetic V-Slice",
            "artist": "Synthetic Artist",
            "playData": {
                "difficulties": ["normal", "hard"],
                "album": "synthetic-album",
                "characters": {
                    "player": "m1ku",
                    "opponent": "dad",
                    "girlfriend": "miku-gf",
                    "opponentVocals": ["dad"],
                },
                "stage": "concert",
            },
            "timeChanges": [
                {"t": 0, "bpm": 120, "n": 4, "d": 4},
                {"t": 4000, "bpm": 180, "n": 3, "d": 4},
            ],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 2.0, "hard": 2.5},
            "notes": {
                "normal": [
                    {"t": 1000, "d": 2, "l": 125.5, "k": "alt-anim"},
                    {"t": 4100, "d": 6, "l": 250},
                    {"t": 4300, "d": 1, "l": 20, "k": "noanim"},
                ],
                "hard": [
                    {"t": 100, "d": 0, "k": "noanim"},
                ],
            },
            "events": [
                {"t": 100, "e": "FocusCamera", "v": {"x": 12, "y": -4, "char": 1, "duration": 6, "ease": "quart", "easeDir": "Out"}},
                {"t": 200, "e": "ChangeCharacter", "v": {"character": "dad", "newchar": "m1ku"}},
                {"t": 300, "e": "PlayAnimation", "v": {"target": "dad", "anim": "hey"}},
                {"t": 400, "e": "untranslated-custom-event", "v": {}},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "synthetic-metadata.json"
            chart_path = fixture / "synthetic-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            source_path = haxe_string(str(fixture))
            metadata_path_hx = haxe_string(str(metadata_path))
            chart_path_hx = haxe_string(str(chart_path))
            main = f'''import haxe.Json;
using StringTools;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({metadata_path_hx}, {chart_path_hx}, {source_path});
    if (result.charts.length != 2) fail("difficulty count");
    if (result.charts[0].fileName != "synthetic-v-slice.json") fail("normal file name");
    if (result.charts[1].fileName != "synthetic-v-slice-hard.json") fail("hard file name");
            var normal:Dynamic = result.charts[0].chart.song;
            if (normal.song != "Synthetic V-Slice") fail("song identity");
            if (normal.songArtist != "Synthetic Artist" || normal.album != "synthetic-album") fail("song metadata");
    if (normal.player1 != "m1ku" || normal.player2 != "dad" || normal.gf != "miku-gf" || normal.stage != "concert") fail("visual identity");
    if (normal.speed != 2) fail("normal speed");
    if (!normal.needsVoices) fail("vocal metadata");
    var sections:Array<Dynamic> = cast normal.notes;
    var notes:Array<Dynamic> = [];
    for (section in sections) for (row in (cast section.sectionNotes:Array<Dynamic>)) notes.push(row);
    if (notes.length != 3) fail("note count");
    var first:Array<Dynamic> = cast notes[0];
    if (first[0] != 1000 || first[1] != 2 || first[2] != 125.5 || first[3] != 1) fail("lane/sustain/alt");
    // Known V-Slice aliases still stay addressable through native noteInfo data;
    // they must not be flattened to the normal lane block.
    var generic:Array<Dynamic> = cast notes[2];
    if (generic[1] != 41) fail("generic note kind lane marker");
    if (result.noteDefinitions.length != 1) fail("note definition count");
    if (result.noteDefinitions[0].sourceKind != "noanim") fail("note source kind");
    if (result.noteDefinitions[0].sourceNoteType != "No Animation"
      || result.noteDefinitions[0].shouldSing != false) fail("native no-animation semantics");
    if (result.noteDefinitions[0].id.indexOf("vslice:noanim:") != 0) fail("note source id");
    if (result.eventCharacterReferences.length != 1 || result.eventCharacterReferences[0] != "m1ku") fail("event character reference");
    if (result.eventCharacterSlots.length != 1
      || result.eventCharacterSlots[0].reference != "m1ku"
      || result.eventCharacterSlots[0].slot != "dad") fail("event character slot");
    var hardSections:Array<Dynamic> = cast result.charts[1].chart.song.notes;
    var hardRow:Array<Dynamic> = cast (cast hardSections[0].sectionNotes:Array<Dynamic>)[0];
    if (hardRow[1] != 40) fail("shared note definition index");
    var changed = false;
    for (section in sections) if (section.changeBPM) changed = true;
    if (!changed) fail("tempo change");
    var events:Array<Dynamic> = cast normal.events;
    if (events.length != 4) fail("preserved event count");
    if (events[0][1][0][0] != "FocusCamera") fail("focus authored kind");
    var focusRoute = EngineCompat.routeLegacyEvent("FocusCamera", events[0][1][0][1], events[0][1][0][2], events[0][1][0][3]);
    if (focusRoute == null || focusRoute.name != "Focus Camera") fail("focus runtime route");
    var focusOptions = EngineCompat.eventOptions(focusRoute.v3);
    if (focusOptions == null || focusOptions.char != 1 || focusOptions.duration != 6
      || focusOptions.ease != "quart" || focusOptions.easeDir != "Out") fail("focus payload");
    var charRoute = EngineCompat.routeLegacyEvent("ChangeCharacter", events[1][1][0][1], events[1][1][0][2], events[1][1][0][3]);
    if (charRoute == null || charRoute.name != "Change Character" || charRoute.v1 != "dad" || charRoute.v2 != "m1ku") fail("character event route");
    var animRoute = EngineCompat.routeLegacyEvent("PlayAnimation", events[2][1][0][1], events[2][1][0][2], events[2][1][0][3]);
    if (animRoute == null || animRoute.name != "Play Animation" || animRoute.v1 != "hey" || animRoute.v2 != "dad") fail("animation event route");
    if (events[3][1][0][0] != "untranslated-custom-event" || events[3][1][0][1] != "{{}}") fail("foreign event identity/payload");
    var sawKind = false;
    var sawNativeKind = false;
    var sawEvent = false;
    for (finding in result.diagnostics) {{
      if (finding.code == "note-kind-generic") sawKind = true;
      if (finding.code == "note-kind-native") sawNativeKind = true;
      if (finding.code == "foreign-event-preserved") sawEvent = true;
    }}
    if (sawKind || !sawNativeKind || !sawEvent) fail("kind/event diagnostics");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_declared_variation_metadata_converts_its_own_chart_and_vocal_roles(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Synthetic Mix",
            "playData": {
                "songVariations": ["alt", "lyrics", "alt"],
                "difficulties": ["alt"],
                "characters": {
                    "player": "bf-alt",
                    "opponent": "dad",
                    "playerVocals": ["bf-alt"],
                    "opponentVocals": ["dad-alt"],
                    "instrumental": "alt",
                },
                "stage": "mall",
                "noteStyle": "pixel",
            },
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"alt": 2.4},
            "notes": {"alt": [{"t": 321, "d": 4, "l": 77}]},
            "events": [{"t": 500, "e": "FocusCamera", "v": {"x": 20, "y": -5, "char": 1}}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "metadata.json"
            chart_path = fixture / "chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main():Void {{
    var metadata = Json.parse(sys.io.File.getContent({haxe_string(str(metadata_path))}));
    var chart = Json.parse(sys.io.File.getContent({haxe_string(str(chart_path))}));
    var variations = VSliceImporter.songVariationReferences(metadata);
    if (variations.length != 2 || variations[0] != "alt" || variations[1] != "lyrics")
      fail("variation ids were not stable and de-duplicated");
    var vocalRefs = VSliceImporter.vocalStemReferences(metadata);
    if (vocalRefs.length != 2 || vocalRefs[0].id != "dad-alt" || vocalRefs[0].role != "opponent"
      || vocalRefs[1].id != "bf-alt" || vocalRefs[1].role != "player")
      fail("explicit vocal role order was not preserved");
    var converted = VSliceImporter.convert(metadata, chart, "variation-fixture");
    if (converted.charts.length != 1 || converted.charts[0].difficulty != "alt"
      || converted.charts[0].fileName != "synthetic-mix-alt.json")
      fail("variant difficulty was lost");
    var song = converted.charts[0].chart.song;
    if (song.player1 != "bf-alt" || song.player2 != "dad" || song.stage != "mall" || song.uiType != "pixel")
      fail("variant presentation metadata was lost");
    var sections:Array<Dynamic> = cast song.notes;
    var firstSection:Dynamic = sections[0];
    var sectionNotes:Array<Dynamic> = cast firstSection.sectionNotes;
    var firstRow:Array<Dynamic> = cast sectionNotes[0];
    if (sectionNotes.length != 1 || firstRow[0] != 321 || firstRow[1] != 4 || firstRow[2] != 77)
      fail("variant note payload was not converted");
    var eventGroups:Array<Dynamic> = cast song.events;
    var firstEventGroup:Array<Dynamic> = cast eventGroups[0];
    var eventRows:Array<Dynamic> = cast firstEventGroup[1];
    var firstEventRow:Array<Dynamic> = cast eventRows[0];
    if (eventGroups.length != 1 || firstEventGroup[0] != 500 || firstEventRow[0] != "FocusCamera")
      fail("variant events were not converted");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_declared_difficulties_exclude_empty_placeholder_keys(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Alt Pair",
            "playData": {
                "difficulties": ["alt"],
                "characters": {"player": "variant-player", "opponent": "opponent"},
            },
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 2.0, "alt": 2.0},
            "notes": {
                "normal": [],
                "alt": [{"t": 420, "d": 2, "l": 75}],
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "metadata.json"
            chart_path = fixture / "chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))},
      {haxe_string(str(chart_path))});
    if (result.charts.length != 1 || result.charts[0].difficulty != "alt")
      fail("metadata-declared difficulty set included the empty normal placeholder");
    var sections:Array<Dynamic> = cast result.charts[0].chart.song.notes;
    var count = 0;
    var first:Array<Dynamic> = null;
    for (section in sections) for (row in (cast section.sectionNotes:Array<Dynamic>)) {{
      count++;
      if (first == null) first = cast row;
    }}
    if (count != 1 || first[0] != 420 || first[1] != 2 || first[2] != 75)
      fail("selected variation notes did not match the declared difficulty");

    var fallback = VSliceImporter.convert(
      {{version:"2.2.0", songName:"Legacy Pair", playData:{{}}}},
      {{version:"2.0.0", notes:{{normal:[], hard:[]}}}});
    if (fallback.charts.length != 2 || fallback.charts[0].difficulty != "normal"
      || fallback.charts[1].difficulty != "hard")
      fail("chart keys were not used when metadata has no difficulty list");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_camera_flash_route_preserves_step_duration_and_target(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var hud = EngineCompat.routeVSliceEvent(
      "extra-events-cameraFlashEvent", {duration: 15, applyToHud: true, color: 12});
    if (hud.name != "Camera Flash" || hud.v1 != "hud" || hud.v2 != "15")
      fail("HUD camera flash route");
    var hudOptions = EngineCompat.eventOptions(hud.v3);
    if (hudOptions == null || hudOptions.duration != 15 || hudOptions.color != 12
      || hudOptions.applyToHud != true || hudOptions.durationSteps != true)
      fail("HUD camera flash options");

    var game = EngineCompat.routeVSliceEvent(
      "extra-events-cameraFlashEvent", {duration: 25, applyToHud: false, color: 12});
    if (game.name != "Camera Flash" || game.v1 != "12" || game.v2 != "25")
      fail("game camera flash route");
    var gameOptions = EngineCompat.eventOptions(game.v3);
    if (gameOptions == null || gameOptions.durationSteps != true)
      fail("game camera flash step marker");

    // Psych/FPS legacy rows retain their seconds/color ABI and must not pick
    // up the V-Slice step marker merely because they share the native event.
    var legacy = EngineCompat.routeVSliceEvent("Flash Camera", {value1: "4", value2: ""});
    if (legacy.name != "Camera Flash" || legacy.v1 != "4" || legacy.v2 != "")
      fail("legacy camera flash route");
    if (EngineCompat.eventOptions(legacy.v3) != null)
      fail("legacy camera flash options");
  }
}'''
        result = self.run_fixture(main, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_stock_note_style_maps_to_native_ui_without_chart_edits(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Pixel Style Fixture",
            "playData": {
                "difficulties": ["normal"],
                "noteStyle": "pixel",
                "characters": {"player": "bf", "opponent": "dad"},
            },
        }
        chart = {"version": "2.0.0", "notes": {"normal": [{"t": 0, "d": 0}]}}
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            pixel_metadata = fixture / "pixel-metadata.json"
            pixel_chart = fixture / "pixel-chart.json"
            pixel_metadata.write_text(json.dumps(metadata))
            pixel_chart.write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var pixel = VSliceImporter.convertFiles({haxe_string(str(pixel_metadata))}, {haxe_string(str(pixel_chart))});
    if (pixel.charts[0].chart.song.uiType != "pixel") fail("pixel noteStyle was flattened");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_custom_note_style_converts_separate_atlases_and_hold_pairs(self):
        style = {
            "version": "1.1.0",
            "name": "Example Style",
            "assets": {
                "note": {"assetPath": "shared:notes/example", "scale": 0.7,
                          "data": {"left": {"prefix": "noteLeft"}, "down": {"prefix": "noteDown"},
                                    "up": {"prefix": "noteUp"}, "right": {"prefix": "noteRight"}}},
                "noteStrumline": {"assetPath": "shared:receptors/example", "scale": 0.75,
                                   "offsets": [4, 5], "data": {
                                       "leftStatic": {"prefix": "staticLeft0"},
                                       "leftPress": {"prefix": "pressLeft0"},
                                       "leftConfirm": {"prefix": "confirmLeft0"},
                                       "leftConfirmHold": {"prefix": "loopLeft0"},
                                       "downStatic": {"prefix": "staticDown0"},
                                       "downPress": {"prefix": "pressDown0"},
                                       "downConfirm": {"prefix": "confirmDown0"},
                                       "downConfirmHold": {"prefix": "loopDown0"},
                                       "upStatic": {"prefix": "staticUp0"},
                                       "upPress": {"prefix": "pressUp0"},
                                       "upConfirm": {"prefix": "confirmUp0"},
                                       "upConfirmHold": {"prefix": "loopUp0"},
                                       "rightStatic": {"prefix": "staticRight0"},
                                       "rightPress": {"prefix": "pressRight0"},
                                       "rightConfirm": {"prefix": "confirmRight0"},
                                       "rightConfirmHold": {"prefix": "loopRight0"}}},
                "holdNote": {"assetPath": "shared:holds/example", "scale": 0.7},
                "noteSplash": {"assetPath": "shared:splashes/example", "alpha": 0.8,
                                "offsets": [25, -5], "data": {
                                    "enabled": True,
                                    "leftSplashes": [{"prefix": "impactLeft"}],
                                    "downSplashes": [{"prefix": "impactDown"}],
                                    "upSplashes": [{"prefix": "impactUp"}],
                                    "rightSplashes": [{"prefix": "impactRight"}]}},
                "countdownThree": {"data": {"audioPath": "shared:gameplay/countdown/funkin/introTHREE"}},
                "countdownTwo": {"assetPath": "shared:ui/countdown/example/ready",
                                  "data": {"audioPath": "shared:gameplay/countdown/funkin/introTWO"}},
                "countdownOne": {"assetPath": "shared:ui/countdown/example/set",
                                  "data": {"audioPath": "shared:gameplay/countdown/funkin/introONE"}},
                "countdownGo": {"assetPath": "shared:ui/countdown/example/go",
                                 "data": {"audioPath": "shared:gameplay/countdown/funkin/introGO"}},
                "judgementSick": {"assetPath": "default:ui/popup/example/sick", "scale": 0.65}
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for stem in ("shared/images/notes/example", "shared/images/receptors/example",
                         "shared/images/splashes/example"):
                (root / stem).parent.mkdir(parents=True, exist_ok=True)
                (root / (stem + ".png")).write_bytes(b"png")
                (root / (stem + ".xml")).write_text("<TextureAtlas />")
            (root / "shared/images/holds").mkdir(parents=True, exist_ok=True)
            (root / "shared/images/holds/example.png").write_bytes(b"png")
            for stem in ("shared/images/ui/countdown/example/ready", "shared/images/ui/countdown/example/set",
                         "shared/images/ui/countdown/example/go"):
                (root / stem).parent.mkdir(parents=True, exist_ok=True)
                (root / (stem + ".png")).write_bytes(b"png")
            (root / "shared/sounds/gameplay/countdown/funkin").mkdir(parents=True, exist_ok=True)
            for stem in ("introTHREE", "introTWO", "introONE", "introGO"):
                (root / ("shared/sounds/gameplay/countdown/funkin/" + stem + ".ogg")).write_bytes(b"ogg")
            judgement = root / "images/ui/popup/example/sick.png"
            judgement.parent.mkdir(parents=True, exist_ok=True)
            judgement.write_bytes(b"png")
            style_path = root / "style.json"
            style_path.write_text(json.dumps(style))
            main = f'''import haxe.Json;
import sys.io.File;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertNoteStyle(
      Json.parse(File.getContent({haxe_string(str(style_path))})),
      {haxe_string(str(root))}, "Example Style");
    if (!result.supported || result.name != "vslice-example-style") fail("style support/name");
    if (result.registryEntry.noteAsset != "NOTE_assets"
      || result.registryEntry.strumlineAsset != "strumline"
      || result.registryEntry.holdAsset != "hold"
      || result.registryEntry.noteSplashAsset != "noteSplashes") fail("asset routing");
    if (result.registryEntry.holdFramesPerLane != 2) fail("V-Slice hold-pair layout");
    var left:Dynamic = result.preset.definitions.left;
    if (left.note != "noteLeft" || left.confirmHold != "loopLeft0"
      || left.splashes.length != 1 || left.splashes[0] != "impactLeft") fail("prefix preset");
    var destinations = [];
    for (mapping in result.assets) destinations.push(mapping.destination);
    for (required in ["NOTE_assets.png", "NOTE_assets.xml", "strumline.png", "strumline.xml",
      "hold.png", "noteSplashes.png", "noteSplashes.xml", "ready.png", "set.png", "go.png",
      "intro3.ogg", "intro2.ogg", "intro1.ogg", "introGo.ogg", "sick.png"])
      if (destinations.indexOf(required) < 0) fail("missing mapping: " + required);
  }}
}}
'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_countdown_fallback_uses_library_namespace_not_theme_name(self):
        """Missing base-library countdown resources fall back for any theme."""
        style = {
            "version": "1.1.0",
            "name": "Alternate Countdown",
            "assets": {
                "note": {"assetPath": "shared:notes/example"},
                "noteStrumline": {"assetPath": "shared:receptors/example"},
                "countdownThree": {"data": {"audioPath": "shared:gameplay/countdown/alternate/introTHREE"}},
                "countdownTwo": {
                    "assetPath": "shared:ui/countdown/alternate/ready",
                    "data": {"audioPath": "shared:gameplay/countdown/alternate/introTWO"},
                },
                "countdownOne": {
                    "assetPath": "default:ui/countdown/alternate/set",
                    "data": {"audioPath": "default:gameplay/countdown/alternate/introONE"},
                },
                "countdownGo": {
                    "assetPath": "shared:ui/countdown/alternate/go",
                    "data": {"audioPath": "shared:gameplay/countdown/alternate/introGO"},
                },
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for stem in ("shared/images/notes/example", "shared/images/receptors/example"):
                (root / stem).parent.mkdir(parents=True, exist_ok=True)
                (root / (stem + ".png")).write_bytes(b"png")
                (root / (stem + ".xml")).write_text("<TextureAtlas />")
            style_path = root / "style.json"
            style_path.write_text(json.dumps(style))
            main = f'''import haxe.Json;
import sys.io.File;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String, path:String):Bool {{
    var diagnostics:Array<Dynamic> = cast result.diagnostics;
    for (finding in diagnostics)
      if (finding.code == code && finding.message.indexOf(path) >= 0) return true;
    return false;
  }}
  static function main() {{
    var data:Dynamic = Json.parse(File.getContent({haxe_string(str(style_path))}));
    var converted = VSliceImporter.convertNoteStyle(data, {haxe_string(str(root))}, "Alternate Countdown");
    if (!converted.supported) fail("fixture note style should convert");
    if (hasCode(converted, "missing-asset", "ui/countdown/alternate/"))
      fail("namespaced base countdown image emitted a missing-asset warning");
    if (hasCode(converted, "missing-note-style-audio", "gameplay/countdown/alternate/"))
      fail("namespaced base countdown audio emitted a missing-audio warning");
    if (!hasCode(converted, "note-style-countdown-fallback", "Alternate Countdown"))
      fail("aggregate image fallback diagnostic missing");
    if (!hasCode(converted, "note-style-countdown-audio-fallback", "Alternate Countdown"))
      fail("aggregate audio fallback diagnostic missing");

    data.assets.countdownTwo.assetPath = "images/custom-countdown/ready";
    data.assets.countdownTwo.data.audioPath = "sounds/custom-countdown/introTWO";
    var custom = VSliceImporter.convertNoteStyle(data, {haxe_string(str(root))}, "Alternate Countdown");
    if (!hasCode(custom, "missing-asset", "images/custom-countdown/ready"))
      fail("missing custom countdown image warning was suppressed");
    if (!hasCode(custom, "missing-note-style-audio", "sounds/custom-countdown/introTWO"))
      fail("missing custom countdown audio warning was suppressed");
  }}
}}
'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_note_kind_style_is_resolved_by_declared_hxc_style_and_atlas(self):
        """Scripted note kinds may use a style id unrelated to their kind/file name."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data/notestyles").mkdir(parents=True)
            (root / "scripts/notekinds").mkdir(parents=True)
            (root / "shared/images/notes").mkdir(parents=True)
            metadata_path = root / "metadata.json"
            chart_path = root / "chart.json"
            style_path = root / "data/notestyles/rare.json"
            metadata_path.write_text(json.dumps({
                "version": "2.2.0",
                "songName": "Per Kind Style Fixture",
                "playData": {"difficulties": ["normal"]},
            }))
            chart_path.write_text(json.dumps({
                "version": "2.0.0",
                "notes": {"normal": [{"t": 0, "d": 1, "k": "spooky"}]},
            }))
            style_path.write_text(json.dumps({
                "version": "1.1.0",
                "name": "Rare Danger",
                "assets": {"note": {
                    "assetPath": "shared:notes/danger",
                    "scale": 0.8,
                    "offsets": [3, -4],
                    "data": {
                        "left": {"prefix": "Danger Left0"},
                        "down": {"prefix": "Danger Down0"},
                        "up": {"prefix": "Danger Up0"},
                        "right": {"prefix": "Danger Right0"},
                    },
                }},
            }))
            (root / "shared/images/notes/danger.png").write_bytes(b"png")
            (root / "shared/images/notes/danger.xml").write_text("<TextureAtlas />")
            # The adapter id, constructor style id, and script filename are all
            # intentionally distinct, matching real V-Slice NoteKind packs.
            (root / "scripts/notekinds/unrelated-file-name.hxc").write_text('''
import funkin.play.notes.notekind.NoteKind;
class DangerAdapter extends NoteKind {
  public function new() { super("spooky", "Spooky", "rare", []); }
}
''')
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))},
      {haxe_string(str(chart_path))}, {haxe_string(str(root))});
    if (result.noteDefinitions.length != 1) fail("kind definition count");
    var definition = result.noteDefinitions[0];
    if (definition.sourceAdapterClass != "DangerAdapter")
      fail("dedicated NoteKind constructor must win over companion fallback");
    if (definition.sourceNoteStyle != "rare") fail("literal style id discovery");
    if (definition.customNotePath != "assets/images/custom_ui/ui_packs/vslice-rare/NOTE_assets")
      fail("special note atlas destination: " + definition.customNotePath);
    if (definition.animNames[0] != "Danger Left" || definition.animNames[3] != "Danger Right")
      fail("special note prefixes");
    if (definition.customNoteScale != 0.8 || definition.customNoteOffsetX != 3
      || definition.customNoteOffsetY != -4) fail("special note layout");
    if (result.noteStyleConversions.length != 1
      || result.noteStyleConversions[0].conversion.supported)
      fail("partial note-only style should be packaged without claiming a complete UI style");
    var notePng = false;
    var noteXml = false;
    var strumline = false;
    for (mapping in result.noteStyleConversions[0].conversion.assets) {{
      if (mapping.kind == "note-style-note" && mapping.destination == "NOTE_assets.png") notePng = true;
      if (mapping.kind == "note-style-note" && mapping.destination == "NOTE_assets.xml") noteXml = true;
      if (mapping.kind == "note-style-strumline") strumline = true;
    }}
    if (!notePng || !noteXml || strumline) fail("note-kind package asset selection");
    var sawGenericUiWarning = false;
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-note-style") sawGenericUiWarning = true;
    if (sawGenericUiWarning) fail("note-only atlas reported as unsupported full UI style");
  }}
}}'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        note_source = (ROOT / "source/Note.hx").read_text()
        self.assertIn("thingie.customNoteIsPixel", note_source)
        self.assertIn("customNotePath != null && FNFAssets.exists(customNotePath + '.xml')", note_source)
        module_functions = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("importVSliceNoteKindStyleConversion(noteStyle, result)", module_functions)
        self.assertIn("mapping.kind == 'note-style-note' || mapping.kind == 'note-style-hold'", module_functions)

    def test_older_note_info_recovers_selected_root_style_without_rewriting_authored_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "selected"
            other = Path(folder) / "other"
            (root / "scripts/notekinds").mkdir(parents=True)
            (root / "data/notestyles").mkdir(parents=True)
            (root / "images/notes").mkdir(parents=True)
            (other / "images/notes").mkdir(parents=True)
            (root / "scripts/notekinds/unrelated-name.hxc").write_text(
                'class Danger extends NoteKind { function new() { super("danger", "", "warning", []); } }')
            (root / "data/notestyles/warning.json").write_text(json.dumps({
                "assets": {"note": {
                    "assetPath": "shared:notes/danger",
                    "scale": 0.8,
                    "offsets": [3, -4],
                    "data": {
                        "left": {"prefix": "Danger Left0"},
                        "down": {"prefix": "Danger Down0"},
                        "up": {"prefix": "Danger Up0"},
                        "right": {"prefix": "Danger Right0"},
                    },
                }},
            }))
            (root / "images/notes/danger.png").write_bytes(b"png")
            (root / "images/notes/danger.xml").write_text("<TextureAtlas />")
            (other / "images/notes/danger.png").write_bytes(b"png")
            (other / "images/notes/danger.xml").write_text("<TextureAtlas />")
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function old(kind:String):Dynamic return {{
    sourceEngine:"V-Slice", sourceKind:kind, animNames:["purple","blue","green","red"]
  }};
  static function main() {{
    var oldDanger = old("danger");
    var authored = old("danger");
    authored.customNotePath = "assets/images/authored/note";
    var otherKind = old("other");
    var definitions:Array<Dynamic> = [oldDanger, authored, otherKind];
    var selected = {haxe_string(str(root))};
    if (VSliceImporter.applyRuntimeNoteKindStyles(definitions, selected) != 1)
      fail("selected root should restore exactly one old definition");
    if (oldDanger.customNotePath != selected + "/images/notes/danger")
      fail("selected atlas path: " + oldDanger.customNotePath);
    if (oldDanger.animNames[0] != "Danger Left"
      || oldDanger.animNames[3] != "Danger Right")
      fail("native frame-zero prefix was not normalized");
    if (oldDanger.customNoteScale != 0.8
      || oldDanger.customNoteOffsetX != 3 || oldDanger.customNoteOffsetY != -4
      || oldDanger.sourceNoteStyle != "warning")
      fail("runtime note style layout");
    if (authored.customNotePath != "assets/images/authored/note")
      fail("authored atlas was overwritten");
    if (otherKind.customNotePath != null)
      fail("unmatched kind borrowed an atlas");
    var missing:Array<Dynamic> = [old("danger")];
    if (VSliceImporter.applyRuntimeNoteKindStyles(missing, {haxe_string(str(other))}) != 0
      || missing[0].customNotePath != null)
      fail("another root supplied note style metadata");
  }}
}}'''
            result = self.run_fixture(main, root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_stock_popup_and_splash_paths_use_native_fallbacks_only_when_absent(self):
        """Base/shared popup ids are destination-owned, but donor art wins when present."""

        style = {
            "version": "1.1.0",
            "name": "Stock Popup Fallback",
            "assets": {
                "note": {"assetPath": "shared:notes/example"},
                "noteStrumline": {"assetPath": "shared:receptors/example"},
                "noteSplash": {"assetPath": "shared:noteSplashes"},
                "judgementSick": {"assetPath": "shared:ui/popup/funkin/sick"},
                "judgementGood": {"assetPath": "shared:ui/popup/funkin/good"},
                "judgementBad": {"assetPath": "shared:ui/popup/funkin/bad"},
                "judgementShit": {"assetPath": "shared:ui/popup/funkin/shit"},
                "comboNumber0": {"assetPath": "shared:ui/popup/funkin/num0"},
                "comboNumber1": {"assetPath": "shared:ui/popup/funkin/num1"},
                "comboNumber2": {"assetPath": "shared:ui/popup/funkin/num2"},
                "comboNumber3": {"assetPath": "shared:ui/popup/funkin/num3"},
                "comboNumber4": {"assetPath": "shared:ui/popup/funkin/num4"},
                "comboNumber5": {"assetPath": "shared:ui/popup/funkin/num5"},
                "comboNumber6": {"assetPath": "shared:ui/popup/funkin/num6"},
                "comboNumber7": {"assetPath": "shared:ui/popup/funkin/num7"},
                "comboNumber8": {"assetPath": "shared:ui/popup/funkin/num8"},
                "comboNumber9": {"assetPath": "shared:ui/popup/funkin/num9"},
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for stem in ("shared/images/notes/example", "shared/images/receptors/example"):
                (root / stem).parent.mkdir(parents=True, exist_ok=True)
                (root / (stem + ".png")).write_bytes(b"png")
                (root / (stem + ".xml")).write_text("<TextureAtlas />")
            style_path = root / "style.json"
            style_path.write_text(json.dumps(style))
            supplied_root = root / "supplied"
            for stem in ("shared/images/notes/example", "shared/images/receptors/example"):
                (supplied_root / stem).parent.mkdir(parents=True, exist_ok=True)
                (supplied_root / (stem + ".png")).write_bytes(b"png")
                (supplied_root / (stem + ".xml")).write_text("<TextureAtlas />")
            supplied_popup = supplied_root / "shared/images/ui/popup/funkin/sick.png"
            supplied_popup.parent.mkdir(parents=True, exist_ok=True)
            supplied_popup.write_bytes(b"png")
            supplied_style_path = supplied_root / "style.json"
            supplied_style_path.write_text(json.dumps(style))
            main = f'''import haxe.Json;
import sys.io.File;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertNoteStyle(
      Json.parse(File.getContent({haxe_string(str(style_path))})),
      {haxe_string(str(root))}, "Stock Popup Fallback");
    var missing = 0;
    var nativeFallbacks = 0;
    for (finding in result.diagnostics) {{
      if (finding.code == "missing-asset") missing++;
      if (finding.code == "note-style-native-fallback") nativeFallbacks++;
    }}
    if (missing != 0 || nativeFallbacks != 1)
      fail("stock fallback diagnostics: " + missing + "/" + nativeFallbacks);
    if (result.registryEntry.builtInJudgement == true)
      fail("native fallback was mistaken for authored popup art");
    if (result.registryEntry.noteSplashAsset != "")
      fail("native splash fallback did not clear custom asset");
    var stock = 0;
    for (mapping in result.assets)
      if (mapping.destination.indexOf("sick.png") >= 0
          || mapping.destination.indexOf("num0.png") >= 0
          || mapping.destination.indexOf("noteSplashes.png") >= 0)
        stock++;
    if (stock != 0) fail("missing stock files were materialized");

    // A donor-provided file with the same base logical id remains source-backed.
    var suppliedResult = VSliceImporter.convertNoteStyle(
      Json.parse(File.getContent({haxe_string(str(supplied_style_path))})),
      {haxe_string(str(supplied_root))}, "Stock Popup Fallback");
    var authored = false;
    for (mapping in suppliedResult.assets)
      if (mapping.destination == "sick.png") authored = true;
    if (!authored) fail("donor popup was not preserved");
  }}
}}
'''
            result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_vslice_custom_note_styles_are_source_backed(self):
        fixtures = [
            (EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice",
             "HatsuneMiku", "vslice-hatsunemiku"),
            (EXAMPLES / "v-slice/Wacky World UPDATE [V-Slice]",
             "Pomni", "vslice-pomni"),
            (EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE",
             "libitina", "vslice-libitina"),
        ]
        if not all((root / "data/notestyles/" / (name + ".json")).exists() for root, name, _ in fixtures):
            self.skipTest("mounted V-Slice custom note-style fixtures unavailable")
        rows = []
        for root, name, expected in fixtures:
            rows.append("{" + f'root:{haxe_string(str(root))},file:{haxe_string(str(root / "data/notestyles" / (name + ".json")))},expected:{haxe_string(expected)},' + "name:" + haxe_string(name) + "}")
        main = '''import haxe.Json;
import sys.io.File;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var fixtures:Array<Dynamic> = [''' + ",".join(rows) + '''];
    for (fixture in fixtures) {
      var result = VSliceImporter.convertNoteStyle(
        Json.parse(File.getContent(fixture.file)), fixture.root, fixture.name);
      if (!result.supported || result.name != fixture.expected)
        fail("style conversion: " + fixture.name);
      if (result.registryEntry.holdFramesPerLane != 2)
        fail("hold layout: " + fixture.name);
      if (fixture.name == "libitina") {
        if (result.registryEntry.judgementScale != 0.65 || result.registryEntry.comboScale != 0.45)
          fail("Libitina popup scales");
        if (result.registryEntry.builtInJudgement != true)
          fail("Libitina popup assets were not selected");
      }
      var note = false;
      var strumline = false;
      var hold = false;
      var splash = false;
      for (mapping in result.assets) {
        if (mapping.destination == "NOTE_assets.png") note = true;
        if (mapping.destination == "strumline.png") strumline = true;
        if (mapping.destination == "hold.png") hold = true;
        if (mapping.destination == "noteSplashes.png") splash = true;
      }
      if (!note || !strumline || !hold)
        fail("required custom atlas mapping: " + fixture.name);
      // Miku intentionally references a base/shared splash absent from its
      // donor; Pomni and Libitina carry a complete source-backed splash atlas.
      if (fixture.name != "HatsuneMiku" && !splash)
        fail("source-backed splash mapping: " + fixture.name);
      if (fixture.name == "Pomni") {
        if (result.registryEntry.holdCoverEnabled != true)
          fail("Pomni hold-cover runtime flag");
        var coverMappings = 0;
        for (mapping in result.assets)
          if (mapping.destination.indexOf("holdCover") == 0) coverMappings++;
        if (coverMappings != 8) fail("Pomni hold-cover mappings: " + coverMappings);
      } else {
        if (result.registryEntry.holdCoverEnabled == true)
          fail("disabled hold-cover runtime flag: " + fixture.name);
        for (mapping in result.assets)
          if (mapping.destination.indexOf("holdCover") == 0)
            fail("disabled hold-cover mapping: " + fixture.name);
      }
    }
  }
}'''
        result = self.run_fixture(main, EXAMPLES)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        note_source = (ROOT / "source/Note.hx").read_text()
        self.assertIn("holdBitmap.width / (NOTE_AMOUNT * holdFramesPerLane)", note_source)
        self.assertIn("var holdFrame = holdLane * holdFramesPerLane", note_source)
        self.assertIn("var holdEndFrame = holdFramesPerLane > 1 ? holdFrame + 1 : holdFrame", note_source)
        splash_source = (ROOT / "source/NoteSplash.hx").read_text()
        self.assertIn("setupNoteSplash(xPos, yPos, c)", splash_source)
        self.assertIn("curUiType.noteSplashAssetXml == true", splash_source)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("uiSmelly.judgementScale", play_state)
        self.assertIn("uiSmelly.comboScale", play_state)

    def test_vslice_set_health_icon_routes_complete_visual_payload(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var route = EngineCompat.routeVSliceEvent("SetHealthIcon", {
      char: 0,
      id: "face",
      flipX: false,
      isPixel: true,
      offsetX: 12,
      offsetY: -4,
      scale: 1.5,
      shouldBop: false
    });
    if (route == null || route.name != "Set Health Icon"
      || route.v1 != "0" || route.v2 != "face") fail("health icon route");
    var options = EngineCompat.eventOptions(route.v3);
    if (options == null || options.flipX != false || options.isPixel != true
      || options.offsetX != 12 || options.offsetY != -4 || options.scale != 1.5
      || options.shouldBop != false) fail("health icon payload");
    if (EngineCompat.eventName("set health icon") != "Set Health Icon")
      fail("health icon alias");
  }
}'''
        result = self.run_fixture(main, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        health_icon = (ROOT / "source/HealthIcon.hx").read_text()
        self.assertIn("function applyCompatHealthIcon(", play_state)
        self.assertIn("case 'Set Health Icon':", play_state)
        self.assertIn("public var bopBaseSize:Int = 150;", health_icon)
        default_bop = (ROOT / "assets/images/custom_chars/iconbops/default.hscript").read_text()
        test_bop = (ROOT / "assets/images/custom_chars/iconbops/test.hscript").read_text()
        self.assertIn("FlxMath.lerp(icon.bopBaseSize", default_bop)
        self.assertIn("icon.bopPulseSize()", default_bop)
        self.assertIn("FlxMath.lerp(icon.bopBaseSize", test_bop)
        self.assertIn("icon.bopPulseSize()", test_bop)

    def test_mounted_reactor_health_icon_event_uses_native_route(self):
        chart = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/reactor-yuri-mix/reactor-yuri-mix-chart.json"
        if not chart.exists():
            self.skipTest("mounted reactor-yuri-mix chart is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var chart:Dynamic = Json.parse(sys.io.File.getContent({haxe_string(str(chart))}));
    var count = 0;
    for (event in (cast chart.events:Array<Dynamic>)) {{
      if (event.e != "SetHealthIcon") continue;
      var route = EngineCompat.routeVSliceEvent(event.e, event.v);
      if (route == null || route.name != "Set Health Icon"
        || route.v1 != "0" || route.v2 != "face") fail("mounted health icon route");
      var options = EngineCompat.eventOptions(route.v3);
      if (options == null || options.scale != 1 || options.shouldBop != true
        || options.isPixel != false || options.offsetX != 0 || options.offsetY != 0)
        fail("mounted health icon payload");
      count++;
    }}
    if (count != 1) fail("mounted health icon count: " + count);
  }}
}}
'''
        result = self.run_fixture(main, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_standard_stage_variant_is_routed_to_native_stage_and_stage_id(self):
        metadata = {
            "version": "2.2.4",
            "songName": "Stage Variant Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad"},
                "stage": "schoolEvilErect",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 0}]},
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "variant-metadata.json"
            chart_path = fixture / "variant-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            normal_metadata = {**metadata, "playData": {**metadata["playData"], "stage": "schoolEvil"}}
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))});
    var song:Dynamic = result.charts[0].chart.song;
    if (song.stage != "schoolEvil") fail("native stage alias: " + song.stage);
    if (song.stageID != 1) fail("native erect stage id: " + song.stageID);
    var normalMeta = Json.parse({haxe_string(json.dumps(normal_metadata))});
    var normalChart = Json.parse({haxe_string(json.dumps(chart))});
    var normal = VSliceImporter.convert(normalMeta, normalChart).charts[0].chart.song;
    if (normal.stage != "schoolEvil" || normal.stageID != 0) fail("normal stage changed");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matching_hxc_note_adapter_routes_generic_behavior_and_keeps_state_gap(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Adapter Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad"},
                "stage": "stage",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 0, "k": "markov"}]},
        }
        hxc = r'''
class MarkovNotes extends Module {
    var save:Dynamic = DokiPreferences.getDokiSave();
    function new() { super("markov"); }
    function onNoteHit(callback) {
        if (callback.note.noteData.kind == "markov") {
            save.get("hit-count");
            callback.cancelEvent();
        }
    }
    function onNoteMiss(callback) {
        if (callback.note.noteData.kind == "markov") callback.cancelEvent();
    }
    function onSongEnd(event) {
        // The namespaced Doki save is safely isolated by the engine adapter;
        // this native tally still has no equivalent and should remain visible.
        Highscore.tallies.totalNotes--;
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source_root = root / "data/songs/adapter"
            source_root.mkdir(parents=True)
            (root / "scripts/notes").mkdir(parents=True)
            (root / "scripts/notes/markov.hxc").write_text(hxc)
            metadata_path = source_root / "adapter-metadata.json"
            chart_path = source_root / "adapter-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))}, {haxe_string(str(source_root))});
    if (result.noteDefinitions.length != 1) fail("definition count");
    var definition:Dynamic = result.noteDefinitions[0];
    if (definition.sourceAdapter != "HXC" || definition.sourceAdapterClass != "MarkovNotes"
      || definition.genericBehaviorRouted != true) fail("HXC source metadata");
    var routed = false;
    var generic = false;
    var state = false;
    for (finding in result.diagnostics) {{
      if (finding.code == "note-kind-adapter") routed = true;
      if (finding.code == "note-kind-generic") generic = true;
      if (finding.code == "note-kind-state") state = true;
    }}
    if (!routed || generic || state) fail("adapter/state diagnostics");
  }}
}}'''
            result = self.run_fixture(main, root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_active_character_companion_can_own_a_note_kind(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Companion Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf-companion", "opponent": "dad"},
                "stage": "stage",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 4, "k": "hey-anim"}]},
        }
        character_hxc = r'''
class BFCompanion extends SparrowCharacter {
    function new() { super("bf-companion"); }
    function onNoteHit(event) {
        if (event.note.noteData.kind == "hey-anim") {
            holdTimer = 0;
            playAnimation("hey", true);
            return;
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source_root = root / "data/songs/companion-fixture"
            source_root.mkdir(parents=True)
            (root / "scripts/characters").mkdir(parents=True)
            (root / "scripts/characters/bf-companion.hxc").write_text(character_hxc)
            metadata_path = source_root / "companion-fixture-metadata.json"
            chart_path = source_root / "companion-fixture-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))}, {haxe_string(str(source_root))});
    var definition:Dynamic = result.noteDefinitions[0];
    if (definition.sourceAdapter != "HXC" || definition.sourceAdapterClass != "BFCompanion"
      || definition.genericBehaviorRouted != true) fail("character companion metadata");
    var routed = false;
    var generic = false;
    for (finding in result.diagnostics) {{
      if (finding.code == "note-kind-adapter") routed = true;
      if (finding.code == "note-kind-generic") generic = true;
    }}
    if (!routed || generic) fail("character companion diagnostics");
  }}
}}'''
            result = self.run_fixture(main, root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_character_companion_can_own_a_note_kind(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Event Companion Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad"},
                "stage": "stage",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 200, "d": 0, "k": "event-alt"}]},
            "events": [
                {
                    "t": 100,
                    "e": "ChangeCharacter",
                    "v": {"character": "dad", "newchar": "event-companion"},
                }
            ],
        }
        character_hxc = r'''
class EventCompanion extends SparrowCharacter {
    function new() { super("event-companion"); }
    function onNoteHit(event) {
        if (event.note.noteData.kind == "event-alt") {
            holdTimer = 0;
            playAnimation("singLEFT-alt", true);
            return;
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source_root = root / "data/songs/event-companion-fixture"
            source_root.mkdir(parents=True)
            (root / "scripts/characters").mkdir(parents=True)
            (root / "scripts/characters/event-companion.hxc").write_text(character_hxc)
            metadata_path = source_root / "event-companion-fixture-metadata.json"
            chart_path = source_root / "event-companion-fixture-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))}, {haxe_string(str(source_root))});
    var definition:Dynamic = result.noteDefinitions[0];
    if (definition.sourceAdapter != "HXC" || definition.sourceAdapterClass != "EventCompanion"
      || definition.genericBehaviorRouted != true) fail("event character companion metadata");
    if (result.eventCharacterReferences.length != 1
      || result.eventCharacterReferences[0] != "event-companion") fail("event character references");
    for (finding in result.diagnostics)
      if (finding.code == "note-kind-generic") fail("event companion remained generic");
  }}
}}'''
            result = self.run_fixture(main, root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_character_companion_note_kinds_are_not_false_gaps(self):
        fixtures = [
            (
                EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/data/songs/fantasy-girl-01",
                "fantasy-girl-01",
                "hey-anim",
                "bf_tb.hxc",
            ),
            (
                EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/bara-no-yume",
                "bara-no-yume",
                "mom",
                "duetnew.hxc",
            ),
            (
                EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/markov-lyrics",
                "markov-lyrics",
                "markovBlood",
                "yuri-closeup.hxc",
            ),
            (
                EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/sugar-shock",
                "sugar-shock",
                "mom",
                "natsuki-angry.hxc",
            ),
            (
                EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/your-demise",
                "your-demise",
                "mom",
                "monika-angry.hxc",
            ),
            (
                EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/your-demise-vip",
                "your-demise-vip",
                "mom",
                "monika-angry.hxc",
            ),
        ]
        if not all(folder.is_dir() for folder, _, _, _ in fixtures):
            self.skipTest("mounted V-Slice character companion fixtures unavailable")
        rows = []
        for folder, stem, kind, script in fixtures:
            rows.append(
                "{" +
                f'folder:{haxe_string(str(folder))},stem:{haxe_string(stem)},' +
                f'kind:{haxe_string(kind)},script:{haxe_string(script)}' +
                "}"
            )
        main = '''using StringTools;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var fixtures:Array<Dynamic> = [''' + ",".join(rows) + '''];
    for (fixture in fixtures) {
      var metadata = fixture.folder + "/" + fixture.stem + "-metadata.json";
      var chart = fixture.folder + "/" + fixture.stem + "-chart.json";
      var result = VSliceImporter.convertFiles(metadata, chart, fixture.folder);
      var matched = false;
      for (definition in result.noteDefinitions)
        if (definition.sourceKind != null
          && Std.string(definition.sourceKind).toLowerCase() == Std.string(fixture.kind).toLowerCase()) {
          matched = definition.genericBehaviorRouted == true
            && Std.string(definition.sourceAdapterPath).toLowerCase().endsWith("/" + Std.string(fixture.script).toLowerCase());
        }
      if (!matched) fail("missing companion route: " + fixture.kind);
      for (finding in result.diagnostics)
        if (finding.code == "note-kind-generic"
          && finding.message.toLowerCase().indexOf(Std.string(fixture.kind).toLowerCase()) >= 0)
          fail("false generic gap: " + fixture.kind);
    }
  }
}'''
        result = self.run_fixture(main, EXAMPLES)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reachable_vslice_note_kind_bridges_emit_real_callback_adapters(self):
        """Reachable note kinds must be executable, not metadata-only.

        The importer may discover a note behavior in a selected character/song
        companion, so a clean scan should not regress to ``note-kind-generic``.
        This second boundary check makes sure that the HXC pass also emits the
        callback consumed by PlayState's native note pump. Donor files remain
        read-only fixtures; no chart rewrite is involved.
        """
        fixtures = [
            ("characters/yuri-closeup.hxc", "markovBlood"),
            ("characters/natsuki-angry.hxc", "mom"),
            ("characters/monika-angry.hxc", "mom"),
            ("characters/duetnew.hxc", "mom"),
            ("notes/markov.hxc", "markov"),
            ("notes/markovBE.hxc", "markovBE"),
        ]
        script_root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts"
        paths = [script_root / relative for relative, _ in fixtures]
        if not all(path.is_file() for path in paths):
            self.skipTest("reachable V-Slice HXC note fixtures are not mounted")
        declarations = []
        checks = []
        for index, ((relative, kind), path) in enumerate(zip(fixtures, paths)):
            variable = f"result{index}"
            declarations.append(
                f'var {variable} = HxcCompat.analyze(sys.io.File.getContent('
                f'{haxe_string(str(path))}), {haxe_string(str(path))});'
            )
            checks.append(
                f'''if ({variable}.canonicalCallbacks.indexOf("noteHit") < 0)
  fail("{relative} did not emit noteHit");
if ({variable}.generatedHscript == null
  || {variable}.generatedHscript.indexOf("function noteHit") < 0)
  fail("{relative} noteHit adapter was metadata-only");
if ("{relative}".indexOf("/characters/") >= 0
  && ({variable}.generatedHscript.indexOf("markCharacterNoteHandled") < 0
    || {variable}.generatedHscript.indexOf("characterDefaultNoteHit") < 0
    || {variable}.generatedHscript.indexOf("super.onNoteHit") >= 0))
  fail("{relative} character override bridge missing");
if ({variable}.noteBehaviorPatterns.indexOf("kind-routing") < 0)
  fail("{relative} kind routing missing");
if ({variable}.noteKinds.length > 0 && {variable}.noteKinds[0] != "{kind}")
  fail("{relative} authored kind changed: " + {variable}.noteKinds[0]);'''
            )
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    %s
    %s
  }
}''' % ("\n    ".join(declarations), "\n    ".join(checks))
        result = self.run_fixture(main, EXAMPLES)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_event_aliases_route_to_native_rows_and_diagnostics_dedupe(self):
        metadata = {
            "version": "2.2.0",
            "songName": "Alias Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad"},
                "stage": "stage",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 0}]},
            "events": [
                {"t": 100, "e": "ZoomCamera", "v": {"zoom": 1.25, "duration": 8, "ease": "expoOut", "mode": "stage"}},
                {"t": 200, "e": "AddCamZoomPsych", "v": {"gamezoom": "0.018", "hudzoom": "0.03"}},
                {"t": 300, "e": "charChange", "v": {"char": "caine", "target": "dad"}},
                {"t": 400, "e": "ChangeCharacterCL", "v": {"newchar": "pomni", "character": "bf"}},
                {"t": 500, "e": "ScrollSpeed", "v": {"scroll": 1.4, "duration": 4, "ease": "cube", "absolute": False, "strumline": "both"}},
                {"t": 600, "e": "SetCameraBop", "v": {"rate": 1, "intensity": 2.5}},
                {"t": 700, "e": "Flash Camera", "v": {"value1": "4", "value2": ""}},
                {"t": 800, "e": "CameraFlash", "v": {"value1": "#FFFFFF", "value2": "0.5"}},
                {"t": 850, "e": "ChangeStage", "v": {"stageid": "pixel"}},
                {"t": 900, "e": "untranslated-custom-event", "v": {}},
                {"t": 1000, "e": "untranslated-custom-event", "v": {}},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            metadata_path = fixture / "alias-metadata.json"
            chart_path = fixture / "alias-chart.json"
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))});
    var events:Array<Dynamic> = cast result.charts[0].chart.song.events;
    var names:Array<String> = [];
    var rows:Array<Dynamic> = [];
    for (group in events) for (event in (cast group[1]:Array<Dynamic>)) {{
      names.push(Std.string(event[0]));
      rows.push(event);
    }}
			var expected = "ZoomCamera|AddCamZoomPsych|charChange|ChangeCharacterCL|ScrollSpeed|SetCameraBop|Flash Camera|CameraFlash|ChangeStage|untranslated-custom-event|untranslated-custom-event";
    if (names.join("|") != expected) fail("event aliases: " + names.join("|"));
    // Authored kinds are preserved in the chart; native routing happens at
    // dispatch time through the same mapping (routeLegacyEvent).
    var route0 = EngineCompat.routeLegacyEvent(rows[0][0], rows[0][1], rows[0][2], rows[0][3]);
    if (route0 == null || route0.name != "Zoom Camera" || route0.v1 != "1.25" || route0.v2 != "8") fail("zoom route");
    var route1 = EngineCompat.routeLegacyEvent(rows[1][0], rows[1][1], rows[1][2], rows[1][3]);
    if (route1 == null || route1.name != "Add Camera Zoom" || route1.v1 != "0.018" || route1.v2 != "0.03") fail("add zoom route");
    var route2 = EngineCompat.routeLegacyEvent(rows[2][0], rows[2][1], rows[2][2], rows[2][3]);
    if (route2 == null || route2.name != "Change Character" || route2.v1 != "dad" || route2.v2 != "caine") fail("charChange route");
    var route3 = EngineCompat.routeLegacyEvent(rows[3][0], rows[3][1], rows[3][2], rows[3][3]);
    if (route3 == null || route3.name != "Change Character" || route3.v1 != "bf" || route3.v2 != "pomni") fail("ChangeCharacterCL route");
    var route4 = EngineCompat.routeLegacyEvent(rows[4][0], rows[4][1], rows[4][2], rows[4][3]);
    if (route4 == null || route4.name != "Change Scroll Speed" || route4.v1 != "1.4" || route4.v2 != "4") fail("scroll route");
    var route5 = EngineCompat.routeLegacyEvent(rows[5][0], rows[5][1], rows[5][2], rows[5][3]);
    if (route5 == null || route5.name != "Set Camera Bop" || route5.v1 != "1" || route5.v2 != "2.5") fail("bop route");
    var route8 = EngineCompat.routeLegacyEvent(rows[8][0], rows[8][1], rows[8][2], rows[8][3]);
    if (route8 == null || route8.name != "Change Stage" || route8.v1 != "pixel") fail("stage route");
    var preserved = 0;
    for (finding in result.diagnostics)
      if (finding.code == "foreign-event-preserved") preserved++;
    if (preserved != 1) fail("repeated preserved events were not deduplicated: " + preserved);
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_asset_diagnostics_identify_astc_only_and_extra_stems(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var result = VSliceImporter.diagnoseAssets([
      "images/characters/miku.astc",
      "images/characters/miku.png",
      "images/stage/only.astc",
      "songs/demo/Voices-M1KU.ogg",
      "songs/demo/Voices-boyfriend.ogg",
      "songs/demo/Voices.ogg"
    ]);
    if (result.astcOnly.length != 1 || result.astcOnly[0] != "images/stage/only.astc") fail("astc diagnostics");
    if (result.extraVocalStems.length != 2) fail("vocal stem diagnostics");
    var astc = false;
    var vocal = false;
    for (finding in result.diagnostics) {
      if (finding.code == "astc-only") astc = true;
      if (finding.code == "extra-vocal-stem") vocal = true;
    }
    if (!astc || !vocal) fail("diagnostic codes");
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_fixture(main, Path(folder))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_native_slots_and_unique_donor_asset_aliases(self):
        """Blank GF slots and logical nested/plural asset names stay engine-level."""

        character = {
            "version": "1.0.0",
            "name": "Sayo Speaker",
            "assetPath": "characters/BOYFRIEND",
            "animations": [{"name": "idle", "prefix": "Sayo Idle"}],
        }
        stage = {
            "version": "1.0.0",
            "name": "Alias Stage",
            "props": [{
                "name": "scanline",
                "assetPath": "scanline",
                "position": [0, 0],
                "animations": [],
            }],
        }
        metadata = {
            "version": "2.2.0",
            "songName": "No GF Song",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad", "girlfriend": " "},
                "stage": "stage",
            },
        }
        chart = {"version": "2.0.0", "notes": {"normal": [{"t": 0, "d": 0}]}}
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "shared/images/characters/boyfriend").mkdir(parents=True)
            (fixture / "shared/images/credits").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "shared/images/characters/boyfriend/BOYFRIEND.png").write_bytes(b"png")
            (fixture / "shared/images/characters/boyfriend/BOYFRIEND.xml").write_text("<TextureAtlas/>")
            (fixture / "shared/images/credits/scanlines.png").write_bytes(b"png")
            (fixture / "images/icons/icon-sayori.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            stage_path = fixture / "stage.json"
            metadata_path = fixture / "song-metadata.json"
            chart_path = fixture / "song-chart.json"
            character_path.write_text(json.dumps(character))
            stage_path.write_text(json.dumps(stage))
            metadata_path.write_text(json.dumps(metadata))
            chart_path.write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var character = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var sawNested = false;
    var sawMissing = false;
    for (asset in character.assets) {{
      if (asset.source.indexOf("BOYFRIEND.png") >= 0) sawNested = true;
    }}
    for (finding in character.diagnostics) {{
      if (finding.code == "missing-asset") sawMissing = true;
    }}
    if (!sawNested || sawMissing) fail("nested character basename alias");
    var stage = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    var sawPlural = false;
    for (asset in stage.assets) if (asset.source.indexOf("scanlines.png") >= 0) sawPlural = true;
    for (finding in stage.diagnostics) if (finding.code == "missing-asset") fail("plural stage basename alias");
    if (!sawPlural) fail("plural stage asset mapping");
    var song = VSliceImporter.convertFiles({haxe_string(str(metadata_path))}, {haxe_string(str(chart_path))});
    if (song.charts[0].chart.song.gf != "no-gf") fail("blank girlfriend slot");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_conversion_generates_native_registry_hscript_and_mappings(self):
        character = {
            "version": "1.0.0",
            "name": "Synthetic Hero",
            "assetPath": "characters/hero",
            "singTime": 5.5,
            "cameraOffsets": [-20, 30],
            "offsets": [7, -8],
            "isPixel": True,
            "scale": 0.75,
            "startingAnimation": "singLEFT",
            "danceEvery": 2,
            "no_antialiasing": True,
            "healthbar_colors": [12, 34, 56],
            "flipX": True,
            "healthIcon": {"id": "hero", "scale": 1},
            "animations": [
                {"name": "idle", "prefix": "Hero Idle", "offsets": [1, 2], "frameRate": 12, "frameIndices": [0, 2]},
                {"name": "singLEFT", "prefix": "Hero Left", "offsets": [3, 4], "frameRate": 24, "frameIndices": []},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/hero.png").write_bytes(b"png")
            (fixture / "images/characters/hero.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.name != "synthetic-hero") fail("character name");
    if (converted.registryEntry.like != "synthetic-hero") fail("registry like");
    if (converted.assets.length != 3) fail("asset mappings");
    if (converted.hscript.indexOf("addByIndices(\\\"idle\\\", \\\"Hero Idle\\\", [0, 2]") < 0) fail("indexed animation");
    if (converted.hscript.indexOf("char.scale.set(0.75, 0.75)") < 0) fail("scale");
    if (converted.hscript.indexOf("char.vSliceGlobalOffsetX = 7") < 0
      || converted.hscript.indexOf("char.vSliceGlobalOffsetY = -8") < 0
      || converted.hscript.indexOf("char.playerOffsetX = 7") < 0
      || converted.hscript.indexOf("char.followCamY += 30") < 0) fail("offsets");
    if (converted.hscript.indexOf("char.antialiasing = false") < 0 || converted.hscript.indexOf("char.flipX = true") < 0) fail("pixel/flip");
    if (converted.hscript.indexOf("char.danceEvery = 2") < 0) fail("character dance cadence");
    if (converted.hscript.indexOf("char.playAnim(\\\"idle\\\")") < 0) fail("character starting animation");
    if (converted.hscript.indexOf("char.updateHitbox();") < 0) fail("opening-pose hitbox");
    if (converted.registryEntry.colors[0] != "#0C2238") fail("healthbar colors");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_costume_metadata_and_split_animation_assets_are_preserved(self):
        character = {
            "version": "1.0.0",
            "name": "Costume Hero",
            "assetPath": "characters/main",
            "costumes": "hero",
            "costumelist": [
                {"subfolder": True, "internal_Name": "casual", "charFile": "hero-casual"},
                {"subfolder": False, "internal_Name": "classic", "charFile": "hero-classic"},
            ],
            "doesLoop": True,
            "animations": [
                {"name": "idle", "prefix": "Hero Idle"},
                {"name": "special", "assetPath": "characters/special", "prefix": "Hero Special"},
            ],
            "healthIcon": {"id": "costume-hero"},
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            image_root = fixture / "images/characters"
            image_root.mkdir(parents=True)
            for stem in ("main", "special"):
                (image_root / f"{stem}.png").write_bytes(b"png")
                (image_root / f"{stem}.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/icons/icon-costume-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.assets.length != 5) fail("asset mappings: " + converted.assets.length);
    if (converted.registryEntry.vSliceCostumes != "hero") fail("costume root metadata");
    if (converted.registryEntry.vSliceCostumeList.length != 2) fail("costume list metadata");
    if (converted.registryEntry.vSliceDoesLoop != true) fail("doesLoop metadata");
    if (converted.hscript.indexOf("char.vSliceCostumes = \\\"hero\\\"") < 0) fail("runtime costume root");
    if (converted.hscript.indexOf("char.costumelist = char.vSliceCostumeList") < 0) fail("runtime costume alias");
    if (converted.hscript.indexOf("char.doesLoop = char.vSliceDoesLoop") < 0) fail("runtime doesLoop alias");
    if (converted.hscript.indexOf("registerVSliceAnimationAsset(\\\"special\\\"") < 0) fail("runtime animation asset switch");
    for (finding in converted.diagnostics)
      if (finding.code == "unsupported-character-field" || finding.code == "animation-asset-switch") fail("preserved field diagnosed as unsupported");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_animation_timing_and_indices_aliases_are_preserved(self):
        """Older V-Slice exports use fps/indices instead of frameRate/frameIndices."""

        character = {
            "version": "1.0.0",
            "name": "Legacy Animation Hero",
            "assetPath": "characters/legacy",
            "healthIcon": {"id": "legacy-animation-hero"},
            "animations": [
                {
                    "name": "idle",
                    "prefix": "Legacy Idle",
                    "fps": 12,
                    "indices": [0, 2, 4],
                    "looped": True,
                },
                {
                    "name": "singLEFT",
                    "prefix": "Legacy Left",
                    "fps": 31,
                    "indices": [],
                    "looped": False,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/legacy.png").write_bytes(b"png")
            (fixture / "images/characters/legacy.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-legacy-animation-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.hscript.indexOf('addByIndices("idle", "Legacy Idle", [0, 2, 4], "", 12') < 0)
      fail("legacy indices/fps aliases");
    if (converted.hscript.indexOf('addByPrefix("singLEFT", "Legacy Left", 31, false)') < 0)
      fail("legacy fps alias");
    for (finding in converted.diagnostics)
      if (finding.code == "invalid-character-animation") fail("legacy animation was discarded");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_split_animation_asset_reports_authored_dependency(self):
        """A missing donor atlas is not silently substituted by another animation."""

        character = {
            "version": "1.0.0",
            "name": "Missing Split Hero",
            "assetPath": "characters/main",
            "healthIcon": {"id": "missing-split-hero"},
            "animations": [
                {"name": "idle", "prefix": "Hero Idle"},
                {
                    "name": "deathConfirm",
                    "assetPath": "characters/missing-death-atlas",
                    "prefix": "Hero Death Confirm",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/main.png").write_bytes(b"png")
            (fixture / "images/characters/main.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-missing-split-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var sawMissing = false;
    var sawSwitch = false;
            for (finding in converted.diagnostics) {{
              if (finding.code == "missing-asset"
                && finding.message.indexOf("characters/missing-death-atlas") >= 0)
                sawMissing = true;
      if (finding.code == "animation-asset-switch") {{
        sawSwitch = finding.message.indexOf("characters/missing-death-atlas") >= 0
          && finding.message.indexOf("no PNG, ASTC, or validated destination-native fallback") >= 0;
      }}
            }}
            if (!sawMissing || !sawSwitch) fail("missing split dependency was not precise");
            if (converted.hscript.indexOf('addByPrefix("deathConfirm"') >= 0
              || converted.hscript.indexOf('registerVSliceAnimationAsset("deathConfirm"') >= 0)
              fail("unavailable split animation was registered as a zero-frame alias");
          }}
        }}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_render_types_and_multisparrow_atlas_concatenation(self):
        character = {
            "version": "1.0.0",
            "name": "Synthetic Multi",
            "renderType": "multisparrow",
            "assetPath": "characters/main",
            "healthIcon": {"id": "multi"},
            "animations": [
                {"name": "idle", "prefix": "Main Idle"},
                {"name": "special", "assetPath": "characters/special", "prefix": "Special"},
                {"name": "firstDeath", "assetPath": "characters/dead", "prefix": "Dead"},
            ],
        }
        sparrow_character = dict(character)
        sparrow_character["name"] = "Synthetic Sparrow"
        sparrow_character["renderType"] = "sparrow"
        sparrow_character["animations"] = [{"name": "idle", "prefix": "Main Idle"}]
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            for stem in ("main", "special", "dead"):
                (fixture / f"images/characters/{stem}.png").parent.mkdir(parents=True, exist_ok=True)
                (fixture / f"images/characters/{stem}.png").write_bytes(b"png")
                (fixture / f"images/characters/{stem}.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-multi.png").parent.mkdir(parents=True)
            (fixture / "images/icons/icon-multi.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            sparrow_path = fixture / "sparrow-character.json"
            sparrow_path.write_text(json.dumps(sparrow_character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(findings:Array<Dynamic>, code:String):Bool {{
    for (finding in findings) if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var multi = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (multi.assets.length != 7) fail("multisparrow asset mappings");
    if (hasCode(cast multi.diagnostics, "unsupported-character-field")) fail("renderType was diagnosed as an unknown field");
    if (hasCode(cast multi.diagnostics, "animation-asset-switch")) fail("multisparrow atlas switch diagnostic");
    if (multi.hscript.indexOf("FlxAtlasFrames.combineSparrow(vSliceAtlases)") < 0) fail("multisparrow adapter");
    if (multi.hscript.indexOf('hscriptPath + "alternate-special.png"') < 0) fail("special atlas path");
    if (multi.hscript.indexOf('hscriptPath + "dead.png"') < 0) fail("death atlas path");
    var sparrow = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(sparrow_path))})), {haxe_string(str(fixture))});
    if (hasCode(cast sparrow.diagnostics, "unsupported-character-field")) fail("sparrow renderType was diagnosed as an unknown field");
    if (hasCode(cast sparrow.diagnostics, "unsupported-character-render-type")) fail("sparrow renderType unsupported");
    if (sparrow.hscript.indexOf("FlxAtlasFrames.combineSparrow") >= 0) fail("sparrow used multisparrow adapter");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multisparrow_astc_unavailability_is_not_reported_as_missing_primary(self):
        """A present but undecodable ASTC source gets one precise ASTC finding."""
        character = {
            "version": "1.0.0",
            "name": "ASTC Unavailable Multi",
            "renderType": "multisparrow",
            "assetPath": "characters/main",
            "healthIcon": {"id": "astc-unavailable-multi"},
            "animations": [{"name": "idle", "prefix": "Main Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            # An invalid ASTC header still represents a present authored source;
            # it must not be relabelled as an absent multisparrow primary.
            (fixture / "images/characters/main.astc").write_bytes(b"invalid astc source")
            (fixture / "images/characters/main.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-astc-unavailable-multi.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var astc = false;
    var primary = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "astc-only") astc = true;
      if (finding.code == "multisparrow-primary-not-combined") primary = true;
    }}
    if (!astc || primary) fail("ASTC unavailable classification");
    if (converted.hscript.indexOf('addByPrefix("idle"') >= 0) fail("zero-frame primary alias");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multisparrow_absent_primary_retains_precise_missing_diagnostic(self):
        """A truly absent primary remains visible and cannot create a zero-frame alias."""
        character = {
            "version": "1.0.0",
            "name": "Missing Multi Primary",
            "renderType": "multisparrow",
            "assetPath": "characters/missing-multi-primary",
            "healthIcon": {"id": "missing-multi-primary"},
            "animations": [{"name": "idle", "prefix": "Missing Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/icons/icon-missing-multi-primary.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var missing = false;
    var primary = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "missing-asset"
        && finding.message.indexOf("characters/missing-multi-primary") >= 0) missing = true;
      if (finding.code == "multisparrow-primary-not-combined"
        && finding.message.indexOf("authored primary source is absent") >= 0) primary = true;
    }}
    if (!missing || !primary) fail("absent multisparrow primary diagnostic");
    if (converted.hscript.indexOf('addByPrefix("idle"') >= 0) fail("zero-frame missing primary alias");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multisparrow_combination_uses_native_root_for_native_primary(self):
        """Native fallback atlases and imported sub-atlases share one frame set."""
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/special.png").write_bytes(b"png")
            (fixture / "images/characters/special.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-multi-native.png").write_bytes(b"icon")
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var data:Dynamic = {{
      version: "1.0.0", name: "Native Multi", renderType: "multisparrow",
      assetPath: "characters/senpai", healthIcon: {{id: "multi-native"}},
      animations: [
        {{name: "idle", prefix: "Angry Senpai Idle"}},
        {{name: "special", assetPath: "characters/special", prefix: "Special"}}
      ]
    }};
    var converted = VSliceImporter.convertCharacter(data, {haxe_string(str(fixture))}, "multi-native");
    var native = false;
    for (finding in converted.diagnostics)
      if (finding.code == "native-character-asset") native = true;
    if (!native) fail("native multisparrow fallback");
    if (converted.hscript.indexOf('vSliceAtlases.push(["assets/images/custom_chars/senpai/" + "char.png"') < 0)
      fail("native primary was not combined");
    if (converted.hscript.indexOf('vSliceAtlases.push([hscriptPath + "alternate-special.png"') < 0)
      fail("donor subatlas was not combined");
    if (converted.hscript.indexOf('vSliceAtlases.push([hscriptPath + "char.png"') >= 0)
      fail("native primary incorrectly used generated folder");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_multisparrow_missing_primary_falls_back_to_native_and_keeps_donor_extras(self):
        """A missing primary atlas resolves to the destination-native character the
        donor assumed the base game would supply, while prefixes the native atlas
        cannot provide stay unavailable instead of becoming zero-frame aliases."""
        native_png = ROOT / "assets/images/custom_chars/bf/char.png"
        native_xml = ROOT / "assets/images/custom_chars/bf/char.xml"
        if not native_png.exists() or not native_xml.exists():
            self.skipTest("destination-native bf atlas is not available")
        character = {
            "version": "1.0.0",
            "name": "Native Multi BF",
            "renderType": "multisparrow",
            "assetPath": "characters/BOYFRIEND",
            "healthIcon": {"id": "bf"},
            "animations": [
                {"name": "idle", "prefix": "BF idle dance"},
                {"name": "scared", "prefix": "Totally Absent Prefix"},
                {"name": "firstDeath", "assetPath": "characters/signDeath", "prefix": "BF Dead Loop"},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "shared/images/characters").mkdir(parents=True)
            (fixture / "shared/images/characters/signDeath.png").write_bytes(b"png")
            (fixture / "shared/images/characters/signDeath.xml").write_text("<TextureAtlas/>")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))}, "native-multi-bf");
    var native = false;
    var partial = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "native-character-asset") native = true;
      if (finding.code == "native-atlas-missing-prefixes") partial = true;
    }}
    if (!native) fail("native primary fallback was not resolved");
    if (!partial) fail("partial native prefix coverage was not reported");
    if (converted.hscript.indexOf('vSliceAtlases.push(["assets/images/custom_chars/bf/" + "char.png"') < 0)
      fail("native primary was not referenced by the generated script");
    if (converted.hscript.indexOf('vSliceAtlases.push([hscriptPath + "dead.png"') < 0)
      fail("donor-shipped extra atlas was not combined");
    if (converted.hscript.indexOf('addByPrefix("idle"') < 0)
      fail("native-prefix animation was dropped");
    if (converted.hscript.indexOf('addByPrefix("firstDeath"') < 0)
      fail("donor extra animation was dropped");
    if (converted.hscript.indexOf('addByPrefix("scared"') >= 0)
      fail("missing-prefix animation became a zero-frame alias");
    for (mapping in converted.assets)
      if (mapping.destination == "char.png" || mapping.destination == "char.xml")
        fail("native atlas was scheduled for copy into the mod folder");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_vs_tricky_bftricky_uses_native_primary_with_donor_death_atlas(self):
        """Vs Tricky's bftricky omits characters/BOYFRIEND because base V-Slice owns
        it; the conversion must load the destination-native bf atlas while keeping
        the donor-shipped signDeath death atlas and every available animation."""
        root = EXAMPLES / "v-slice/Vs Tricky"
        character = root / "data/characters/bftricky.json"
        native_png = ROOT / "assets/images/custom_chars/bf/char.png"
        native_xml = ROOT / "assets/images/custom_chars/bf/char.xml"
        if not character.exists() or not native_png.exists() or not native_xml.exists():
            self.skipTest("mounted Vs Tricky/native bf fixture is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var donor = {haxe_string(str(root))};
    if (sys.FileSystem.exists(donor + "/shared/images/characters/BOYFRIEND.png"))
      fail("donor unexpectedly ships the base atlas; fixture premise changed");
    var definition = donor + "/data/characters/bftricky.json";
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent(definition)),
      donor, "bftricky", true, definition);
    if (converted.name != "bftricky") fail("conversion identity");
    var missingPrimary = false;
    var native = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "missing-asset" && finding.message.indexOf("characters/BOYFRIEND") >= 0)
        missingPrimary = true;
      if (finding.code == "native-character-asset") native = true;
    }}
    if (missingPrimary) fail("base primary atlas was reported missing");
    if (!native) fail("native primary fallback was not reported");
    if (converted.hscript.indexOf('vSliceAtlases.push(["assets/images/custom_chars/bf/" + "char.png"') < 0)
      fail("native bf atlas missing from generated script");
    if (converted.hscript.indexOf('vSliceAtlases.push([hscriptPath + "dead.png"') < 0)
      fail("donor signDeath atlas missing from generated script");
    for (animation in ["idle", "singLEFT", "singUPmiss", "hey", "firstDeath", "deathLoop", "deathConfirm"])
      if (converted.hscript.indexOf('addByPrefix("' + animation + '"') < 0)
        fail("authored animation was dropped: " + animation);
    if (converted.hscript.indexOf('addByPrefix("scared"') >= 0)
      fail("scared stayed registered without any atlas providing its prefix");
    var copiedPrimary = false;
    var copiedDead = false;
    for (mapping in converted.assets) {{
      if (mapping.destination == "char.png" || mapping.destination == "char.xml") copiedPrimary = true;
      if (mapping.destination == "dead.png") copiedDead = true;
    }}
    if (copiedPrimary) fail("native primary was scheduled for copy");
    if (!copiedDead) fail("donor death atlas mapping was lost");
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_without_health_icon_uses_character_id_fallback(self):
        character = {
            "version": "1.0.0",
            "name": "Fallback Hero",
            "assetPath": "characters/hero",
            "animations": [{"name": "idle", "prefix": "Hero Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/hero.png").write_bytes(b"png")
            (fixture / "images/characters/hero.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-fallback-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.assets.length != 3) fail("fallback icon mapping");
    var missingIcon = false;
    for (finding in converted.diagnostics)
      if (finding.code == "missing-health-icon") missingIcon = true;
    if (missingIcon) fail("resolved conventional icon was reported missing");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_girlfriend_only_character_can_keep_missing_health_icon_optional(self):
        """GF-only V-Slice actors do not need a player/opponent icon asset."""

        character = {
            "version": "1.0.0",
            "name": "GF-only Actor",
            "assetPath": "characters/gf-only",
            "healthIcon": {"id": "lav"},
            "animations": [{"name": "idle", "prefix": "GF Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/characters/gf-only.png").write_bytes(b"png")
            (fixture / "images/characters/gf-only.xml").write_text("<TextureAtlas/>")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))}, "gf-only", false);
    for (finding in converted.diagnostics)
      if (finding.code == "missing-health-icon") fail("GF-only icon remained required");
    if (converted.registryEntry.vSliceHealthIconRequired != false)
      fail("GF-only icon requirement was not retained");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pixel_character_asset_stem_resolves_exact_freeplay_icon_alias(self):
        """Pixel V-Slice characters may omit healthIcon and use a presentation stem."""

        character = {
            "version": "1.0.0",
            "name": "Silhouette Monika",
            "assetPath": "characters/SilhouetteMonikaPixel",
            "isPixel": True,
            "animations": [{"name": "idle", "prefix": "MkaIdle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/freeplay/icons").mkdir(parents=True)
            (fixture / "images/characters/SilhouetteMonikaPixel.png").write_bytes(b"png")
            (fixture / "images/characters/SilhouetteMonikaPixel.xml").write_text("<TextureAtlas/>")
            (fixture / "images/freeplay/icons/monikapixel.png").write_bytes(b"icon")
            (fixture / "images/freeplay/icons/monikapixel.xml").write_text("<TextureAtlas/>")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))}, "silhouettemonika");
    var icon = false;
    var missing = false;
    for (mapping in converted.assets)
      if (mapping.kind == "health-icon" && mapping.source.indexOf("monikapixel.png") >= 0) icon = true;
    for (finding in converted.diagnostics)
      if (finding.code == "missing-health-icon") missing = true;
    if (!icon || missing) fail("pixel asset-stem icon alias");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_asset_resolution_accepts_case_variants_shared_roots_and_pixel_icons(self):
        character = {
            "version": "1.0.0",
            "name": "Case Variant",
            "assetPath": "characters/HERO",
            "healthIcon": {"id": "gfdoki", "isPixel": True},
            "animations": [{"name": "idle", "prefix": "Hero Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "Shared/Images/Characters").mkdir(parents=True)
            (fixture / "Images/Freeplay/Icons").mkdir(parents=True)
            (fixture / "Shared/Images/Characters/Hero.PNG").write_bytes(b"png")
            (fixture / "Shared/Images/Characters/Hero.XML").write_text("<TextureAtlas/>")
            # V-Slice freeplay exports commonly omit the icon- prefix and use a
            # pixel suffix.  The source spelling/case is deliberately foreign
            # to the native resolver.
            (fixture / "Images/Freeplay/Icons/GFDOKIPIXEL.PNG").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.assets.length != 3) fail("case/shared/pixel mappings: " + converted.assets.length);
    if (converted.assets[0].source.indexOf("Shared/Images/Characters/Hero.PNG") < 0) fail("shared case path");
    if (converted.assets[2].source.indexOf("GFDOKIPIXEL.PNG") < 0) fail("pixel icon path");
    for (finding in converted.diagnostics)
      if (finding.code == "missing-health-icon" || finding.code == "missing-asset") fail("false missing diagnostic");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_astc_only_case_variants_are_reported_without_a_fake_png(self):
        character = {
            "version": "1.0.0",
            "name": "ASTC Multi",
            "renderType": "multisparrow",
            "assetPath": "characters/ASTC_HERO",
            "healthIcon": {"id": "astc-icon"},
            "animations": [{"name": "idle", "prefix": "Hero Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "Shared/Images/Characters").mkdir(parents=True)
            (fixture / "Images/Icons").mkdir(parents=True)
            (fixture / "Shared/Images/Characters/ASTC_HERO.AsTc").write_bytes(b"astc")
            (fixture / "Images/Icons/icon-astc-icon.ASTC").write_bytes(b"astc")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
using StringTools;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var astc = 0;
    for (mapping in converted.assets)
      if (!mapping.supported && mapping.source.toLowerCase().endsWith(".astc")) astc++;
    var sawAstc = false;
    var sawFakePng = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "astc-only") sawAstc = true;
      if (finding.code == "missing-health-icon") sawFakePng = true;
    }}
    if (astc != 2 || !sawAstc) fail("ASTC-only mappings/diagnostics");
    if (sawFakePng) fail("ASTC-only icon was reported as an unrelated missing icon");
    for (mapping in converted.assets)
      if (mapping.destination.toLowerCase().endsWith(".png")) fail("fabricated PNG mapping");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(os.name == "nt", "fake decoder fixture uses a POSIX executable wrapper")
    def test_astc_decoder_preserves_multisparrow_xml_mappings(self):
        character = {
            "version": "1.0.0",
            "name": "ASTC Decoder Multi",
            "renderType": "multisparrow",
            "assetPath": "characters/main",
            "healthIcon": {"id": "decoder-multi"},
            "animations": [
                {"name": "idle", "prefix": "Main Idle"},
                {"name": "special", "assetPath": "characters/special", "prefix": "Special"},
                {"name": "firstDeath", "assetPath": "characters/dead", "prefix": "Dead"},
            ],
        }
        fake_decoder = """#!/usr/bin/env python3
import sys

if len(sys.argv) > 1 and sys.argv[1] == '-ds':
    # The character conversion test only probes the executable, but keep the
    # wrapper honest if a future fixture exercises decodeFile as well.
    output = sys.argv[3]
    with open(output, 'wb') as stream:
        stream.write(bytes.fromhex(
            '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
            '0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082'))
else:
    print('astcenc fake 4.0')
"""
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            decoder = fixture / "astcenc-fake.py"
            decoder.write_text(fake_decoder)
            decoder.chmod(0o755)
            image_root = fixture / "images/characters"
            image_root.mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            # 4x4x1 blocks, 1x1x1 texels, and exactly one 16-byte ASTC block.
            astc = bytes.fromhex("13aba15c040401010000010000010000") + (b"\0" * 16)
            for stem in ("main", "special", "dead"):
                (image_root / f"{stem}.astc").write_bytes(astc)
                (image_root / f"{stem}.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-decoder-multi.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            env = os.environ.copy()
            env["DISAPPOINTINGPLUS_ASTCENC"] = str(decoder)
            main = f'''import haxe.Json;
using StringTools;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var astcMappings = 0;
    var xmlMappings = 0;
    for (mapping in converted.assets) {{
      if (mapping.requiresConversion == true) {{
        astcMappings++;
        if (!mapping.supported || !mapping.destination.toLowerCase().endsWith(".png")) fail("ASTC mapping was not conversion-ready");
      }}
      if (mapping.destination.toLowerCase().endsWith(".xml")) {{
        xmlMappings++;
        if (!mapping.supported) fail("companion XML was not supported");
      }}
    }}
    if (astcMappings != 3 || xmlMappings != 3 || converted.assets.length != 7) fail("mapping counts: " + astcMappings + "/" + xmlMappings + "/" + converted.assets.length);
    if (converted.hscript.indexOf("FlxAtlasFrames.combineSparrow(vSliceAtlases)") < 0) fail("multisparrow atlas combine");
    for (finding in converted.diagnostics)
      if (finding.code == "multisparrow-primary-not-combined" || finding.code == "astc-only") fail("false ASTC unsupported diagnostic");
    var decoded = VSliceAstcAdapter.decodeFile({haxe_string(str(fixture / "images/characters/main.astc"))}, {haxe_string(str(fixture / "decoded.png"))});
    if (!decoded.success || !sys.FileSystem.exists({haxe_string(str(fixture / "decoded.png"))})) fail("fake decoder conversion");
  }}
}}
'''
            result = self.run_fixture(main, fixture, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_legacy_position_aliases_and_death_camera_metadata(self):
        character = {
            "version": "1.0.0",
            "name": "Camera Hero",
            "assetPath": "characters/hero",
            "position": [12, -8],
            "camera_position": [-20, 30],
            "death": {"cameraOffsets": [-150, 50], "cameraZoom": 0.9},
            "Made_With": "metadata only",
            "healthIcon": {"id": "camera-hero"},
            "animations": [{"name": "idle", "prefix": "Hero Idle"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/hero.png").write_bytes(b"png")
            (fixture / "images/characters/hero.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-camera-hero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    if (converted.hscript.indexOf("char.playerOffsetX = 12") < 0) fail("position alias");
    if (converted.hscript.indexOf("char.followCamX += -20") < 0) fail("camera_position alias");
    if (converted.hscript.indexOf("char.deathCameraOffsetX = -150") < 0) fail("death camera offset");
    if (converted.hscript.indexOf("char.deathCameraZoom = 0.9") < 0) fail("death camera zoom");
    for (finding in converted.diagnostics)
      if (finding.code == "unsupported-character-field") fail("supported alias diagnosed as unsupported");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        character_source = (ROOT / "source/Character.hx").read_text()
        game_over_source = (ROOT / "source/GameOverSubstate.hx").read_text()
        self.assertIn("public var deathCameraOffsetX:Float", character_source)
        self.assertIn("bf.deathCameraOffsetX", game_over_source)
        self.assertIn("bf.deathCameraZoom", game_over_source)

    def test_multisparrow_missing_subatlas_is_explicitly_diagnosed(self):
        character = {
            "version": "1.0.0",
            "name": "Missing Multi",
            "renderType": "multisparrow",
            "assetPath": "characters/main",
            "animations": [
                {"name": "idle", "prefix": "Main Idle"},
                {"name": "special", "assetPath": "characters/missing", "prefix": "Special"},
            ],
            "healthIcon": {"id": "missing"},
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/characters/main.png").write_bytes(b"png")
            (fixture / "images/characters/main.xml").write_text("<TextureAtlas/>")
            (fixture / "images/characters/missing.png").write_bytes(b"png")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    var sawMissingAtlas = false;
    var sawExplicitMulti = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "missing-atlas-data") sawMissingAtlas = true;
      if (finding.code == "multisparrow-subatlas-not-combined") sawExplicitMulti = true;
    }}
    if (!sawMissingAtlas || !sawExplicitMulti) fail("missing multisparrow subatlas was not diagnosed precisely");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_dance_every_is_live_runtime_state(self):
        character = (ROOT / "source/Character.hx").read_text()
        importer = (ROOT / "source/VSliceImporter.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("public var danceEvery:Int = 1;", character)
        self.assertIn("char.danceEvery =", importer)
        self.assertIn("character.danceEvery <= 0", play_state)
        self.assertIn("characterDanceDue(dad, curBeat)", play_state)
        self.assertIn("characterDanceDue(boyfriend, curBeat)", play_state)
        self.assertIn("characterDanceDue(gf, curBeat)", play_state)

    def test_stage_conversion_preserves_positions_layers_props_and_animation_metadata(self):
        stage = {
            "version": "1.0.0",
            "name": "Synthetic Stage",
            "directory": "shared",
            "cameraZoom": 0.72,
            "characters": {
                "bf": {"zIndex": 300, "position": [900, 600], "cameraOffsets": [-10, 20]},
                "dad": {"zIndex": 200, "position": [100, 620], "cameraOffsets": [30, -4]},
                "gf": {"zIndex": 100, "position": [450, 400], "cameraOffsets": [0, 5]},
                "spectator": {"position": [0, 0]},
            },
            "props": [{
                "zIndex": 250,
                "position": [12, 34],
                "scale": [1.2, 0.8],
                "scroll": [0.7, 0.9],
                "alpha": 0.65,
                "flipX": True,
                "flipY": True,
                "angle": 12.5,
                "color": "#ABCDEF",
                "danceEvery": 2,
                "animType": "sparrow",
                "name": "Front Thing",
                "isPixel": False,
                "startingAnimation": "idle",
                "assetPath": "stages/front",
                "blend": "add",
                "animations": [
                    {"name": "idle", "prefix": "front idle", "frameRate": 18, "frameIndices": [0, 1]},
                    {"name": "treeLoop", "frameRate": 12, "frameIndices": [2, 3], "looped": True}
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/stages").mkdir(parents=True)
            (fixture / "images/stages/front.png").write_bytes(b"png")
            (fixture / "images/stages/front.xml").write_text("<TextureAtlas/>")
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    if (converted.name != "synthetic-stage" || converted.registryValue != "synthetic-stage") fail("stage identity");
    if (converted.assets.length != 2) fail("stage asset mappings");
    if (converted.hscript.indexOf("setDefaultZoom(0.72)") < 0) fail("zoom");
    if (converted.hscript.indexOf("stage.setOffsets(\\\"bf\\\", 900 - boyfriend.width / 2 + boyfriend.playerOffsetX, 600 - boyfriend.height + boyfriend.playerOffsetY, false)") < 0 || converted.hscript.indexOf("boyfriend.x = 900 - boyfriend.width / 2 + boyfriend.playerOffsetX") < 0 || converted.hscript.indexOf("dad.followCamX = 0") < 0 || converted.hscript.indexOf("stage.setCamOffsets(\\\"dad\\\", 30, -4, false)") < 0) fail("character placement");
    if (converted.hscript.indexOf("scale.set(1.2, 0.8)") < 0 || converted.hscript.indexOf("scrollFactor.set(0.7, 0.9)") < 0) fail("prop transform");
    if (converted.hscript.indexOf("addByIndices(\\\"idle\\\", \\\"front idle\\\", [0, 1]") < 0) fail("prop animation");
    if (converted.hscript.indexOf("addByIndices(\\\"treeLoop\\\", \\\"\\\", [2, 3]") < 0) fail("index-only prop animation");
    if (converted.hscript.indexOf("flipX = true") < 0 || converted.hscript.indexOf("flipY = true") < 0) fail("prop flips");
    if (converted.hscript.indexOf("angle = 12.5") < 0 || converted.hscript.indexOf("color = 0xFFABCDEF") < 0) fail("prop tint/angle");
    if (converted.hscript.indexOf("if (beat % 2 == 0)") < 0 || converted.hscript.indexOf("animation.play(\\\"idle\\\", true)") < 0) fail("prop dance cadence");
    if (converted.hscript.indexOf("blendModeFromString(\\\"add\\\")") < 0) fail("prop blend");
    if (converted.hscript.indexOf("BEHIND_BF") < 0) fail("prop z layer");
    if (converted.hscript.indexOf("stage.elements.set(\\\"Front Thing\\\", vSliceProp_front_thing_0)") < 0) fail("authored prop lookup");
    var unsupported = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "unsupported-stage-field") fail("directory was treated as unsupported");
      if (finding.code == "unsupported-stage-character") unsupported = true;
    }}
    if (!unsupported) fail("unsupported stage diagnostic");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_conversion_applies_uniform_prop_scale_and_stage_character_transforms(self):
        # Wacky World ships "scale": 1.9 as a lone number (V-Slice Scale fields
        # are one-or-two values) and hides the girlfriend via authored alpha.
        stage = {
            "version": "1.0.0",
            "name": "Circo Digital",
            "cameraZoom": 0.65,
            "characters": {
                "bf": {"position": [926, 857], "cameraOffsets": [0, -60], "scale": 1.05},
                "dad": {"position": [-480, 381], "cameraOffsets": [450, -150], "scale": 1.05},
                "gf": {"position": [604, 756], "alpha": 0},
            },
            "props": [
                {"name": "circo", "position": [-1367, -1019], "scale": 1.9, "alpha": 1, "animType": "none", "assetPath": "circo/image0"},
                {"name": "brillo", "position": [-1376, -1024], "scale": 1.9, "alpha": 0.2, "animType": "none", "assetPath": "circo/image1"},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/circo").mkdir(parents=True)
            (fixture / "images/circo/image0.png").write_bytes(b"png")
            (fixture / "images/circo/image1.png").write_bytes(b"png")
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    if (converted.hscript.indexOf("scale.set(1.9, 1.9)") < 0) fail("uniform prop scale was dropped");
    if (converted.hscript.indexOf("alpha = 0.2") < 0) fail("prop alpha");
    // Stage character scale multiplies the character's own base scale (funkin
    // Stage.addCharacter), and authored alpha is applied directly.
    if (converted.hscript.indexOf("boyfriend.scale.set(boyfriend.scale.x * 1.05, boyfriend.scale.y * 1.05)") < 0
        || converted.hscript.indexOf("boyfriend.updateHitbox()") < 0) fail("stage bf scale");
    if (converted.hscript.indexOf("dad.scale.set(dad.scale.x * 1.05, dad.scale.y * 1.05)") < 0) fail("stage dad scale");
    if (converted.hscript.indexOf("gf.alpha = 0") < 0) fail("authored gf alpha");
    if (converted.hscript.indexOf("setDefaultZoom(0.65)") < 0) fail("zoom");
    if (converted.hscript.indexOf("boyfriend.y = 857 - boyfriend.height") < 0) fail("feet-anchored placement");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_conversion_supports_solid_colour_props_and_static_pngs(self):
        stage = {
            "version": "1.0.0",
            "name": "Colour Stage",
            "props": [
                {
                    "name": "backdrop",
                    "assetPath": "#A7D1F2",
                    "position": [-500, -1000],
                    "scale": [2400, 2000],
                    "scroll": [0, 0],
                },
                {
                    "name": "static foreground",
                    "assetPath": "stage/foreground",
                    "position": [0, 0],
                    "scale": [1, 1],
                    "animations": [],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/stage").mkdir(parents=True)
            (fixture / "images/stage/foreground.png").write_bytes(b"png")
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    if (converted.assets.length != 1) fail("solid colour created a file mapping");
    if (converted.hscript.indexOf("makeGraphic(1, 1, 0xFFA7D1F2)") < 0) fail("solid colour graphic");
    if (converted.hscript.indexOf("scale.set(2400, 2000)") < 0) fail("solid colour dimensions");
    var missingAsset = false;
    var missingAtlas = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "missing-asset") missingAsset = true;
      if (finding.code == "missing-atlas-data") missingAtlas = true;
    }}
    if (missingAsset) fail("solid colour treated as an asset path");
    if (missingAtlas) fail("static graphic required atlas metadata");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_packer_txt_atlas_is_case_safe_and_preserved(self):
        stage = {
            "version": "1.0.0",
            "name": "Packer Stage",
            "props": [{
                "name": "treeLoop",
                "assetPath": "stages/weebTrees.txt",
                "animType": "packer",
                "position": [0, 0],
                "animations": [{
                    "name": "treeLoop",
                    "frameIndices": list(range(19)),
                    "frameRate": 12,
                    "looped": True,
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            image_root = fixture / "Shared/Images/StAgEs"
            image_root.mkdir(parents=True)
            (image_root / "WEEBTREES.PNG").write_bytes(b"png")
            (image_root / "WEEBTREES.TxT").write_text("0\n")
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    if (converted.assets.length != 2) fail("packer asset mappings: " + converted.assets.length);
    var sawPng = false;
    var sawTxt = false;
    for (mapping in converted.assets) {{
      if (mapping.destination == "prop-treeloop-0.png") sawPng = mapping.source.indexOf("WEEBTREES.PNG") >= 0;
      if (mapping.destination == "prop-treeloop-0.txt") sawTxt = mapping.source.indexOf("WEEBTREES.TxT") >= 0;
    }}
    if (!sawPng || !sawTxt) fail("case-safe packer mappings");
    if (converted.hscript.indexOf("fromSpriteSheetPacker(hscriptPath + \\\"prop-treeloop-0.png\\\", hscriptPath + \\\"prop-treeloop-0.txt\\\")") < 0) fail("packer runtime loader");
    if (converted.hscript.indexOf("addByIndices(\\\"treeLoop\\\", \\\"\\\", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]") < 0) fail("packer frame sequence");
    for (finding in converted.diagnostics)
      if (finding.code == "missing-atlas-data") fail("TXT atlas treated as missing");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_script_owned_stage_prop_requires_emitted_runtime_loader_and_asset(self):
        stage = {
            "version": "1.0.0",
            "name": "Concert",
            "props": [{"name": "teto", "assetPath": None}],
        }
        hxc = r'''
class ConcertStage extends Stage {
    var teto:FlxSprite;
    override function onCreate(event:ScriptEvent):Void {
        teto = new FlxSprite(0, 0);
        teto.frames = Paths.getSparrowAtlas("stage/teto_idle");
        add(teto);
    }
}
'''
        unresolved_hxc = r'''
class Concert2Stage extends Stage {
    var teto:FlxSprite;
    override function onCreate(event:ScriptEvent):Void {
        // The JSON prop is intentionally unresolved; no Teto sprite is made.
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/stage").mkdir(parents=True)
            (fixture / "images/stage/teto_idle.png").write_bytes(b"png")
            (fixture / "images/stage/teto_idle.xml").write_text("<TextureAtlas />")
            (fixture / "scripts/stages").mkdir(parents=True)
            (fixture / "scripts/stages/concert.hxc").write_text(hxc)
            (fixture / "scripts/stages/concert2.hxc").write_text(unresolved_hxc)
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasMissing(stage:Dynamic):Bool {{
    var findings:Array<Dynamic> = cast stage.diagnostics;
    for (finding in findings) if (finding.code == "missing-prop-asset") return true;
    return false;
  }}
  static function main() {{
    var data = Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))}));
    var owned = VSliceImporter.convertStage(data, {haxe_string(str(fixture))}, "concert");
    if (hasMissing(owned)) fail("runtime-owned prop was still diagnosed");
    var unresolved = VSliceImporter.convertStage(data, {haxe_string(str(fixture))}, "concert2");
    if (!hasMissing(unresolved)) fail("unresolved script prop was suppressed");
  }}
}}
'''
            result = self.run_fixture(main, fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_vslice_fixture_is_read_only_and_converts_when_available(self):
        root = EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice"
        metadata = root / "data/songs/fantasy-girl-01/fantasy-girl-01-metadata.json"
        chart = root / "data/songs/fantasy-girl-01/fantasy-girl-01-chart.json"
        if not metadata.exists() or not chart.exists():
            self.skipTest("example V-Slice fixture is not mounted")
        main = f'''class Main {{
  static function main() {{
    var result = VSliceImporter.convertFiles({haxe_string(str(metadata))}, {haxe_string(str(chart))});
    if (result.charts.length != 1) throw "real fixture difficulty count";
    var total = 0;
    for (section in (cast result.charts[0].chart.song.notes:Array<Dynamic>))
      total += (cast section.sectionNotes:Array<Dynamic>).length;
    if (total != 1060) throw "real fixture note count";
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_sadbf_split_animation_omissions_are_precise(self):
        """The mounted DDTO++ source omits both alternate game-over atlases."""

        root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
        character = root / "data/characters/sadbf.json"
        if not character.exists():
            self.skipTest("mounted DDTO++ V-Slice fixture is not mounted")
        missing_assets = [
            root / "shared/images/characters/SadBFDies_Assets.png",
            root / "shared/images/characters/SadBFDies_Assets.astc",
            root / "shared/images/characters/MarkovGameOver.png",
            root / "shared/images/characters/MarkovGameOver.astc",
        ]
        for path in missing_assets:
            self.assertFalse(path.exists(), f"donor unexpectedly gained {path.name}")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character))})), {haxe_string(str(root))}, "sadbf", true, {haxe_string(str(character))});
    var switches = 0;
    var missing = 0;
    var sad = false;
    var markov = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "animation-asset-switch") {{
        switches++;
        if (finding.message.indexOf("SadBFDies_Assets") >= 0) sad = true;
        if (finding.message.indexOf("MarkovGameOver") >= 0) markov = true;
        if (finding.path != {haxe_string(str(character))}) fail("split switch did not retain character source path: " + finding.path);
        if (finding.message.indexOf("Search root: ") < 0) fail("split switch omitted searched-root evidence");
      }}
      if (finding.code == "missing-asset") {{
        missing++;
        if (finding.path != {haxe_string(str(character))}) fail("missing atlas did not retain character source path: " + finding.path);
        if (finding.message.indexOf("Search root: ") < 0) fail("missing atlas omitted searched-root evidence");
      }}
    }}
    if (switches != 2 || missing != 2 || !sad || !markov)
      fail("mounted split-asset diagnostics: " + switches + "/" + missing);
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_silhouette_monika_uses_donor_pixel_icon(self):
        root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
        character = root / "data/characters/silhouettemonika.json"
        icon = root / "images/freeplay/icons/monikapixel.png"
        if not character.exists() or not icon.exists():
            self.skipTest("mounted DDTO++ silhouette fixture is not mounted")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character))})), {haxe_string(str(root))}, "silhouettemonika");
    var icon = false;
    var missing = false;
    for (mapping in converted.assets)
      if (mapping.kind == "health-icon" && mapping.source.indexOf("monikapixel.png") >= 0) icon = true;
    for (finding in converted.diagnostics)
      if (finding.code == "missing-health-icon") missing = true;
    if (!icon || missing) fail("mounted silhouette icon alias");
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_bigsayo_legacy_animation_aliases_are_convertible(self):
        """TAKEOVER's mounted big-sayori definition uses the legacy aliases."""

        root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
        character = root / "data/characters/bigsayo.json"
        atlas = root / "shared/images/characters/Doki_BigSayori_Assets.astc"
        if not character.exists() or not atlas.exists():
            self.skipTest("mounted DDTO++ big-sayori fixture is not mounted")
        source = json.loads(character.read_text())
        animations = source.get("animations", [])
        self.assertEqual(len(animations), 5)
        self.assertTrue(all("fps" in item and "indices" in item and "looped" in item for item in animations))
        self.assertTrue(all("frameRate" not in item and "frameIndices" not in item for item in animations))
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character))})), {haxe_string(str(root))}, "bigsayo");
    if (converted.hscript.indexOf('char.animation.addByPrefix("idle", "Big Sayo Idle", 24') < 0)
      fail("mounted legacy idle animation");
    if (converted.hscript.indexOf('char.animation.addByPrefix("singLEFT", "Big Sayo Left", 24') < 0)
      fail("mounted legacy sing animation");
    for (finding in converted.diagnostics)
      if (finding.code == "invalid-character-animation") fail("mounted legacy animation was discarded");
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_wacky_camera_flash_events_keep_vslice_units(self):
        root = EXAMPLES / "v-slice/Wacky World UPDATE [V-Slice]"
        chart = root / "data/songs/wacky-world/wacky-world-chart.json"
        if not chart.exists():
            self.skipTest("mounted Wacky World V-Slice chart is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var chart:Dynamic = Json.parse(sys.io.File.getContent({haxe_string(str(chart))}));
    var count = 0;
    var explicitGameTarget = 0;
    for (event in (cast chart.events:Array<Dynamic>)) {{
      if (event.e != "extra-events-cameraFlashEvent") continue;
      var route = EngineCompat.routeVSliceEvent(event.e, event.v);
      if (route.name != "Camera Flash") fail("mounted route name");
      if (route.v2 != Std.string(event.v.duration)) fail("mounted duration payload");
      if (route.v1 == "hud") fail("mounted game flash became HUD flash");
      var options = EngineCompat.eventOptions(route.v3);
      if (options == null || options.durationSteps != true)
        fail("mounted duration lost step units");
      if (event.v.applyToHud == false) explicitGameTarget++;
      count++;
    }}
    if (count != 5) fail("mounted camera flash count: " + count);
    if (explicitGameTarget != 2) fail("mounted explicit game target count");
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_wacky_focus_camera_preserves_character_and_tween_payload(self):
        """V-Slice FocusCamera rows are not coordinate-only camera locks."""

        root = EXAMPLES / "v-slice/Wacky World UPDATE [V-Slice]"
        chart = root / "data/songs/wacky-world/wacky-world-chart.json"
        if not chart.exists():
            self.skipTest("mounted Wacky World V-Slice chart is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var chart:Dynamic = Json.parse(sys.io.File.getContent({haxe_string(str(chart))}));
    var count = 0;
    var charOnly = 0;
    var coordinate = 0;
    var instant = 0;
    for (event in (cast chart.events:Array<Dynamic>)) {{
      if (event.e != "FocusCamera") continue;
      var route = EngineCompat.routeVSliceEvent(event.e, event.v);
      if (route == null || route.name != "Focus Camera") fail("mounted FocusCamera route");
      var options = EngineCompat.eventOptions(route.v3);
      if (options == null || options.char == null || options.char != event.v.char)
        fail("mounted character slot");
      if (event.v.x == null) {{
        if (route.v1 != "0" || route.v2 != "0") fail("char-only coordinates");
        charOnly++;
      }} else {{
        if (route.v1 != Std.string(event.v.x) || route.v2 != Std.string(event.v.y))
          fail("mounted coordinates");
        if (event.v.duration != null && options.duration != event.v.duration)
          fail("mounted duration");
        if (event.v.ease != null && options.ease != event.v.ease)
          fail("mounted ease");
        coordinate++;
      }}
      if (event.v.ease == "INSTANT") instant++;
      count++;
    }}
    if (count != 28 || charOnly == 0 || coordinate == 0 || instant == 0)
      fail("mounted FocusCamera coverage: " + count + "/" + charOnly + "/" + coordinate + "/" + instant);
  }}
}}
        '''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("case 'Focus Camera':", play_state)
        self.assertIn("FocusCamera({", play_state)
        self.assertIn("function resolveFocusCameraEase", play_state)
        self.assertIn("Reflect.field(focusOptions, 'easeDir')", play_state)
        self.assertIn("easeDir: focusEaseDir", play_state)

    def test_mounted_vslice_note_styles_preserve_pixel_and_classify_donor_optional_assets(self):
        pixel_root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
        pixel_metadata = pixel_root / "data/songs/your-demise/your-demise-metadata.json"
        pixel_chart = pixel_root / "data/songs/your-demise/your-demise-chart.json"
        custom_root = EXAMPLES / "v-slice/Wacky World UPDATE [V-Slice]"
        custom_metadata = custom_root / "data/songs/wacky-world/wacky-world-metadata.json"
        custom_chart = custom_root / "data/songs/wacky-world/wacky-world-chart.json"
        if not all(path.exists() for path in (pixel_metadata, pixel_chart, custom_metadata, custom_chart)):
            self.skipTest("mounted V-Slice note-style fixtures are not available")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var pixel = VSliceImporter.convertFiles({haxe_string(str(pixel_metadata))}, {haxe_string(str(pixel_chart))});
    if (pixel.charts.length == 0 || pixel.charts[0].chart.song.uiType != "pixel")
      fail("mounted pixel noteStyle");
    var customStyle = VSliceImporter.convertNoteStyle(
      haxe.Json.parse(sys.io.File.getContent({haxe_string(str(custom_root / "data/notestyles/Pomni.json"))})),
      {haxe_string(str(custom_root))}, "Pomni");
    if (!customStyle.supported || customStyle.name != "vslice-pomni")
      fail("mounted custom style adapter");
    if (customStyle.registryEntry.holdCoverEnabled != true)
      fail("mounted custom hold-cover runtime flag");
    var coverMappings = 0;
    for (mapping in customStyle.assets)
      if (mapping.destination.indexOf("holdCover") == 0) coverMappings++;
    if (coverMappings != 8)
      fail("mounted custom hold-cover materialization mappings: " + coverMappings);
    var imageFallback = false;
    var audioFallback = false;
    var missingAudio = false;
    var nativeImageFallback = false;
    var missingAsset = false;
    for (finding in customStyle.diagnostics) {{
      if (finding.code == "note-style-hold-cover" || finding.code == "missing-note-style-hold-cover")
        fail("mounted custom hold-cover diagnostic: " + finding.code);
      if (finding.code == "note-style-countdown-fallback") imageFallback = true;
      if (finding.code == "note-style-countdown-audio-fallback") audioFallback = true;
      if (finding.code == "missing-note-style-audio") missingAudio = true;
      if (finding.code == "note-style-native-fallback") nativeImageFallback = true;
      if (finding.code == "missing-asset") missingAsset = true;
    }}
    if (!imageFallback || !audioFallback || missingAudio || !nativeImageFallback || missingAsset)
      fail("mounted donor-optional countdown classification");
    var miku = VSliceImporter.convertNoteStyle(
      haxe.Json.parse(sys.io.File.getContent({haxe_string(str((EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice") / "data/notestyles/HatsuneMiku.json"))})),
      {haxe_string(str(EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice"))}, "HatsuneMiku");
    if (miku.registryEntry.holdCoverEnabled == true)
      fail("disabled Miku hold-cover was enabled");
    for (mapping in miku.assets)
      if (mapping.destination.indexOf("holdCover") == 0)
        fail("disabled Miku hold-cover was materialized");
  }}
}}
'''
        result = self.run_fixture(main, pixel_root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_hold_cover_runtime_contract_is_style_driven(self):
        """Generated hold-cover metadata reaches the pooled HUD runtime."""
        judgement = (ROOT / "source/Judgement.hx").read_text()
        self.assertIn("holdCoverEnabled:Bool", judgement)
        self.assertIn("holdCoverStartPrefixes:Array<String>", judgement)
        importer = (ROOT / "source/VSliceImporter.hx").read_text()
        for token in (
            "missing-note-style-hold-cover",
            "holdCoverAssets",
            "holdCoverStartPrefixes",
            "holdCoverEnabled: holdCoverEnabled",
        ):
            self.assertIn(token, importer)
        cover = (ROOT / "source/NoteHoldCover.hx").read_text()
        for token in ("playStart", "playContinue", "playEnd", "DynamicAtlasFrames.combineSparrow"):
            self.assertIn(token, cover)
        strumline = (ROOT / "source/Strumline.hx").read_text()
        for token in ("noteHoldCovers", "playNoteHoldCover", "endNoteHoldCover", "endNoteHoldCoverAtLane", "getFirstAvailable"):
            self.assertIn(token, strumline)
        self.assertIn("Reflect.setField(headNote, 'cover', cover)", strumline)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("strums.playNoteHoldCover(note);", play_state)
        self.assertIn("add(enemyStrums.noteHoldCovers);", play_state)
        self.assertIn("add(playerStrums.noteHoldCovers);", play_state)
        self.assertIn("endNoteHoldCover(note);", play_state)
        self.assertIn("revive();", cover)

    def test_vslice_hold_cover_pool_and_early_end_helpers_execute(self):
        """Pooled activation, sustain-head resolution, and forced end are executable."""
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var head:Dynamic = {isSustainNote: false, noteData: 2};
    var sustain:Dynamic = {isSustainNote: true, prevNote: head, noteData: 2};
    var wrapper:Dynamic = {nativeNote: sustain};
    if (NoteHoldCoverCompat.resolveHead(wrapper) != head)
      fail("sustain segment did not resolve to hold head");
    var pooled = NoteHoldCoverCompat.activate();
    if (!pooled.alive || !pooled.exists || !pooled.active)
      fail("pooled cover was not revived");
    if (!NoteHoldCoverCompat.shouldEnd(100, 101))
      fail("authored end was not recognized");
    if (!NoteHoldCoverCompat.shouldEnd(100, 0, true))
      fail("forced miss/cancel end was not recognized");
    if (NoteHoldCoverCompat.shouldEnd(Math.POSITIVE_INFINITY, 999, false))
      fail("infinite cover ended without miss/cancel");
  }
}'''
        result = self.run_fixture(main, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_vslice_character_and_stage_fixtures_are_read_only_and_convertible(self):
        root = EXAMPLES / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice"
        character = root / "data/characters/m1ku.json"
        stage = root / "data/stages/concert.json"
        if not character.exists() or not stage.exists():
            self.skipTest("example V-Slice character/stage fixtures are not mounted")
        main = f'''import haxe.Json;
class Main {{
  static function main() {{
    var character = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character))})), {haxe_string(str(root))});
    if (character.name != "m1ku" || character.registryEntry.like != "m1ku") throw "real character identity";
    if (character.assets.length < 2) throw "real character asset mappings";
    if (character.hscript.indexOf("addByPrefix(\\\"singLEFT\\\"") < 0) throw "real character animations";
    var stage = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage))})), {haxe_string(str(root))});
    if (stage.name != "concert" || stage.hscript.indexOf("setDefaultZoom(0.65)") < 0) throw "real stage identity/zoom";
    if (stage.hscript.indexOf("boyfriend.x = 889") < 0 || stage.hscript.indexOf("dad.x = 50") < 0) throw "real stage positions";
    // concert's Teto prop intentionally has no assetPath, but the companion
    // stage HXC constructs and loads it at runtime, so it is script-owned.
    var missingProp = false;
    for (finding in stage.diagnostics) if (finding.code == "missing-prop-asset") missingProp = true;
    if (missingProp) throw "real stage script-owned prop diagnostic";
    var stage2Path = {haxe_string(str(root / "data/stages/concert2.json"))};
    var stage2 = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent(stage2Path)), {haxe_string(str(root))}, "concert2", stage2Path);
    var unresolvedProp = false;
    for (finding in stage2.diagnostics) if (finding.code == "missing-prop-asset") {{
      unresolvedProp = true;
      if (finding.path != stage2Path) throw "future-sound prop did not retain stage source path: " + finding.path;
      if (finding.message.indexOf("no matching runtime HXC sprite") < 0) throw "future-sound prop did not explain runtime ownership gap";
    }}
    if (!unresolvedProp) throw "real unresolved stage prop diagnostic";
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        concert2_script = root / "scripts/stages/concert2.hxc"
        self.assertTrue(concert2_script.exists())
        concert2_source = concert2_script.read_text(errors="ignore")
        self.assertNotIn("teto = new FlxSprite", concert2_source)
        self.assertNotIn('getSparrowAtlas("stage/TB/teto_idle")', concert2_source)

    def test_vslice_base_character_atlas_can_use_exact_native_registry_fallback(self):
        """Base-game V-Slice atlases are supplied by the destination engine."""
        root = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
        normal = root / "data/characters/senpai-ddto.json"
        angry = root / "data/characters/senpai-angry-ddto.json"
        wilted_metadata = root / "data/songs/wilted/wilted-metadata.json"
        wilted_chart = root / "data/songs/wilted/wilted-chart.json"
        native_png = ROOT / "assets/images/custom_chars/senpai/char.png"
        native_xml = ROOT / "assets/images/custom_chars/senpai/char.xml"
        if (not normal.exists() or not angry.exists() or not wilted_metadata.exists()
                or not wilted_chart.exists() or not native_png.exists() or not native_xml.exists()):
            self.skipTest("mounted TAKEOVER/base Senpai fixture is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function check(path:String, expected:String):Void {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent(path)), {haxe_string(str(root))});
    var missing = false;
    var native = false;
    for (finding in converted.diagnostics) {{
      if (finding.code == "missing-asset") missing = true;
      if (finding.code == "native-character-asset") native = true;
    }}
    if (missing) fail("base atlas reported missing: " + path);
    if (!native) fail("native atlas fallback was not reported: " + path);
    if (converted.hscript.indexOf("assets/images/custom_chars/senpai/") < 0)
      fail("generated script did not reference the native atlas: " + path);
    if (converted.hscript.indexOf(expected) < 0)
      fail("required animation prefix was not retained: " + expected);
  }}
  static function main() {{
    if (EngineCompat.vSliceNativeCharacterCandidates("characters/not-a-stock-character").length != 0)
      fail("custom logical character crossed the native boundary");
    var song = VSliceImporter.convertFiles({haxe_string(str(wilted_metadata))}, {haxe_string(str(wilted_chart))}, {haxe_string(str(root))});
    var sawAngryReference = false;
    for (reference in song.eventCharacterReferences)
      if (reference == "senpai-angry-ddto") sawAngryReference = true;
    if (!sawAngryReference) fail("character-change event reference was not discovered");
    check({haxe_string(str(normal))}, "Senpai Idle instance 10");
    check({haxe_string(str(angry))}, "Angry Senpai Idle instance 1");
  }}
}}
'''
        result = self.run_fixture(main, root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
