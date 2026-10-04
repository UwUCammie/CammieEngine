"""Regression coverage for the opt-in native note framebuffer probe."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "source" / "RuntimeSmokeHarness.hx"


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
    raise AssertionError(f"unterminated Haxe method: {marker}")


class RuntimeNoteRenderReadbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HARNESS.read_text(encoding="utf-8")

    def test_framebuffer_capture_is_explicit_and_waits_for_live_note_rendering(self):
        source = self.source
        self.assertIn("noteRenderReadback: false", source)
        self.assertIn("case '--smoke-note-render-readback'", source)
        self.assertIn("noteRenderAfterMs: 5000", source)
        self.assertIn("case '--smoke-note-render-after-ms'", source)
        self.assertIn("case '--smoke-note-render-path'", source)

        install = extract_method(source, "static function installNoteRenderReadback(")
        self.assertIn("window.onRender.add(onNoteRenderReadbackRendered, false, -1000)", install)
        callback = extract_method(source, "static function onNoteRenderReadbackRendered(")
        self.assertIn("noteRenderReadbackVisits.exists(visitsStarted)", callback)
        self.assertIn("!songStartObserved", callback)
        self.assertIn("Conductor.songPosition < config().noteRenderAfterMs", callback)
        self.assertIn("!note.visible", callback)
        self.assertIn("!note.isOnScreen()", callback)
        self.assertIn("note.isSustainNote", callback)

        capture = extract_method(source, "static function captureNoteRenderReadback(")
        self.assertIn("window.readPixels()", capture)
        self.assertIn("image.encode()", capture)
        self.assertIn("File.saveBytes(outputPath, encoded)", capture)
        self.assertIn("emit('note_render_readback'", capture)
        self.assertIn("noteRenderPathForVisit(config().noteRenderPath", capture)

        path_method = extract_method(source, "static function noteRenderPathForVisit(")
        fixture = """import haxe.io.Path;
class ReadbackPathTest {
  METHOD
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function main() {
    check(noteRenderPathForVisit('baseline.png', 1, 1) == 'baseline.png',
      'single visit path changed');
    check(noteRenderPathForVisit('tmp/baseline.png', 1, 2) == 'tmp/baseline.visit-1.png',
      'first visit path was not isolated');
    check(noteRenderPathForVisit('tmp/baseline.png', 2, 2) == 'tmp/baseline.visit-2.png',
      'second visit path was not isolated');
    check(noteRenderPathForVisit('tmp/baseline', 2, 2) == 'tmp/baseline.visit-2',
      'extensionless path was not isolated');
  }
}
""".replace("METHOD", path_method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "ReadbackPathTest.hx"
            source_path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "ReadbackPathTest"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_intro_capture_observes_a_held_countdown_without_releasing_it(self):
        callback = extract_method(self.source, "static function onNoteRenderReadbackRendered(")
        self.assertIn("!songStartObserved", callback)
        self.assertIn(".startedCountdown", callback)
        self.assertIn("nowMs() - introRenderHeldAt >= 5000", callback)
        self.assertIn("captureIntroRenderReadback", callback)
        capture = extract_method(self.source, "static function captureIntroRenderReadback(")
        self.assertIn("window.readPixels()", capture)
        self.assertIn("'.intro.png'", capture)
        self.assertIn("muted: FlxG.sound.muted", capture)
        self.assertNotIn("startCountdown()", capture)
        self.assertNotIn("animation.play", capture)
        self.assertNotIn("songPosition =", capture)

    def test_shader_uniform_diagnostic_reports_palette_and_actual_bindings(self):
        methods = "\n\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function noteRenderShaderDiagnostic(",
                "static function noteRenderShaderParameter(",
            )
        )
        fixture = """class ReadbackUniform {
  public var name:String;
  public var index:Dynamic;
  public var value:Dynamic;
  public function new(name:String, index:Int, value:Dynamic) {
    this.name = name; this.index = index; this.value = value;
  }
}
class ReadbackShader {
  public var r:ReadbackUniform;
  public var g:ReadbackUniform;
  public var b:ReadbackUniform;
  public var mult:ReadbackUniform;
  public var u_alpha:ReadbackUniform;
  public var u_flash:ReadbackUniform;
  public var glProgram:Dynamic = {};
  public var data:Dynamic;
  public function new() {
    r = new ReadbackUniform('r', 1, [0.1, 0.2, 0.3]);
    g = new ReadbackUniform('g', 2, [0.4, 0.5, 0.6]);
    b = new ReadbackUniform('b', 3, [0.7, 0.8, 0.9]);
    mult = new ReadbackUniform('mult', 4, [1.0]);
    u_alpha = new ReadbackUniform('u_alpha', 5, [0.75]);
    u_flash = new ReadbackUniform('u_flash', 6, [0.0]);
    data = {bitmap: {name:'bitmap', index:0}};
  }
}
class ReadbackPalette {
  public var shader:ReadbackShader;
  public var r:Int = 0xFFC24B99;
  public var g:Int = 0xFFFFFFFF;
  public var b:Int = 0xFF3C1F56;
  public var mult:Float = 1.0;
  public function new(shader:ReadbackShader) this.shader = shader;
}
class ReadbackReference {
  public var parent:ReadbackPalette;
  public var enabled:Bool = true;
  public function new(parent:ReadbackPalette) this.parent = parent;
}
class ReadbackNightmareVisionRGB {
  public var palette:ReadbackPalette;
  public var enabled:Bool = true;
  public var alpha:Float = 0.8;
  public var flash:Float = 0.25;
  public function new(palette:ReadbackPalette) this.palette = palette;
}
class Note {
  public var rgbShader:ReadbackReference;
  public var nightmareVisionRGB:ReadbackNightmareVisionRGB;
  public var shader:Dynamic;
  public function new(shader:Dynamic, reference:ReadbackReference,
      nightmareVision:ReadbackNightmareVisionRGB) {
    this.shader = shader;
    rgbShader = reference;
    nightmareVisionRGB = nightmareVision;
  }
}
class ReadbackDiagnosticTest {
  METHODS
  static function check(ok:Bool, message:String):Void
    if (!ok) throw message;
  static function main() {
    var shader = new ReadbackShader();
    var palette = new ReadbackPalette(shader);
    var note = new Note(shader, null, new ReadbackNightmareVisionRGB(palette));
    var result = noteRenderShaderDiagnostic(note);
    var uniforms:Dynamic = Reflect.field(result, 'uniforms');
    var red:Array<Float> = cast Reflect.field(Reflect.field(uniforms, 'r'), 'value');
    var alpha:Array<Float> = cast Reflect.field(Reflect.field(uniforms, 'u_alpha'), 'value');
    check(Reflect.field(result, 'bound') == true, 'live shader binding was omitted');
    check(Reflect.field(result, 'shaderClass') == 'ReadbackShader', 'shader class was omitted');
    check(Reflect.field(result, 'programReady') == true, 'GL program readiness was omitted');
    check(Reflect.field(Reflect.field(result, 'bitmapInput'), 'index') == 0,
      'bitmap sampler location was omitted');
    check(red.length == 3 && red[0] == 0.1 && red[2] == 0.3,
      'RGB uniform values were not copied into the diagnostic');
    check(Reflect.field(Reflect.field(uniforms, 'r'), 'index') == 1,
      'RGB uniform location was omitted');
    check(alpha.length == 1 && alpha[0] == 0.75, 'alpha uniform was not reported');
    check(Reflect.field(Reflect.field(result, 'palette'), 'mult') == 1.0,
      'palette multiplier was not reported');
    check(Reflect.field(Reflect.field(result, 'nightmareVision'), 'alpha') == 0.8
      && Reflect.field(Reflect.field(result, 'nightmareVision'), 'flash') == 0.25,
      'NMV per-note visual state was not reported');
    note.nightmareVisionRGB = null;
    note.rgbShader = new ReadbackReference(palette);
    result = noteRenderShaderDiagnostic(note);
    check(Reflect.field(result, 'referenceEnabled') == true,
      'Psych reference-enabled state was not reported');
    note.shader = null;
    result = noteRenderShaderDiagnostic(note);
    check(Reflect.field(result, 'bound') == false, 'missing shader binding was misreported');
    check(Reflect.field(result, 'uniforms') == null, 'missing binding exposed stale uniforms');
  }
}
""".replace("METHODS", methods)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "ReadbackDiagnosticTest.hx"
            source_path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "ReadbackDiagnosticTest"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_frame_graphic_diagnostic_reports_cache_liveness(self):
        method = extract_method(self.source, "static function noteRenderGraphicDiagnostic(")
        fixture = """class ReadbackBitmap { public var width:Int; public var height:Int;
  public function new(width:Int,height:Int){this.width=width;this.height=height;} }
class ReadbackGraphic { public var key:String; public var isDestroyed:Bool=false;
  public var isLoaded:Bool=true; public var useCount:Int; public var bitmap:ReadbackBitmap;
  public function new(key:String,useCount:Int,bitmap:ReadbackBitmap){this.key=key;this.useCount=useCount;this.bitmap=bitmap;} }
class ReadbackFrames { public var parent:ReadbackGraphic; public function new(parent:ReadbackGraphic)this.parent=parent; }
class Note { public var frames:ReadbackFrames; public var psychSkinUsesNativeDefaultFallback:Bool=false;
  public function new(frames:ReadbackFrames)this.frames=frames; }
class ReadbackGraphicDiagnosticTest {
  METHOD
  static function check(ok:Bool,message:String):Void if(!ok)throw message;
  static function main() {
    var graphic=new ReadbackGraphic('fnfassets:disk-bitmap:/owner/NOTE_assets.png',3,new ReadbackBitmap(1023,1069));
    var result=noteRenderGraphicDiagnostic(new Note(new ReadbackFrames(graphic)));
    var bitmap:Dynamic=Reflect.field(result,'bitmap');
    check(Reflect.field(result,'framesPresent')==true && Reflect.field(result,'isDestroyed')==false,
      'live frame parent was not reported');
    check(Reflect.field(result,'key')=='fnfassets:disk-bitmap:/owner/NOTE_assets.png'
      && Reflect.field(result,'useCount')==3,'cache key or use count was omitted');
    check(Reflect.field(result,'nativeDefaultFallback')==false,
      'Psych native-fallback classification was omitted');
    check(Reflect.field(bitmap,'width')==1023 && Reflect.field(bitmap,'height')==1069,
      'bitmap dimensions were omitted');
    graphic.isDestroyed=true; graphic.bitmap=null;
    result=noteRenderGraphicDiagnostic(new Note(new ReadbackFrames(graphic)));
    check(Reflect.field(result,'isDestroyed')==true && Reflect.field(result,'bitmap')==null,
      'destroyed cached graphics were not distinguishable');
  }
}
""".replace("METHOD", method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "ReadbackGraphicDiagnosticTest.hx"
            source_path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "ReadbackGraphicDiagnosticTest"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
