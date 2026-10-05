"""Execute the real Psych skin reload and sprite texture methods with small Flixel doubles."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    match = re.search(r'\bfunction\s+' + re.escape(name) + r'\s*\(', source)
    if not match:
        raise AssertionError(f'missing {name}')
    start = source.rfind('\n', 0, match.start()) + 1
    brace = source.index('{', match.end())
    semicolon = source.find(';', match.end())
    if semicolon < brace:
        return source[start:semicolon + 1]
    depth = 0
    for at in range(brace, len(source)):
        if source[at] == '{':
            depth += 1
        elif source[at] == '}':
            depth -= 1
            if depth == 0:
                return source[start:at + 1]
    raise AssertionError(f'unclosed {name}')


class PsychSkinRuntimeTest(unittest.TestCase):
    def test_real_reload_and_texture_setters(self):
        shader_source = (ROOT / 'source/PsychRGBShader.hx').read_text()
        shader_constructor = method(shader_source, 'new')
        self.assertNotIn('setPalette(', shader_constructor,
                         'native uniforms are initialized after the constructor returns')
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            for name in ('PsychSkinRuntime.hx', 'PsychSkinResolver.hx', 'NoteTypeCompat.hx', 'NoteOffsetState.hx'):
                shutil.copyfile(ROOT / 'source' / name, work / name)
            flixel = work / 'flixel/graphics/frames'
            flixel.mkdir(parents=True)
            (flixel / 'FlxAtlasFrames.hx').write_text('''package flixel.graphics.frames;
class FlxAtlasFrames {
  public var frames:Array<{name:String}> = [];
  public function new(names:Array<String>) for (name in names) frames.push({name:name});
}''', newline='\n')
            (work / 'DynamicSprite.hx').write_text('''class DynamicSprite {}
class DynamicAtlasFrames {
  public static function fromSparrow(image:String, xml:String):flixel.graphics.frames.FlxAtlasFrames {
    var text = sys.io.File.getContent(xml);
    var names = [];
    var pattern = ~/name="([^"]+)"/g;
    while (pattern.match(text)) {
      names.push(pattern.matched(1));
      text = pattern.matchedRight();
    }
    return new flixel.graphics.frames.FlxAtlasFrames(names);
  }
}''', newline='\n')
            (work / 'Sprite.hx').write_text('''class Sprite {
  public var animation = new Anim();
  public var scale = new Point(1, 1);
  public var offset = new Point(3, 4);
  public var width:Float = 10;
  public var antialiasing:Bool = true;
  public var shader:Dynamic;
  public var frames:flixel.graphics.frames.FlxAtlasFrames;
  public var hitboxScaleY:Float = 0;
  public var originCentered:Bool=false;
  public function new() {}
  public function loadGraphic(bitmap:Bitmap, animated:Bool, w:Int, h:Int):Void {width = w;}
  public function setGraphicSize(size:Int):Void {scale.x = size / width; scale.y = scale.x;}
  public function updateHitbox():Void {hitboxScaleY = scale.y; centerOffsets();}
  public function centerOffsets():Void offset.set(5, 5);
  public function centerOrigin():Void originCentered=true;
}
class Point {
  public var x:Float; public var y:Float;
  public function new(x:Float, y:Float) {this.x=x; this.y=y;}
  public function set(x:Float, y:Float):Void {this.x=x; this.y=y;}
}
class Anim {
  public var curAnim:{name:String};
  var names = new Map<String, Bool>();
  public function new() {}
  public function add(name:String, frames:Array<Int>, fps:Float=24, loop:Bool=true):Void names.set(name,true);
  public function addByPrefix(name:String, prefix:String, fps:Float=24, loop:Bool=true):Void names.set(name,true);
  public function exists(name:String):Bool return names.exists(name);
  public function play(name:String, force:Bool=false, reversed:Bool=false, frame:Int=0):Void curAnim={name:name};
}
class Bitmap {
  public var width:Int; public var height:Int;
  public function new(width:Int, height:Int) {this.width=width; this.height=height;}
}''', newline='\n')
            (work / 'FNFAssets.hx').write_text('''import Sprite.Bitmap;
class FNFAssets {
  public static function getBitmapData(path:String):Bitmap
    return new Bitmap(40, StringTools.endsWith(path, "ENDS.png") ? 20 : 50);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}''', newline='\n')
            (work / 'PlayState.hx').write_text('class PlayState {public static var daPixelZoom:Float = 6;}', newline='\n')
            (work / 'RuntimeSmokeHarness.hx').write_text('''class RuntimeSmokeHarness {
  public static var phase:String='';
  public static var steps:Array<String>=[];
  public static function enabled():Bool return true;
  public static function setPsychSkinDiagnosticPhase(value:String):Void phase=value;
  public static function markStep(value:String):Void steps.push(value);
}''', newline='\n')
            (work / 'PsychRGBShader.hx').write_text('''class PsychRGBShader {
  public var hurt:Bool = false;
  public var lane:Int=-1; public var pixel:Bool=false; public var paletteCalls:Int=0;
  public function new() {}
}''', newline='\n')
            (work / 'PsychRGBPalette.hx').write_text('''class PsychRGBPalette {
  static var cached:Map<String,PsychRGBPalette>=new Map();
  public var shader:PsychRGBShader;
  public function new(lane:Int,pixel:Bool,hurt:Bool=false) {
    shader=new PsychRGBShader(); shader.lane=lane; shader.pixel=pixel;
    shader.hurt=hurt; shader.paletteCalls++;
  }
  public static function defaultFor(lane:Int,pixel:Bool,hurt:Bool=false):PsychRGBPalette
  {
    var key=lane+':'+pixel+':'+hurt;
    if(!cached.exists(key)) cached.set(key,new PsychRGBPalette(lane,pixel,hurt));
    return cached.get(key);
  }
}''', newline='\n')
            (work / 'PsychRGBShaderReference.hx').write_text('''class PsychRGBShaderReference {
  public var parent:PsychRGBPalette;
  public var enabled(default,set):Bool=true;
  public var hasCustomPalette:Bool=false;
  public var explicitlyEnabled:Bool=false;
  var owner:Sprite;
  public function new(owner:Sprite,palette:PsychRGBPalette) {
    this.owner=owner; parent=palette; owner.shader=palette.shader;
  }
  public function usePalette(palette:PsychRGBPalette):Void {
    if (palette != parent) { parent=palette; hasCustomPalette=false; if (enabled) owner.shader=palette.shader; }
  }
  function set_enabled(value:Bool):Bool {explicitlyEnabled=value;owner.shader=value?parent.shader:null;return enabled=value;}
  public function tune():Void {hasCustomPalette=true;if(enabled)owner.shader=parent.shader;}
}''', newline='\n')
            note_source = (ROOT / 'source/Note.hx').read_text()
            self.assertRegex(note_source, r"else if \(Reflect.field\(thingie, 'sourceNoteType'\) != null\)[\s\S]*?sourceKind = Std.string\(Reflect.field\(thingie, 'sourceNoteType'\)\)")
            strum_source = (ROOT / 'source/Strumline.hx').read_text()
            note_methods = '\n'.join(method(note_source, name) for name in (
                'get_texture', 'set_texture', 'configurePsychSkin', 'refreshPsychNoteType', 'resetPsychVisualOffset',
                'set_sourceKind', 'applyPsychNoteAnimationType', 'get_rgbShader'))
            strum_methods = '\n'.join(method(strum_source, name) for name in (
                'get_texture', 'set_texture', 'configurePsychRGBShader', 'set_useRGBShader',
                'configurePsychSkin', 'refreshPsychRGB', 'playAnim', 'get_rgbShader',
                'hasNightmareVisionRGB', 'getNightmareVisionRGB'))
            (work / 'Note.hx').write_text('''class Note extends Sprite {
  public var texture(get,set):String;
  var psychTexture:String=''; var psychSkinOwner:String=null; var psychChartSkin:String=null;
  var psychPixelSkin:Bool=false; var psychSkinPostfix:String='';
  var psychRGBDisabled:Bool=false; var psychRGBShader:PsychRGBShaderReference=null;
  public var psychSkinUsesNativeDefaultFallback:Bool=false;
  public var rgbShader(get,never):PsychRGBShaderReference;
  var psychSkinDiagnosticNoteIndex:Int=0;
  var psychSkinDiagnosticsEnabled:Bool=false;
  var offsetState:NoteOffsetState=new NoteOffsetState();
  public var sourceKind(default,set):Null<String>=null;
  public var sourceTimingMode:Int=0;
  public var hitPriority:Int=1;
  public var noAnimation:Bool=false; public var noMissAnimation:Bool=false;
  public var noteData:Int=0; public var isSustainNote:Bool=false;
  public var strumTime:Float=123; public var mineNote:Bool=false;
  function applySourceHurtNoteSemantics():Void {}
  public function new(sustain:Bool=false) {super(); isSustainNote=sustain;}
''' + note_methods + '\n}', newline='\n')
            (work / 'NightmareVisionRGBGraphics.hx').write_text('class NightmareVisionRGBGraphics {public function new(palette:Dynamic) {}}', newline='\n')
            (work / 'Strumline.hx').write_text('''class Strumline {public var noAnims:Bool=false; public function new() {}}
class StrumNote extends Sprite {
  public var nightmareVisionSource:Bool=false;
  public var nightmareVisionRGB:NightmareVisionRGBGraphics=null;
  public var nightmareVisionOffsets:Map<String,Array<Float>>=null;
  public var nightmareVisionPalette:Dynamic=null;
  public var texture(get,set):String;
  var psychTexture:String=''; var psychSkinOwner:String=null; var psychChartSkin:String=null;
  var psychPixelSkin:Bool=false; var psychSkinPostfix:String='';
  var psychRGBDisabled:Bool=false; var psychRGBShader:PsychRGBShaderReference=null;
  public var psychSkinUsesNativeDefaultFallback:Bool=false;
  var psychSkinConfigured:Bool=false; var psychRGBExplicitlyEnabled:Bool=false;
  public var rgbShader(get,never):Dynamic;
  public var useRGBShader(default,set):Bool=true;
  public var confirmationGeneration:Int=0;
  public var ID:Int=0; public var isPixel:Bool=false; public var normalSize:Float=1;
  var usesVSliceGeometry:Bool=false; public var parentLine:Strumline=null;
  public function alignVSliceFrame():Void {}
  public function markReceptorVisual():Void {}
  public function new() {super();}
''' + strum_methods + '\n}', newline='\n')
            owner = work / 'assets/imported_mods/one/images'
            owner.mkdir(parents=True)
            for key in ('Later', 'Receptor', 'Receptor2'):
                (owner / (key + '.png')).write_bytes(b'png')
            (owner / 'Later.xml').write_text('<TextureAtlas><SubTexture name="purple0"/><SubTexture name="purple hold piece"/><SubTexture name="purple hold end"/><SubTexture name="red0"/><SubTexture name="red hold piece"/><SubTexture name="red hold end"/></TextureAtlas>', newline='\n')
            for key in ('Receptor', 'Receptor2'):
                (owner / (key + '.xml')).write_text('<TextureAtlas><SubTexture name="arrowLEFT"/><SubTexture name="left press"/><SubTexture name="left confirm"/></TextureAtlas>', newline='\n')
            native_skin = work / 'assets/images/custom_ui/ui_packs/normal'
            native_skin.mkdir(parents=True)
            (native_skin / 'NOTE_assets.png').write_bytes(b'png')
            (native_skin / 'NOTE_assets.xml').write_text(
                '<TextureAtlas><SubTexture name="purple0"/><SubTexture name="blue0"/><SubTexture name="green0"/><SubTexture name="red0"/><SubTexture name="purple hold piece"/><SubTexture name="blue hold piece"/><SubTexture name="green hold piece"/><SubTexture name="red hold piece"/><SubTexture name="purple hold end"/><SubTexture name="blue hold end"/><SubTexture name="green hold end"/><SubTexture name="red hold end"/><SubTexture name="arrowLEFT"/><SubTexture name="arrowDOWN"/><SubTexture name="arrowUP"/><SubTexture name="arrowRIGHT"/><SubTexture name="left press"/><SubTexture name="left confirm"/><SubTexture name="down press"/><SubTexture name="down confirm"/><SubTexture name="up press"/><SubTexture name="up confirm"/><SubTexture name="right press"/><SubTexture name="right confirm"/></TextureAtlas>', newline='\n')
            (work / 'Probe.hx').write_text('''class Probe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function main():Void {
    var owner='assets/imported_mods/one';
    var definitions:Array<Dynamic>=[];
    check(NoteTypeCompat.ensureDefinition('hurt',definitions) == 0 &&
      Reflect.field(definitions[0], 'sourceNoteType') == 'Hurt Note', 'generated Hurt type');
    var note=new Note(); note.noteData=3; note.sourceKind='Hurt Note';
    note.offset.set(24, 24);
    check(!note.configurePsychSkin(owner,'Missing',false,false), 'missing default');
    check(note.texture == '', 'failed default readback');
    note.texture='Later';
    check(note.texture == 'Later' && note.animation.curAnim.name == 'Scroll', 'retry texture');
    check(note.strumTime == 123 && note.sourceKind == 'Hurt Note' && note.hitPriority == 0
      && note.shader.hurt, 'type, priority, and timing');
    check(note.shader.lane == 3 && !note.shader.pixel && note.shader.paletteCalls > 0,
      'note palette must be applied after shader construction');
    check(note.offset.x == 5 && note.originCentered, 'note skin recenters relative to receptor');
    note.texture='Missing'; check(note.texture == 'Later', 'failed write rollback');
    RuntimeSmokeHarness.steps=[];
    var sampled=new Note(); sampled.noteData=0;
    check(sampled.configurePsychSkin(owner,'Later',false,false,'',7,true), 'sampled skin configure');
    var trace=RuntimeSmokeHarness.steps.join('|');
    var reloadBegin=trace.indexOf('psych-note-skin:reload-begin count=7');
    var reloadComplete=trace.indexOf('psych-note-skin:reload-complete count=7');
    var rgbBegin=trace.indexOf('psych-note-skin:rgb-refresh-begin count=7');
    var paletteBegin=trace.indexOf('psych-note-skin:rgb-palette-begin count=7');
    var paletteComplete=trace.indexOf('psych-note-skin:rgb-palette-complete count=7');
    var rgbComplete=trace.indexOf('psych-note-skin:rgb-refresh-complete count=7');
    check(reloadBegin >= 0 && reloadComplete > reloadBegin && rgbBegin > reloadComplete
      && paletteBegin > rgbBegin && paletteComplete > paletteBegin && rgbComplete > paletteComplete,
      'sampled skin and RGB marker order');
    check(RuntimeSmokeHarness.phase == 'configure:complete', 'successful skin phase reset');
    var legacy=new Note();
    check(legacy.configurePsychSkin(owner,'noteSkins/NOTE_assets',false,false),
      'legacy chart should resolve the native base atlas');
    check(legacy.psychSkinUsesNativeDefaultFallback && legacy.shader == null,
      'precolored native fallback must skip Psych RGB recoloring');
    legacy.rgbShader.tune(); legacy.refreshPsychNoteType();
    check(legacy.shader != null,
      'an authored Psych RGB palette edit must remain active on the native fallback');
    legacy.rgbShader.enabled=false;
    check(legacy.shader == null, 'an explicit RGB disable must still work on the native fallback');
    legacy.rgbShader.enabled=true; legacy.refreshPsychNoteType();
    check(legacy.shader != null, 'an explicit RGB enable must still work on the native fallback');
    legacy.texture='Later';
    check(!legacy.psychSkinUsesNativeDefaultFallback && legacy.shader != null,
      'explicit selected-owner skin must retain Psych RGB');
    var legacyStrum=new Strumline.StrumNote();
    check(legacyStrum.configurePsychSkin(owner,'noteSkins/NOTE_assets',false,false),
      'legacy receptor should resolve the native base atlas');
    legacyStrum.playAnim('confirm');
    check(legacyStrum.psychSkinUsesNativeDefaultFallback && legacyStrum.shader == null,
      'precolored native receptor fallback must skip Psych RGB recoloring');
    legacyStrum.useRGBShader=false; legacyStrum.useRGBShader=true;
    check(legacyStrum.shader != null,
      'an explicit receptor RGB enable must still work on the native fallback');
    legacyStrum.texture='Receptor'; legacyStrum.playAnim('confirm');
    check(!legacyStrum.psychSkinUsesNativeDefaultFallback && legacyStrum.shader != null,
      'explicit selected-owner receptor skin must retain Psych RGB');
    var hold=new Note(true); hold.scale.y=9; hold.animation.play('hold');
    hold.offset.set(24, 24);
    check(hold.configurePsychSkin(owner,'Later',true,false), 'hold configure');
    check(hold.scale.y == 9 && hold.hitboxScaleY == 9, 'hold scale and hitbox');
    check(hold.offset.x == 5, 'sustain horizontal geometry recentered');
    check(hold.animation.curAnim.name == 'hold' && hold.shader == null, 'hold anim and rgb disable');
    var strum=new Strumline.StrumNote();
    check(!strum.configurePsychSkin(owner,'Missing',false,false), 'strum missing default');
    strum.texture='Receptor'; check(strum.texture == 'Receptor', 'strum retry');
    strum.playAnim('confirm'); check(strum.shader != null, 'confirm rgb');
    check(strum.shader.lane == strum.ID && !strum.shader.pixel && strum.shader.paletteCalls > 0,
      'receptor palette must be applied after shader construction');
    check(strum.offset.x == 5 && strum.originCentered, 'Psych confirm offsets and origin');
    strum.useRGBShader=false; check(strum.shader == null, 'live rgb disable');
    strum.useRGBShader=true; check(strum.shader != null, 'live rgb enable');
    strum.texture='Missing'; check(strum.texture == 'Receptor', 'strum failed write rollback');
    var disabled=new Strumline.StrumNote();
    check(disabled.configurePsychSkin(owner,'Receptor',true,false), 'disabled configure');
    disabled.playAnim('confirm'); check(disabled.shader == null, 'chart rgb disabled');
    disabled.useRGBShader=true; check(disabled.shader != null, 'explicit rgb enable');
    disabled.texture='Receptor2';
    check(disabled.texture == 'Receptor2' && disabled.useRGBShader && disabled.shader != null,
      'texture swap preserves explicit rgb enable');
  }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work),
                                     '-main', 'Probe', '--interp'], cwd=work, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
