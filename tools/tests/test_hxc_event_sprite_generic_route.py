"""Static sprite events are routed by their descriptor, never by a fixed name."""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

EVENT_SOURCE = '''
class BannerFlashEvent extends ScriptedSongEvent {
    function new() super("Stage Banner");
    function handleEvent(data) {
        var left = data.value.posX;
        var top = data.value.posY;
        var banner = new FlxSprite(left, top);
        banner.frames = Paths.getSparrowAtlas("stage/banner");
        banner.animation.addByPrefix("show", "Banner Show", 24, false);
        banner.animation.play("show");
        banner.scrollFactor.set(0, 0);
        banner.cameras = [PlayState.instance.camHUD];
        banner.animation.finishCallback = function(s:String) {
            PlayState.instance.remove(banner);
            banner.kill();
        };
    }
}
'''


def strip_comments(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//[^\n]*", "", source)


class HxcEventSpriteGenericRouteTest(unittest.TestCase):
    def run_fixture(self, body):
        fixture = f'''import haxe.Json;
class SpriteRouteFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
        var source = {json.dumps(EVENT_SOURCE)};
        var descriptor = EngineCompat.eventSpriteDescriptorFromSource(source);
        if (descriptor == null) fail("fixture is not a static sprite event");
        var catalog = HxcEventSpriteDescriptor.parseCatalog(
            HxcEventSpriteDescriptor.serializeCatalog([descriptor]));
        {body}
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "SpriteRouteFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-main", "SpriteRouteFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_object_payload_row_is_routed_with_the_descriptor_fields(self):
        self.run_fixture('''
        var route = EngineCompat.routeEventSprite(catalog, "Stage Banner",
            Json.stringify({posX: 320, posY: -48}), "", "");
        if (route == null || route.name != "Stage Banner") fail("event id route");
        if (route.x != 320 || route.y != -48) fail("payload fields: " + route.x + "," + route.y);
        if (route.descriptor.atlasKey != "stage/banner") fail("descriptor not carried");
        ''')

    def test_positional_row_takes_x_and_y_from_the_first_two_values(self):
        self.run_fixture('''
        var route = EngineCompat.routeEventSprite(catalog, "Stage Banner", "120", "64", "");
        if (route == null || route.x != 120 || route.y != 64) fail("positional slots");
        var payload = EngineCompat.hxcSongEventPayload(["Stage Banner", "120", "64", ""],
            EngineCompat.eventSpriteDescriptorForName(catalog, "Stage Banner"));
        if (payload.eventData.value.posX != "120" || payload.eventData.value.posY != "64")
            fail("script payload did not get the descriptor field names");
        var authored = EngineCompat.hxcSongEventPayload(
            ["Stage Banner", Json.stringify({posX: 5}), "", ""],
            EngineCompat.eventSpriteDescriptorForName(catalog, "Stage Banner"));
        if (authored.eventData.value.posX != 5 || Reflect.hasField(authored.eventData.value, "posY"))
            fail("an object payload must be left as authored");
        var plain = EngineCompat.hxcSongEventPayload(["Stage Banner", "120", "64", ""]);
        if (Reflect.hasField(plain.eventData.value, "posX")) fail("no descriptor, no field names");
        ''')

    def test_rows_written_under_the_class_name_or_an_older_routed_name_still_match(self):
        self.run_fixture('''
        if (EngineCompat.routeEventSprite(catalog, "Banner Flash", "1", "2", "") == null)
            fail("spaced class name");
        if (EngineCompat.routeEventSprite(catalog, "BannerFlashEvent", "1", "2", "") == null)
            fail("class name");
        if (EngineCompat.routeEventSprite(catalog, "stage banner", "1", "2", "") == null)
            fail("case-insensitive id");
        var renamed = Reflect.copy(descriptor);
        renamed.canonicalName = "Older Routed Name";
        var older = [renamed];
        if (EngineCompat.routeEventSprite(older, "Older Routed Name", "1", "2", "") == null)
            fail("stored routed name");
        if (EngineCompat.routeEventSprite(older, "Stage Banner", "1", "2", "") == null)
            fail("event id against an older catalog");
        if (EngineCompat.routeEventSprite(catalog, "Some Other Event", "1", "2", "") != null)
            fail("unrelated event claimed");
        if (EngineCompat.routeEventSprite([], "Stage Banner", "1", "2", "") != null)
            fail("no descriptors, no route");
        var clash = Reflect.copy(descriptor);
        clash.framePrefix = "Different";
        if (EngineCompat.routeEventSprite([descriptor, clash], "Stage Banner", "1", "2", "") != null)
            fail("two different descriptors must stay ambiguous");
        ''')

    def test_importer_analysis_claims_the_event_through_the_descriptor(self):
        self.run_fixture('''
        var result = HxcCompat.analyze(source, "scripts/events/banner.hxc");
        if (result.kind != "song-event" || result.identifier != "Stage Banner") fail("identity");
        if (result.eventAdapters.length != 1 || result.eventAdapters[0].canonicalName != "Stage Banner")
            fail("descriptor adapter");
        for (finding in (cast result.diagnostics:Array<Dynamic>))
            if (finding.code == "unsupported-hxc-event-body" || finding.code == "hxc-event-body-gap")
                fail("descriptor body reported as a gap");
        if (EngineCompat.eventName("Stage Banner") != "Stage Banner") fail("fixed alias table used");
        if (EngineCompat.routeVSliceEvent("Stage Banner", {posX: 1, posY: 2}) != null)
            fail("fixed route table used");
        ''')

    def test_every_fixed_native_event_name_is_one_the_game_handles_itself(self):
        # The fixed list is only for events the game's own event switch runs.
        # A script-owned sprite event has no case there, so it can never be
        # put back on the list by name.
        compat = strip_comments((ROOT / "source/HxcCompat.hx").read_text(encoding="utf-8", errors="ignore"))
        native = compat[compat.index("static function isNativeEvent("):
            compat.index("static function lifecycleCallback(")]
        names = re.findall(r"'([^']+)'", native[native.index("switch (name)"):])
        self.assertGreater(len(names), 5)
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        for name in names:
            self.assertIn("'" + name + "'", play_state, name)
        # The alias table may only hand out names from that same switch or
        # leave the authored name alone, so a sprite event keeps its own id.
        self.run_fixture('''
        for (id in ["Stage Banner", "BannerFlashEvent", "Banner Flash", "bannerflash"])
            if (EngineCompat.eventName(id) != id) fail("alias table renamed " + id);
        ''')
        sprite = play_state[play_state.index("function spawnHxcEventSprite("):
            play_state.index("function disposeFinishedHxcEventSprites(")]
        self.assertIn("EngineCompat.routeEventSprite(hxcEventSpriteDescriptors(root)", sprite)


if __name__ == "__main__":
    unittest.main()
