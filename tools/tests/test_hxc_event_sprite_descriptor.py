from haxe_test_support import HAXE_COMMAND
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
MOUNTED_EVENT = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/"
    "TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/EyePopup.hxc"
)


class HxcEventSpriteDescriptorTest(unittest.TestCase):
    def compile_descriptor_assertions(self, source, assertions):
        fixture = f'''import HxcEventSpriteDescriptor;
class HxcEventSpriteDescriptorTest {{
    static function fail(message:String):Void throw message;
    static function main() {{
        var source = {json.dumps(source)};
        {assertions}
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "HxcEventSpriteDescriptorTest.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-main", "HxcEventSpriteDescriptorTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_synthetic_static_event_extracts_and_serializes_only_valid_metadata(self):
        source = '''
class OverlayCueEvent extends ScriptedSongEvent {
    function new() super("OverlayCue");
    function handleEvent(data) {
        var cueX = data.value.x;
        var cueY = data.value.y;
        var cue = new FlxSprite(cueX, cueY);
        cue.frames = Paths.getSparrowAtlas("ui/overlay");
        cue.animation.addByPrefix("pulse", "Overlay Pulse", 18, false);
        cue.animation.play("pulse");
        cue.scrollFactor.set(0, 0);
        cue.cameras = [PlayState.instance.camHUD];
        cue.animation.finishCallback = function(s:String) {
            PlayState.instance.remove(cue);
            cue.kill();
        };
    }
}
'''
        assertions = '''
        var descriptor = HxcEventSpriteDescriptor.extract(source);
        if (descriptor == null || descriptor.sourceName != "OverlayCue"
            || descriptor.atlasKey != "ui/overlay" || descriptor.atlasType != "sparrow"
            || descriptor.animationName != "pulse" || descriptor.framePrefix != "Overlay Pulse"
            || descriptor.frameRate != 18 || descriptor.loop != false
            || descriptor.xField != "x" || descriptor.yField != "y"
            || descriptor.camera != "hud" || descriptor.scrollX != 0 || descriptor.scrollY != 0)
            fail("static event descriptor fields");
        var encoded = HxcEventSpriteDescriptor.serializeCatalog([descriptor, descriptor]);
        var catalog = HxcEventSpriteDescriptor.parseCatalog(encoded);
        if (catalog.length != 1 || HxcEventSpriteDescriptor.find(catalog, "overlaycue") == null)
            fail("descriptor catalog round trip");
        var unsafe = HxcEventSpriteDescriptor.normalize({version: 1, className: "Bad",
            sourceName: "Bad", canonicalName: "Bad", atlasKey: "../outside",
            atlasType: "sparrow", animationName: "idle", framePrefix: "Idle",
            frameRate: 24, loop: false, xField: "x", yField: "y", camera: "hud",
            scrollX: 0, scrollY: 0, cleanupOnFinish: true});
        if (unsafe != null) fail("unsafe atlas traversal accepted");
        var conflict = Reflect.copy(descriptor);
        conflict.framePrefix = "Different";
        var conflictedCatalog = HxcEventSpriteDescriptor.parseCatalog(
            HxcEventSpriteDescriptor.serializeCatalog([descriptor, conflict]));
        if (HxcEventSpriteDescriptor.find(conflictedCatalog, "OverlayCue") != null)
            fail("conflicting event descriptors must be ambiguous");
'''
        self.compile_descriptor_assertions(source, assertions)

    def test_dynamic_or_ambiguous_source_is_not_translated(self):
        source = '''
class DynamicEvent extends ScriptedSongEvent {
    function new() super("DynamicOverlay");
    function handleEvent(data) {
        var x = data.value.x;
        var y = data.value.y;
        var overlay = new FlxSprite(x, y);
        overlay.frames = Paths.getSparrowAtlas(data.value.atlas);
        overlay.animation.addByPrefix("idle", "Idle", 24, false);
        overlay.animation.play("idle");
        overlay.cameras = [PlayState.instance.camHUD];
        overlay.animation.finishCallback = function(_) { PlayState.instance.remove(overlay); overlay.kill(); };
    }
}
'''
        self.compile_descriptor_assertions(
            source,
            'if (HxcEventSpriteDescriptor.extract(source) != null) fail("dynamic path accepted");',
        )

    @unittest.skipUnless(MOUNTED_EVENT.is_file(), "mounted V-Slice donor event is unavailable")
    def test_mounted_event_source_is_read_only_and_extracts_to_data(self):
        before = MOUNTED_EVENT.read_bytes()
        source = before.decode("utf-8")
        assertions = '''
        var descriptor = HxcEventSpriteDescriptor.extract(source);
        if (descriptor == null || descriptor.sourceName != "EyePopup"
            || descriptor.atlasKey != "MarkovEyes" || descriptor.framePrefix != "MarkovWindow"
            || descriptor.xField != "x" || descriptor.yField != "y")
            fail("mounted donor event static metadata extraction");
'''
        self.compile_descriptor_assertions(source, assertions)
        self.assertEqual(MOUNTED_EVENT.read_bytes(), before, "the mounted donor source must remain untouched")


if __name__ == "__main__":
    unittest.main()
