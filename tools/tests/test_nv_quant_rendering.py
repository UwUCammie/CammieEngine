"""Execute production quant rendering and source receptor color selection."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_nightmare_vision_note_skin_runtime import STUBS
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvQuantRenderingTest(unittest.TestCase):
    def test_note_flags_colors_sustain_inheritance_and_receptor_pressed_colors(self):
        stubs = dict(STUBS)
        stubs['Note.hx'] = stubs['Note.hx'].replace(' public function new(', '''
 public var quant:Int=4;public var isQuant:Bool=false;public var canQuant:Bool=true;
 public var nightmareVisionQuantInitialized:Bool=false;
 public var prevNote:Note;public var sourceDirection:Int=0;public var noteData:Int=0;
 public var nightmareVisionTypeRuntime:Dynamic;
 public function new(''', 1)
        # Extend the shared RGB facade without replacing its updated apply method.
        stubs['NightmareVisionRGBGraphics.hx'] = stubs['NightmareVisionRGBGraphics.hx'].replace(
            ' public function new(', """
 public function setColors(colors:Array<Int>):Void {palette.r=colors[0];palette.g=colors[1];palette.b=colors[2];}
 public function getColors():Array<Int> return [palette.r,palette.g,palette.b];
 public function new(""", 1)
        source = (ROOT / 'source/Strumline.hx').read_text()
        handle = method(source, 'public function handleColors(')
        stubs['Strumline.hx'] = stubs['Strumline.hx'].replace(' public function new() {}', '''
 public var nightmareVisionSource:Bool=true;public var useRGBShader:Bool=true;
 public var isQuant:Bool=false;public var nightmareVisionQuantPrefs:Dynamic;
 public var lastNote:Note;
 function getNightmareVisionRGB():NightmareVisionRGBGraphics {
  if(nightmareVisionRGB==null)nightmareVisionRGB=new NightmareVisionRGBGraphics(nightmareVisionPalette);
  return nightmareVisionRGB;
 }
 __HANDLE__
 public function new() {}'''.replace('__HANDLE__', handle), 1)
        main = r'''
import flixel.graphics.frames.FlxAtlasFrames;
import Strumline.StrumNote;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main() {
  var prefs:Dynamic={quants:true,arrowRGBquant:[[0xFF112233,0xFFFFFFFF,0xFF010203]]};
  var other:Dynamic={quants:false,arrowRGBquant:[[0xFF556677,0xFFFFFFFF,0xFF08090A]]};
  var paths=new NightmareVisionPaths('owner-a',new FlxAtlasFrames(['purple0000']));
  var skin=new NightmareVisionNoteSkin(paths,'default',4,0);
  var note=new Note();note.prevNote=note;
  check(skin.applyNote(note,0),'skin setup');
  note.nightmareVisionRGB.alpha=0.4;note.nightmareVisionRGB.flash=0.6;
  var rgb=note.nightmareVisionRGB;var lane=skin.palette(0).r;
  NightmareVisionQuantRendering.classify(note,prefs,0.5);
  NightmareVisionQuantRendering.apply(note,skin,prefs);
  check(note.quant==8 && note.isQuant && rgb.palette.r==0xFF193BE5,'source note quant');
  check(rgb==note.nightmareVisionRGB && rgb.alpha==0.4 && rgb.flash==0.6
   && skin.palette(0).r==lane,'isolated RGB state');
  skin.quantsEnabled=false;
  NightmareVisionQuantRendering.apply(note,skin,prefs);
  check(!note.isQuant && rgb.palette.r==0xFF193BE5,'metadata flag does not disable source quant color');
  note.canQuant=false;
  NightmareVisionQuantRendering.apply(note,skin,prefs);
  check(!note.isQuant && rgb.palette.r==0xFF193BE5,'stored quant color is independent of canQuant on reload');
  NightmareVisionQuantRendering.classify(note,prefs,0.5);
  NightmareVisionQuantRendering.apply(note,skin,prefs);
  check(note.quant==8 && rgb.palette.r==0xFF193BE5,'attachment/reload must not reclassify an initialized note');
  var unquantized=new Note();unquantized.canQuant=false;
  NightmareVisionQuantRendering.classify(unquantized,prefs,0.5);
  NightmareVisionQuantRendering.apply(unquantized,skin,prefs);
  check(unquantized.quant==4 && !unquantized.isQuant && unquantized.nightmareVisionRGB.palette.r==0xFFE51919,
   'source default quant retained when classification is disabled');
  note.canQuant=true;skin.quantsEnabled=true;
  NightmareVisionQuantRendering.classify(note,prefs,0.5);
  var next=new Note();next.prevNote=note;
  NightmareVisionQuantRendering.classify(next,prefs,1);
  check(next.quant==4,'ordinary host prevNote does not leak grid');
  var hold=new Note(true);hold.prevNote=note;
  NightmareVisionQuantRendering.classify(hold,prefs,0.625);
  check(hold.quant==8,'sustain inherits previous source quant');
  NightmareVisionQuantRendering.apply(note,skin,other);
  check(!note.isQuant && note.quant==8 && rgb.palette.r==lane,'other owner flag and lane fallback');
  note.nightmareVisionTypeRuntime={api:{customColors:function(n:Note):Array<Dynamic> return [0xFFABCDEF,0xFFFFFFFF,0xFF111111]}};
  NightmareVisionQuantRendering.apply(note,skin,prefs);
  check(rgb.palette.r==0xFFABCDEF,'custom note color survives reload');
  var receptor=new StrumNote();receptor.nightmareVisionPalette=skin.palette(0);
  receptor.nightmareVisionQuantPrefs=prefs;receptor.isQuant=true;
  receptor.handleColors('pressed',note);
  check(receptor.nightmareVisionRGB.palette.r==0xFF112233 && receptor.lastNote==note
   && receptor.shader==receptor.nightmareVisionRGB.palette.shader,'pressed quant uses owner row zero and rendered palette');
  receptor.handleColors('confirm');
  check(receptor.nightmareVisionRGB.palette.r==0xFFABCDEF,'confirm keeps last-note custom colors');
  receptor.nightmareVisionQuantPrefs=other;receptor.handleColors('pressed');
  check(receptor.nightmareVisionRGB.palette.r==0xFF556677 && prefs.arrowRGBquant[0][0]==0xFF112233,'owner isolation');
  receptor.handleColors('static');check(!receptor.nightmareVisionRGB.enabled,'static disables recoloring');
  receptor.useRGBShader=false;var before=receptor.nightmareVisionRGB.palette.r;
  receptor.handleColors('pressed');check(receptor.nightmareVisionRGB.palette.r==before,'explicit disabled shader retained');
  trace('NV_QUANT_RENDERING_OK');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            for name, content in stubs.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            (work / 'Main.hx').write_text(main, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                                     '-main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NV_QUANT_RENDERING_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
