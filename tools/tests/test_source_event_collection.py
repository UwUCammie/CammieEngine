"""Check native and source-family event ordering and duplicate policies."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''package;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function names(events:Array<Dynamic>):String
  return [for (event in events) event.name].join(",");

 static function main():Void {
  var embedded:Array<Dynamic> = [
   [300.0, [["late-chart", "c", "d", "chart-v3"]]],
   [100.0, [["same", "a", "b", "same-v3"],
    ["repeat", "r", "s", "repeat-v3"], ["repeat", "r", "s", "repeat-v3"]]]
  ];
  var companion:Array<Dynamic> = [
   [200.0, [["middle", "m", "n", "middle-v3"]]],
   [100.0, [["same", "a", "b", "same-v3"], ["companion", "x", "y", "comp-v3"]]],
   [300.0, [["same", "a", "b", "other-v3"]]]
  ];

  var native = SongEvents.collect(embedded, companion);
  check(names(native) == "same,repeat,companion,middle,late-chart,same",
   "native collection should dedupe exact rows and sort chronologically: " + names(native));
  check(native[4].v3 == "chart-v3" && native[5].v3 == "other-v3",
   "native exact dedupe should retain rows with distinct v3 payloads");

  var nullableRows:Array<Dynamic> = [
   [75.0, [["ExplicitNull", null]]],
   [80.0, [["MissingValues"]]]
  ];
  var psychNullable = SongEvents.collect(nullableRows, null, true);
  check(psychNullable.length == 2 && psychNullable[0].v1 == null
    && psychNullable[0].v2 == null && psychNullable[1].v1 == null
    && psychNullable[1].v2 == null,
   "source-order collection should preserve explicit-null and missing values for source callbacks");
  var nativeNullable = SongEvents.collect(nullableRows, null);
  check(nativeNullable.length == 2 && nativeNullable[0].v1 == ""
    && nativeNullable[0].v2 == "" && nativeNullable[1].v1 == ""
    && nativeNullable[1].v2 == "",
   "default native collection should continue normalizing nullable values to empty strings");

  var directEvents:Array<Dynamic> = [["Shared", "same", "args", "route-v3"],
   ["ChartTie", "chart", "tie", ""]];
  var directGroups:Array<Dynamic> = [[100.0, directEvents]];
  var legacyRows:Array<Dynamic> = [
   [100.0, -1, "Shared", "same", "args", "route-v3"],
   [100.0, -1, "LegacyA", "a", "one", ""],
   [99.0, -1, "LegacyEarlier", "e", "early", ""],
   [100.0, -1, "LegacyB", "b", "two", ""],
   [100.0, -1, "LegacyNull", null]
  ];
  var legacySections:Array<Dynamic> = [{sectionNotes:legacyRows}];
  var legacySong:Dynamic = {song:{events:directGroups, notes:legacySections}};
  var nvLegacyRows:Array<Dynamic> = [];
  for (rawRow in legacyRows) {
   var row:Array<Dynamic> = cast rawRow;
   var nvRow = row.copy();
   nvRow[1] = -4;
   nvLegacyRows.push(nvRow);
  }
  nvLegacyRows.push([100.0, -2, "FourKeyRawMinusTwo", "skip", "skip", ""]);
  nvLegacyRows.push([100.0, 0, "FourKeyNonnegative", "skip", "skip", ""]);
  var nvLegacySong:Dynamic = {song:{keys:4, notes:[{sectionNotes:nvLegacyRows}]}};
  var sidecarEvents:Array<Dynamic> = [["Shared", "same", "args", "sidecar-v3"],
   ["SidecarTie", "side", "car", ""]];
  var sidecarGroups:Array<Dynamic> = [[100.0, sidecarEvents]];
  var sidecarData:Dynamic = {song:{events:sidecarGroups}};
  var directOnly = SongEvents.fromSong(legacySong, false);
  check(directOnly.length == 1 && directOnly[0][1].length == 2,
   "includeLegacy=false should keep direct rows and exclude negative-type section rows");
  var defaultLegacy = SongEvents.fromSong(legacySong);
  var nativeLegacy = SongEvents.collect(defaultLegacy, null);
  check(names(nativeLegacy) == "LegacyEarlier,Shared,ChartTie,LegacyA,LegacyB,LegacyNull",
   "default fromSong/native collection should keep its historical legacy merge, exact dedupe, and time sort");
  var psychLegacy = SongEvents.collect(defaultLegacy, null, true);
  check(names(psychLegacy) == "Shared,ChartTie,Shared,LegacyA,LegacyEarlier,LegacyB,LegacyNull",
   "default Psych source collection should retain the previous authored legacy order and duplicate rows");

  var nvDirect = SongEvents.collect(directOnly, SongEvents.fromSong(sidecarData, false), true, true);
  check(names(nvDirect) == "Shared,SidecarTie,ChartTie",
   "NV should dedupe direct chart and companion rows while retaining companion-first source order");
  check(nvDirect[0].v3 == "sidecar-v3",
   "NV should keep the first direct source row when only v3 differs");
  SongEvents.appendLegacySourceEvents(nvDirect, nvLegacySong);
  check(names(nvDirect) == "Shared,SidecarTie,ChartTie,Shared,LegacyA,LegacyEarlier,LegacyB,LegacyNull",
   "legacy rows should append after deduplicated direct rows in authored order");
  check(nvDirect[0].order == 0 && nvDirect[2].order == 2
    && nvDirect[3].order == 3 && nvDirect[7].order == 7,
   "appended rows should receive a stable order after direct events");
  check(nvDirect[3].v3 == "route-v3" && nvDirect[7].v1 == null && nvDirect[7].v2 == null,
   "legacy/direct-identical NV events should remain duplicated, with null source values preserved");
  check(SongEvents.fromSong(nvLegacySong).length == 0,
   "default fromSong must retain its historical exact -1 selector for non-NV callers");

  check(!SongEvents.isNightmareVisionLegacyEventRow([0.0, -2], 4)
    && SongEvents.isNightmareVisionLegacyEventRow([0.0, -4], 4)
    && !SongEvents.isNightmareVisionLegacyEventRow([0.0, -5], 6)
    && SongEvents.isNightmareVisionLegacyEventRow([0.0, -6], 6),
   "NV legacy detection should follow integer playfield division at four- and six-key boundaries");
  var malformedNoteRow:Array<Dynamic> = [0.0, "not-a-number"];
  check(!SongEvents.isNightmareVisionLegacyEventRow(malformedNoteRow, 4)
    && !SongEvents.isNightmareVisionLegacyEventRow([0.0, -4], 0)
    && !SongEvents.isNightmareVisionLegacyEventRow([0.0, -4], -4),
   "NV legacy detection should reject malformed note data and invalid key counts");
  var missingKeysResult:Array<Dynamic> = [];
  var missingKeysRows:Array<Dynamic> = [
   [20.0, -2, "MissingKeysMinusTwo", "skip", "skip", ""],
   [21.0, -4, "MissingKeysMinusFour", "keep", "four", ""]
  ];
  var missingKeysChart:Dynamic = {song:{notes:[{sectionNotes:missingKeysRows}]}};
  SongEvents.appendLegacySourceEvents(missingKeysResult, missingKeysChart);
  check(names(missingKeysResult) == "MissingKeysMinusFour",
   "NV legacy appending should default to four keys only when the source chart omits keys");
  var sixKeysResult:Array<Dynamic> = [];
  var sixKeysRows:Array<Dynamic> = [
   [30.0, -5, "SixKeysMinusFive", "skip", "skip", ""],
   [31.0, -6, "SixKeysMinusSix", "keep", "six", ""]
  ];
  var sixKeysChart:Dynamic = {song:{keys:6, notes:[{sectionNotes:sixKeysRows}]}};
  SongEvents.appendLegacySourceEvents(sixKeysResult, sixKeysChart);
  check(names(sixKeysResult) == "SixKeysMinusSix",
   "NV legacy appending should use the preserved six-key count for its boundary");
  nvDirect.sort(function(a, b) return a.time < b.time ? -1 : a.time > b.time ? 1 : a.order - b.order);
  check(names(nvDirect) == "LegacyEarlier,Shared,SidecarTie,ChartTie,Shared,LegacyA,LegacyB,LegacyNull",
   "same-time direct event order should precede appended legacy events after source sorting");

  var psych = SongEvents.collect(embedded, companion, true);
  check(names(psych) == "middle,same,companion,same,late-chart,same,repeat,repeat",
   "Psych collection should visit companion first, preserve group order, and retain repeated rows: " + names(psych));

  var nvEmbedded:Array<Dynamic> = [
   [100.0, [["Near", "a", "b", "embedded-v3"]]],
   [110.0, [["SameValues", "left", "right", "embedded-v3"]]],
   [120.0, [["DifferentV1", "old", "right", ""]]],
   [130.0, [["DifferentV2", "left", "old", ""]]],
   [200.0, [["OutsideEpsilon", "x", "y", "embedded"]]]
  ];
  var nvCompanion:Array<Dynamic> = [
   [100.00000005, [["Near", "a", "b", "companion-v3"]]],
   [110.0, [["SameValues", "left", "right", "companion-v3"]]],
   [120.0, [["DifferentV1", "new", "right", ""]]],
   [130.0, [["DifferentV2", "left", "new", ""]]],
   [200.0000002, [["OutsideEpsilon", "x", "y", "companion"]]]
  ];
  var nightmareVision = SongEvents.collect(nvEmbedded, nvCompanion, false, true);
  check(nightmareVision.length == 8,
   "NV should collapse epsilon/name/v1/v2 matches, ignore v3, and keep non-matches; got " + nightmareVision.length);
  check(nightmareVision[0].time == 100.0 && nightmareVision[0].v3 == "embedded-v3"
    && nightmareVision[1].time == 110.0 && nightmareVision[1].v3 == "embedded-v3",
   "NV duplicate rows should retain the first embedded event and ignore v3 differences");
  check(nightmareVision[2].v1 == "old" && nightmareVision[3].v1 == "new"
    && nightmareVision[4].v2 == "old" && nightmareVision[5].v2 == "new",
   "NV equality must still require exact v1 and v2 values");
  check(nightmareVision[6].time == 200.0 && nightmareVision[7].time == 200.0000002,
   "NV timestamps outside the donor epsilon must remain distinct");

  var sidecar:Array<Dynamic> = ["Old Event", "one", "two", "three"];
  var sidecarKey = SongEvents.eventSignature(sidecar, 400.0);
  var replacement:Array<Dynamic> = ["Edited Event", "new", "values", "kept"];
  SongEvents.markEditorSidecarEvent(replacement, sidecarKey);
  var replacementResult = SongEvents.collect([[450.0, [replacement]],
   [400.0, [["Unrelated", "u", "v", "w"]]]], [[400.0, [sidecar]]], true);
  check(names(replacementResult) == "Edited Event,Unrelated",
   "an edited marked row should suppress its unchanged companion source row");

  var tombstone:Array<Dynamic> = ["Deleted Event", "gone", "gone", "gone"];
  var tombstoneKey = SongEvents.eventSignature(tombstone, 500.0);
  SongEvents.markEditorSidecarEvent(tombstone, tombstoneKey, true);
  check(SongEvents.isEditorSidecarTombstone(tombstone), "deleted source row should be marked as a tombstone");
  var deleted = SongEvents.collect([[500.0, [tombstone]]],
   [[500.0, [["Deleted Event", "gone", "gone", "gone"]]]], true);
  check(deleted.length == 0,
   "editor tombstones should suppress companion rows without leaking into callbacks");
 }
}
'''


class SourceEventCollectionTest(unittest.TestCase):
    def test_native_psych_nightmare_vision_and_editor_row_policies(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
