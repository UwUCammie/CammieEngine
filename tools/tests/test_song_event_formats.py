from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SongEventFormatsTest(unittest.TestCase):
    def test_modern_psych_object_events_are_normalized(self):
        """Psych's compact t/e/v records must reach the native event pump."""
        fixture = '''class ModernPsychEventsFixture {
 static function main(){
  var payload=haxe.Json.parse('{"events":[{"t":12.5,"e":"FocusCamera","v":["1","2"]},{"time":24,"event":"Camera Flash","v":"0.5;1"},{"t":36,"name":"Zoom","v":{"value1":"0.1","value2":"0.2"}},{"t":48,"e":"Gap","v":{"v2":"kept-in-slot-2"}}]}');
  var events=SongEvents.collect(SongEvents.fromSong(payload),null);
  if(events.length!=4)throw 'Psych object events were dropped';
  if(events[0].time!=12.5||events[0].name!='FocusCamera'||events[0].v1!='1'||events[0].v2!='2')throw 'array-valued event changed';
  if(events[1].time!=24||events[1].name!='Camera Flash'||events[1].v1!='0.5'||events[1].v2!='1')throw 'string-valued event changed';
  if(events[2].time!=36||events[2].name!='Zoom'||events[2].v1!='0.1'||events[2].v2!='0.2')throw 'object-valued event changed';
  if(events[3].name!='Gap'||events[3].v1!=''||events[3].v2!='kept-in-slot-2')throw 'object event values shifted slots';
  Sys.println('OK');
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "ModernPsychEventsFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "ModernPsychEventsFixture"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_funkadelix_actor_lyric_events_keep_their_targets(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods") / (
            "funkadelixv1/assets/shared/data/spookeez/events.json"
        )
        if not donor.is_file():
            self.skipTest("example donor is not mounted")
        fixture = '''class LyricEventsFixture {
 static function main(){
  var events=SongEvents.collect(SongEvents.fromSong(haxe.Json.parse(sys.io.File.getContent(Sys.args()[0]))),null);
  var lyrics=0; var second=0; var clear=0;
  for(event in events) {
   if(event.name=='Lyrics') { lyrics++; if(lyrics==1 && event.v2!='skid')throw 'Lyrics actor was dropped'; }
   if(event.name=='Second Lyric Line') { second++; if(second==1 && event.v2!='skid')throw 'Second lyric actor was dropped'; }
   if(event.name=='Clear Lyrics') { clear++; if(clear==1 && event.v1!='bf')throw 'Clear lyric actor was dropped'; }
  }
  if(lyrics!=73||second!=47||clear!=12)throw 'Funkadelix lyric event counts changed';
  Sys.println('OK');
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "LyricEventsFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "LyricEventsFixture", str(donor)],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_fps_plus_sidecar_rows_are_normalized_and_real_donor_is_read_only(self):
        """FPS Plus keeps events as section/time/semicolon rows in a wrapper."""
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods") / (
            "whitty/data/songs/remorse/events.json"
        )
        if not donor.is_file():
            self.skipTest("example donor is not mounted")
        fixture = '''class EventFormatsFixture {
 static function main(){
  var wrapped=haxe.Json.parse('{"events":{"events":[[56,112000,0,"changeCharacter;bf;BfUpdikeEdgy"],[56,112009.375,1,"changeCharacter;gf;GfKinkyEdgy"]]}}');
  var normalized=SongEvents.collect(SongEvents.fromSong(wrapped),null);
  if(normalized.length!=2||normalized[0].time!=112000||normalized[0].name!='changeCharacter'
    ||normalized[0].v1!='bf'||normalized[0].v2!='BfUpdikeEdgy')throw 'FPS sidecar row was not normalized';
  var direct=haxe.Json.parse('{"events":[[64,"Camera Flash","0.5","1"]]}');
  var directEvents=SongEvents.collect(SongEvents.fromSong(direct),null);
  if(directEvents.length!=1||directEvents[0].name!='Camera Flash'||directEvents[0].v1!='0.5'||directEvents[0].v2!='1')throw 'direct legacy row was not normalized';
  var donor=haxe.Json.parse(sys.io.File.getContent(Sys.args()[0]));
  var actual=SongEvents.collect(SongEvents.fromSong(donor),null);
  if(actual.length!=6||actual[0].name!='changeCharacter'||actual[0].time!=112000)throw 'mounted FPS fixture changed';
  var overheadPath=Sys.args()[1];
  if(!sys.FileSystem.exists(overheadPath))throw 'mounted FPS overhead fixture missing';
  var overhead=SongEvents.collect(SongEvents.fromSong(haxe.Json.parse(sys.io.File.getContent(overheadPath))),null);
  var toggles=0;
  for(event in overhead) if(event.name=='toggleCamMovement') {
   if(toggles==0 && event.v1!='1')throw 'FPS toggle enable bit was dropped';
   if(toggles==1 && event.v1!='0')throw 'FPS toggle disable bit was dropped';
   toggles++;
  }
  if(toggles!=10)throw 'FPS toggle rows changed';
  Sys.println('OK');
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "EventFormatsFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "EventFormatsFixture", str(donor),
                 str(donor.parent.parent / "overhead/events.json")],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_mounted_fps_sidecars_preserve_rows_and_reach_native_routes(self):
        """All mounted FPS Plus rows retain their payloads and native ownership."""
        donor_root = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty/data/songs")
        donors = [donor_root / song / "events.json" for song in ("ballistic", "overhead", "remorse")]
        if not all(path.is_file() for path in donors):
            self.skipTest("mounted FPS Plus sidecars are not available")

        before = {
            path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
            for path in donors
        }
        fixture = r'''class MountedFpsEventsFixture {
 static function fail(message:String):Void throw message;
 static function main(){
  var nativeNames = ["Legacy Camera Zoom", "Camera Follow Pos",
   "Toggle Camera Movement", "Add Camera Zoom", "Change Character"];
  for(path in Sys.args()) {
   var root:Dynamic = haxe.Json.parse(sys.io.File.getContent(path));
   var wrapper:Dynamic = Reflect.field(root, "events");
   var rows:Array<Dynamic> = cast Reflect.field(wrapper, "events");
   var normalized = SongEvents.collect(SongEvents.fromSong(root), null);
   if(normalized.length != rows.length)
    fail(path + " row count changed: " + rows.length + " -> " + normalized.length);
   for(index in 0...rows.length) {
    var row:Array<Dynamic> = cast rows[index];
    var expectedTime = Std.parseFloat(Std.string(row[1]));
    var parts = Std.string(row[3]).split(";");
    var expectedName = parts[0];
    var expectedV1 = parts.length > 1 ? parts[1] : "";
    var expectedV2 = parts.length > 2 ? parts[2] : "";
    var expectedV3 = parts.length > 3 ? parts[3] : "";
    if(expectedName.toLowerCase() == "togglecammovement" && parts.length == 1)
     expectedV1 = Std.string(row[2]);
    var event:Dynamic = normalized[index];
    if(event.time != expectedTime || event.name != expectedName
      || event.v1 != expectedV1 || event.v2 != expectedV2 || event.v3 != expectedV3)
     fail(path + " row " + index + " changed at the SongEvents boundary");
    var route = EngineCompat.routeLegacyEvent(event.name, event.v1, event.v2, event.v3);
    if(route == null || nativeNames.indexOf(EngineCompat.eventName(route.name)) < 0)
     fail(path + " row " + index + " has no native route: " + event.name);
    if(expectedName.toLowerCase() == "cambopbig"
      && (route.v1 != "0.03" || route.v2 != "0.06"))
     fail(path + " row " + index + " lost camBopBig native defaults");
    Sys.println("EVENT|" + haxe.Json.stringify({song:path, index:index, time:event.time,
     name:event.name, v1:event.v1, v2:event.v2, v3:event.v3, route:route.name,
     routeV1:route.v1, routeV2:route.v2, routeV3:route.v3}));
   }
  }
  Sys.println("OK");
 }
}'''
        build_tmp = ROOT / "tmp"
        build_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build_tmp) as folder:
            (Path(folder) / "MountedFpsEventsFixture.hx").write_text(fixture, newline='\n')
            environment = os.environ.copy()
            environment["TMPDIR"] = str(build_tmp)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "MountedFpsEventsFixture", *(str(path) for path in donors)],
                cwd=ROOT, env=environment, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("OK", output)

        events = []
        for line in output.splitlines():
            if line.startswith("EVENT|"):
                events.append(json.loads(line.split("|", 1)[1]))
        self.assertEqual(len(events), 84)
        self.assertEqual(
            {
                Path(event["song"]).parent.name: sum(
                    1 for candidate in events if Path(candidate["song"]).parent.name == Path(event["song"]).parent.name
                )
                for event in events
            },
            {"ballistic": 15, "overhead": 63, "remorse": 6},
        )
        counts = {}
        route_counts = {}
        for event in events:
            counts[event["name"]] = counts.get(event["name"], 0) + 1
            route_counts[event["route"]] = route_counts.get(event["route"], 0) + 1
        self.assertEqual(counts, {
            "camZoom": 55,
            "changeCharacter": 8,
            "camMove": 7,
            "toggleCamMovement": 10,
            "camBopBig": 4,
        })
        self.assertEqual(route_counts, {
            "Legacy Camera Zoom": 55,
            "Change Character": 8,
            "Camera Follow Pos": 7,
            "Toggle Camera Movement": 10,
            "Add Camera Zoom": 4,
        })
        self.assertEqual(
            [(event["name"], event["v1"], event["v2"]) for event in events if event["name"] == "camZoom"][:1],
            [("camZoom", "0.9", "2.2")],
        )
        toggles = [event["v1"] for event in events if event["name"] == "toggleCamMovement"]
        self.assertEqual(toggles, ["1", "0", "1", "0", "0", "0", "0", "0", "0", "0"])
        self.assertEqual(
            [(event["name"], event["v1"], event["v2"]) for event in events if event["name"] == "camBopBig"],
            [("camBopBig", "", "")] * 4,
        )

        playstate = (ROOT / "source/PlayState.hx").read_text()
        for native_name in (
            "Legacy Camera Zoom", "Camera Follow Pos", "Toggle Camera Movement",
            "Add Camera Zoom", "Change Character",
        ):
            self.assertRegex(
                playstate,
                rf"case ['\"]{re.escape(native_name)}['\"]",
                f"mounted route lacks a PlayState native case: {native_name}",
            )
        self.assertEqual(
            before,
            {
                path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in donors
            },
        )

    def test_all_companion_files_and_legacy_deduplication(self):
        fixtures = [
            ROOT / 'assets/data/really-happy/events.json',
            ROOT / 'assets/data/terrible-fate/events.json',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted companion-event fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        fixture = '''class EventFormatsTest {
 static function main(){
  var summaries=[];
  for(dir in sys.FileSystem.readDirectory('assets/data')) {
   var path='assets/data/'+dir+'/events.json';
   if(!sys.FileSystem.exists(path))continue;
   var groups=SongEvents.fromSong(haxe.Json.parse(sys.io.File.getContent(path)));
   var events=SongEvents.collect(groups,null);
   summaries.push({song:dir,count:events.length});
   var prev=-1e20;
   for(e in events){if(e.time<prev)throw 'Unsorted '+dir;prev=e.time;}
  }
  var old=SongEvents.fromSong(haxe.Json.parse('{"song":{"notes":[{"sectionNotes":[[10,-1,"custom","a","b","c"],[10,-1,"custom","a","b","d"],[20,0,0]]}]}}'));
  var embedded=SongEvents.fromSong(haxe.Json.parse('{"song":"example","events":[[10,[["custom","a","b","c"]]]]}'));
  var merged=SongEvents.collect(embedded,old);
  if(merged.length!=2||merged[0].v3!='c'||merged[1].v3!='d')throw 'Lost distinct custom arguments or replayed duplicate';
  if(SongEvents.collect(null,SongEvents.fromSong(null)).length!=0)throw 'Empty files';
  Sys.println(haxe.Json.stringify(summaries));
 }
}'''
        expected = {}
        for path in (ROOT / 'assets/data').glob('*/events.json'):
            data = json.loads(path.read_text())
            song = data.get('song', data)
            groups = list(song.get('events') or [])
            for section in song.get('notes') or []:
                for row in section.get('sectionNotes') or []:
                    if len(row) >= 3 and row[1] == -1 and isinstance(row[2], str):
                        groups.append([row[0], [row[2:6]]])
            unique = set()
            for group in groups:
                for event in group[1]:
                    values = tuple('' if i >= len(event) or event[i] is None else str(event[i]) for i in range(1, 4))
                    unique.add((group[0], event[0], *values))
            expected[path.parent.name] = len(unique)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'EventFormatsTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-cp', str(ROOT / 'source'), '-main', 'EventFormatsTest', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            actual = {row['song']: row['count'] for row in json.loads(result.stdout)}
            self.assertEqual(actual, expected)
            self.assertEqual(actual['really-happy'], 499)
            self.assertEqual(actual['terrible-fate'], 24)
