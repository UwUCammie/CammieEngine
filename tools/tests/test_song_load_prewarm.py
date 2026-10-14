"""Song loading decodes a global script's images and uploads textures under the overlay."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"


def run_fixture(test, name, body):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
        work = Path(directory)
        (work / (name + ".hx")).write_text(body, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(FixturePath(SOURCE)), "-cp", str(FixturePath(work)),
             "--main", name, "--interp"],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def method_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise AssertionError("unterminated method " + signature)


class SongLoadPrewarmTest(unittest.TestCase):
    def test_only_fixed_sprite_image_names_are_found(self):
        run_fixture(self, "LiteralFixture", r'''
class LiteralFixture {
 static function fail(message:String):Void throw message;
 static function same(actual:Array<String>, expected:Array<String>, label:String):Void
  if (actual.join('|') != expected.join('|')) fail(label + ': got [' + actual.join(', ') + '] expected [' + expected.join(', ') + ']');
 static function main() {
  var lua = "
function onEndSong()
    makeLuaSprite('bg', '', -10, -10)
    makeLuaSprite('cpText', 'clearPercent/clearPercentText', 840, 285)
    makeAnimatedLuaSprite('cp1', \"clearPercent/numbers\", 765, 362)
    makeAnimatedLuaSprite('again', 'clearPercent/numbers', 1, 2)
    makeLuaSprite('diff', 'diff_'..string.lower(difficultyName), 550, 0)
    makeLuaSprite(tag, imageVariable, 0, 0)
    makeLuaSprite('letter'..i, 'resultsAlphabet', 670 + (i * 36), 5)
    makeAnimatedLuaSprite( 'spaced' ,  'spaced/image' )
    remakeLuaSprite('nope', 'notACall', 0, 0)
    makeLuaSprite('escaped', 'bad\\name', 0, 0)
    makeLuaSprite(getTag('a', 'b'), 'afterCall', 0, 0)
end";
  same(ScriptImageLiterals.spriteImages(lua),
   ['clearPercent/clearPercentText', 'clearPercent/numbers', 'resultsAlphabet', 'spaced/image', 'afterCall'],
   'lua literals');
  same(ScriptImageLiterals.spriteImages(lua, 2), ['clearPercent/clearPercentText', 'clearPercent/numbers'], 'limit');
  same(ScriptImageLiterals.spriteImages(null), [], 'null source');
  same(ScriptImageLiterals.spriteImages('makeLuaSprite(', 5), [], 'cut off call');
  same(ScriptImageLiterals.spriteImages("makeLuaSprite('a', 'b'"), [], 'unterminated call');

  // Only images of known, bounded size are decoded early, within one budget.
  var sizes = ['small' => 512 * 512, 'big' => 8192 * 8192, 'edge' => 2048 * 2048, 'missing' => -1,
   'second' => 2048 * 2048, 'third' => 2048 * 2048, 'fourth' => 2048 * 2048, 'tiny' => 16];
  same(ScriptImageLiterals.withinBudget(['small', 'big', 'missing', 'edge', 'second', 'third', 'fourth', 'tiny'],
   function(name) return sizes.get(name)), ['small', 'edge', 'second', 'third', 'tiny'], 'budget');
  var png = haxe.io.Bytes.alloc(24);
  png.set(0, 0x89); png.set(1, 'P'.code); png.set(2, 'N'.code); png.set(3, 'G'.code);
  png.set(18, 0x08); png.set(19, 0x00); png.set(22, 0x04); png.set(23, 0x9C);
  if (ScriptImageLiterals.pngPixels(png) != 2048 * 1180) fail('png size ' + ScriptImageLiterals.pngPixels(png));
  png.set(1, 'X'.code);
  if (ScriptImageLiterals.pngPixels(png) != -1) fail('a non png was given a size');
  if (ScriptImageLiterals.pngPixels(null) != -1 || ScriptImageLiterals.pngPixels(haxe.io.Bytes.alloc(10)) != -1)
   fail('a short header was given a size');
 }
}
''')

    def test_pixels_released_only_after_a_possible_upload(self):
        run_fixture(self, "ReleaseRuleFixture", r'''
class ReleaseRuleFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  if (!SongTexturePrewarm.canReleasePixels(true, true, true, true)) fail('decoded, readable, owner thread and context must release');
  if (SongTexturePrewarm.canReleasePixels(false, true, true, true)) fail('no pixels to release');
  if (SongTexturePrewarm.canReleasePixels(true, false, true, true)) fail('a graphic already made GPU-only was touched again');
  if (SongTexturePrewarm.canReleasePixels(true, true, false, true)) fail('released off the GL thread');
  if (SongTexturePrewarm.canReleasePixels(true, true, true, false)) fail('released without a context to upload into');
 }
}
''')

    def test_gpu_only_retention_restores_pixels_when_the_upload_fails(self):
        assets = (SOURCE / "FNFAssets.hx").read_text(encoding="utf-8")
        body = method_body(assets, "public static function retainForSongOnGpu(graphic:FlxGraphic):Bool")
        # Held for the song like retainForSong, before anything else can return.
        self.assertLess(body.index("SongGraphicRetention.hold(graphic.key, graphic, pathEpoch(), true);"), body.index("#if !flash"))
        # disposeImage first, so OpenFL's own upload drops the pixels.
        self.assertLess(body.index("bitmap.disposeImage();"), body.index("bitmap.getTexture(stage.context3D)"))
        after = body[body.index("bitmap.getTexture(stage.context3D)"):]
        self.assertIn("if (bitmap.image != null) {", after)
        self.assertIn("@:privateAccess bitmap.readable = true;", after)
        # Without the rule's conditions it behaves exactly like retainForSong.
        fallback = body[body.index("SongTexturePrewarm.canReleasePixels("):body.index("bitmap.disposeImage();")]
        self.assertIn("uploadTexture(bitmap);", fallback)

    def test_load_flow_runs_the_prewarm_before_play(self):
        loading = (SOURCE / "SongLoadingScreen.hx").read_text(encoding="utf-8")
        handoff = loading.split("if (progress.completed == 3) {", 1)[1].split("}", 1)[0]
        self.assertLess(handoff.index("EngineMemory.collectNow"), handoff.index("complete(4"))
        # A bulk upload of every cached texture here made the first render and
        # the first frame after the music starts about twice as slow.
        self.assertNotIn("uploadSongTextures", loading)
        self.assertNotIn("uploadSongTextures", (SOURCE / "FNFAssets.hx").read_text(encoding="utf-8"))

        play = (SOURCE / "PlayState.hx").read_text(encoding="utf-8")
        create = method_body(play, "override public function create()")
        self.assertLess(create.index("precacheGlobalProviderImages();"), create.index("markLoadPhase('stage_loaded')"))
        body = method_body(play, "function precacheGlobalProviderImages():Void")
        self.assertLess(body.index("lowMemoryMode"), body.index("defaultProvider()"))
        self.assertIn("entry.scope != PsychScriptDiscovery.GLOBAL", body)
        # The same owner-checked precache as a script's own precacheImage call.
        self.assertIn("ScriptImageLiterals.spriteImages(source)", body)
        self.assertIn("ScriptImageLiterals.withinBudget(names", body)
        self.assertIn("ScriptImageLiterals.pngPixels(header)", body)
        # Owner-checked like a script's precacheImage, held on the GPU only.
        self.assertIn("compatPrecacheImageForOwner(owner, image, true, true)", body)
        precache = method_body(play, "function compatPrecacheImageForOwner(")
        self.assertIn("gpuOnly && Std.isOfType(graphic, flixel.graphics.FlxGraphic))\n\t\t\tFNFAssets.retainForSongOnGpu(graphic);", precache)
        # A script's own precacheImage keeps its pixels.
        self.assertIn("FNFAssets.retainForSong(graphic, allowGPU != false);", precache)
        self.assertIn("gpuOnly:Bool = false", play.split("function compatPrecacheImageForOwner(", 1)[1].split("{", 1)[0])
        self.assertIsNone(re.search(r"results|vslice", body, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
