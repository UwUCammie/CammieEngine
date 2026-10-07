"""Execute production NV field generation, lookup, bank routing and RGB access."""
from nv_field_fixture_support import write_nv_field_dependencies
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


class NvMultifieldRoutesTest(unittest.TestCase):
    def test_real_generation_lookup_layout_input_note_and_rgb_routes(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('if (nightmareVisionScripts != null && !nightmareVisionAcceptsNoteField(chartAddress.playfieldIndex)) continue;', play)
        strums = (ROOT / 'source/Strumline.hx').read_text()
        note = (ROOT / 'source/Note.hx').read_text()
        methods = '\n'.join(method(play, sig) for sig in [
            'function nightmareVisionLaneCount():Int',
            'function nightmareVisionKeyCount():Int',
            'function nightmareVisionAcceptsNoteField(id:Int):Bool',
            'function initializeNightmareVisionPlayFields():Void',
            'public function getNightmareVisionField(id:Int)',
            'function nightmareVisionFieldForNote(note:Note)',
            'public function generatePlayfields():Void',
            'function createNightmareVisionDefaultField(lane:Int)',
            'function nightmareVisionConfigureFieldReceptors(field:NightmareVisionPlayFieldView):Void',
            'function configureNightmareVisionStrumlines():Void',
            'function getNoteStrumline(note:Note)',
            'function setSourceInputReceptor(key:Int',
        ])
        rgb_start = strums.index('@:keep public var rgbShader(get, never):Dynamic;')
        rgb_end = strums.index('\n\t/** Match the source receptor\'s lane/last-note fallback and pressed override. */', rgb_start)
        lane_start = note.index('@:keep public var lane(get, set):Int;')
        lane_end = note.index('\n\t/** Direction', lane_start)
        fixture = r'''
class PsychRGBShaderReference { public function new() {} }
class NightmareVisionRGBGraphics {
 public var alpha:Float = 1;
 public var colors:Array<Int>=[];
 public function new(palette:Dynamic) {}
 public function setColors(colors:Array<Int>):Void this.colors=colors;
 public function getColors():Array<Int> return colors;
}
class FlxG { public static var width:Float=1280; public static var height:Float=720; }
class Skin extends NightmareVisionNoteSkin { public function new() super(); }
class Note {
 public static var NOTE_AMOUNT:Int=4;
 public static var swagWidth:Float=112;
 public var sourcePlayfieldIndex:Int=-1;
 public var noteData:Int=3;
 public var mustPress:Bool=false;
 public var codenameInputLine:Dynamic=null;
 public function new() {}
 __LANE__
}
class Main {
 public var nightmareVisionPaths:Dynamic=null;
 public var modifiersRegistered=false;
 public var modManager:Dynamic={configureDimensions:function(keys:Int,lanes:Int):Void {},registerEssentialModifiers:function():Void {},registerDefaultModifiers:function():Void {},registerScriptedModifiers:function():Void {}};
 public var SONG:Dynamic = {lanes:3, uiType:'default', format:'nmv2'};
 public var nightmareVisionScripts:Dynamic = {};
 public var nightmareVisionPrefs:Dynamic = {view:{quants:false,opponentStrums:true,middleScroll:false}};
 public var generatedFields:Bool=false; public var genNotesBeforeCountdown:Bool=true;
 public var skipArrowStartTween:Bool=false; public var skipCountdown:Bool=false;
 public var startOnTime:Float=0; public var isStoryMode:Bool=false;
 public var nightmareVisionDefaultGenerationDepth:Int=0;
 public var playFields:NightmareVisionPlayFields;
 public var nightmareVisionFields:Array<NightmareVisionPlayFieldView>=[];
 public var nightmareVisionStrumlines:Array<Strumline>=[];
 public var nightmareVisionOwnedStrumlines:Array<Strumline>=[];
 public var nightmareVisionOwnedFields:Array<NightmareVisionPlayFieldView>=[];
 public var nightmareVisionNoteFields:haxe.ds.ObjectMap<Note, NightmareVisionPlayFieldView>=new haxe.ds.ObjectMap();
 public var playerStrums:Strumline=new Strumline(0,50,'default');
 public var enemyStrums:Strumline=new Strumline(0,50,'default');
 public var strumLine:Dynamic={y:50};
 public var camHUD:Dynamic={};
 public var boyfriend:Dynamic={stunned:false};
 public var dad:Dynamic={stunned:false};
 public var cpuControlled:Bool=false;
 public var downscroll:Bool=false;
 public var strumsBlocked:Array<Bool>=[];
 public function new() {}
 function comboBreakThingies(player:Int):Void {}
 function callNightmareVision(name:String,args:Array<Dynamic>):Dynamic return 0;
 function nightmareVisionSourceSkinRegistry():Dynamic return {noteskins:[]};
 function initializeNightmareVisionFieldSplashes(field:NightmareVisionPlayFieldView):Void {}
 function bindNightmareVisionPlayFieldLifecycle(field:NightmareVisionPlayFieldView):Void {
  nightmareVisionOwnedFields.push(field);
  field.bindNativeLifecycle({generateReceptors:function(f) {
   f.strumline.regenerate(); nightmareVisionConfigureFieldReceptors(f);
  },clearReceptors:function(f) f.strumline.members.resize(0),fadeIn:function(f,skip) {}});
 }
 function nightmareVisionClearFieldReceptors(f:NightmareVisionPlayFieldView):Void f.clearReceptors();
 function nightmareVisionDefaultSkinForField(id:Int,reuseCached:Bool=true):NightmareVisionNoteSkin return null;
 function nightmareVisionSkinForField(id:Int):NightmareVisionNoteSkin return null;
 function getCodenameLineStrumline(id:Int):Strumline return null;
 function getInputStrumline(line:Dynamic, player:Bool):Strumline return player ? playerStrums : enemyStrums;
 function attachNightmareVisionPlayField(field:NightmareVisionPlayFieldView):Void {
  if(field.strumline!=null && !nightmareVisionOwnedStrumlines.contains(field.strumline)) nightmareVisionOwnedStrumlines.push(field.strumline);
 }
 function detachNightmareVisionPlayField(field:NightmareVisionPlayFieldView):Void {}
 function publishNightmareVisionReceptorBanks():Void {}
 function syncNightmareVisionPlayFieldCollection():Void {
  if(playFields!=null) nightmareVisionFields=playFields.members;
 }
 __METHODS__
 static function check(ok:Bool, label:String) { if (!ok) throw label; }
 static function main() {
  var h=new Main();
  h.initializeNightmareVisionPlayFields();
  check(h.playFields.length==0 && h.getNightmareVisionField(0)==null, 'pre-generation source fields empty');
  h.generatePlayfields();
  h.configureNightmareVisionStrumlines();
  check(h.playFields.length==3 && h.nightmareVisionFields==h.playFields.members, 'three live source fields');
  var f0=h.getNightmareVisionField(0), f1=h.getNightmareVisionField(1), f2=h.getNightmareVisionField(2);
  check(f0.baseX==FlxG.width-112*2-103 && f1.baseX==112*2+97 && f2.baseX==FlxG.width*0.5-3,
   'authored field center positions');
  check(f0.strumline.x==f0.baseX-224 && f1.strumline.x==f1.baseX-224
   && f2.strumline.x==f2.baseX-224 && f2.strumline.y==f2.baseY-56,
   'receptor banks use their live field base coordinates');
  check(f0.strumline==h.playerStrums && f1.strumline==h.enemyStrums, 'legacy source fields');
  check(f2.strumline!=f0.strumline && f2.strumline!=f1.strumline, 'extra bank must be distinct');
  check(f2.members==f2.strumline.members && f2.members!=f0.members, 'live unique receptor arrays');
  var extra=new Strumline.StrumNote(); f2.strumline.members.push(extra);
  check(f2.members[4]==extra, 'field members stay live');
  check(f0.owner==h.boyfriend && f1.owner==h.dad && f2.owner==h.boyfriend, 'donor owner policy');
  check(f0.playerControls && !f1.playerControls && f2.playerControls, 'donor input ownership');
  check(!f0.autoPlayed && f1.autoPlayed && f2.autoPlayed, 'donor autoplay policy');
  check(f0.noteSplashes && !f1.noteSplashes && !f2.noteSplashes, 'donor splash defaults');
  check(!f0.autoPlayed, 'source construction captures initial CPU flag');
  f0.autoPlayed=true; check(f0.autoPlayed, 'source CPU flag remains mutable');
  f2.autoPlayed=false; check(f2.canInput(), 'extra field manual override');
  var n=new Note(); n.lane=2;
  check(n.sourcePlayfieldIndex==2 && n.noteData==3 && h.getNoteStrumline(n)==f2.strumline, 'note field independent of direction');
  h.setSourceInputReceptor(3,true,false,2);
  check(f2.members[3].animation.curAnim.name=='pressed' && f0.members[3].animation.curAnim.name=='static', 'input targets field two');
  h.setSourceInputReceptor(3,true,true,2);
  check(f2.members[3].animation.curAnim.name=='static', 'release targets field two');
  check(f2.members[0].nightmareVisionSource, 'NV receptors marked with missing skin');
  var nv=f2.members[0].rgbGraphics;
  check(nv!=null && nv==f2.members[0].rgbShader, 'NV modern and legacy RGB views share identity');
  nv.alpha=0.3; check(f2.members[0].rgbGraphics.alpha==0.3, 'live NV RGB writes');
  var psych=new Strumline.StrumNote();
  check(psych.rgbShader==psych.psychRGBShader && psych.rgbGraphics==null, 'Psych RGB typed object preserved');
  f0.ID=7; f2.ID=0;
  check(h.getNightmareVisionField(0)==f2 && h.getNightmareVisionField(7)==f0, 'mutable IDs take precedence');
  check(h.getNightmareVisionField(2)==f2 && h.getNightmareVisionField(-1)==null && h.getNightmareVisionField(9)==null, 'array fallback and missing lookup');
  var count=h.playFields.length; h.generatePlayfields(); check(h.playFields.length==count,'generation idempotent');
  for (format in [null,'','nmv2','psych_v1']) {
   var missing=new Main(); missing.SONG.format=format;
   missing.initializeNightmareVisionPlayFields();missing.generatePlayfields();missing.configureNightmareVisionStrumlines();
   var receptor=missing.playFields.members[2].members[0];
   check(receptor.nightmareVisionSource,'selected NV receptor marking independent of chart format');
   var shader:Dynamic=receptor.rgbShader;
   check(shader!=null && shader==receptor.rgbGraphics,'missing format still exposes NV graphics');
   Reflect.callMethod(shader,Reflect.field(shader,'setColors'),[[1,2,3]]);
   check(receptor.rgbGraphics.getColors().join(',')=='1,2,3','reflective color call targets NV graphics');
  }
  var absent=new Main();absent.SONG={lanes:3,uiType:'default'};
  absent.initializeNightmareVisionPlayFields();absent.generatePlayfields();absent.configureNightmareVisionStrumlines();
  var absentRGB:Dynamic=absent.playFields.members[2].members[0].rgbShader;
  Reflect.callMethod(absentRGB,Reflect.field(absentRGB,'setColors'),[[4,5,6]]);
  check(absent.playFields.members[2].members[0].rgbGraphics.getColors().join(',')=='4,5,6','absent format RGB adapter live');
  var native=new Main();native.nightmareVisionScripts=null;
  native.configureNightmareVisionStrumlines();
  check(!native.playerStrums.members[0].nightmareVisionSource,'no NV runtime preserves native receptor');

  for (lanes in [null,0,-2,1,3,5]) {
   var one=new Main(); one.SONG.lanes=lanes; one.initializeNightmareVisionPlayFields(); one.generatePlayfields();
   var expected=lanes==null || lanes<1 ? 2 : lanes;
   check(one.playFields.length==expected,'authored lane count and default');
   check(!one.nightmareVisionAcceptsNoteField(-1) && !one.nightmareVisionAcceptsNoteField(expected), 'out of range fields excluded');
   for (id in 0...expected) check(one.nightmareVisionAcceptsNoteField(id), 'valid field admitted');
   check(one.enemyStrums.visible==(expected!=1),'one field hides unused opponent bank');
  }
 }
}
'''.replace('__METHODS__', methods).replace('__LANE__', note[lane_start:lane_end])
        line_fixture = r'''
class Strumline {
 public var ID:Int=99;
 public var members:Array<StrumNote>=[];
 public var x:Float=0;
 public var y:Float=0;
 public var centerReceptors:Bool=false;
 public var alpha:Float=1;
 public var visible:Bool=true;
 public var cameras:Array<Dynamic>=[];
 public var noteHoldCovers:Dynamic={cameras:[]};
 public function new(x:Float,y:Float,ui:String,transition:Bool=false,generate:Bool=true) { if(generate) regenerate(); }
 public function regenerate():Void { members.resize(0); for (i in 0...4) { var s=new StrumNote(); s.ID=i; members.push(s); } }
 public function setCenteredLayout(x:Float,y:Float) { this.x=x; this.y=y; }
 public function resetStrums() {}
 public function forEachReceptor(fn:StrumNote->Void) { for(s in members) fn(s); }
}
class StrumNote {
 public var ID:Int=0;
 public var alphaMult:Float=1;
 public var animation:Dynamic={curAnim:{name:'static'}};
 public var resetAnim:Float=0;
 public var nightmareVisionSource:Bool=false;
 public var nightmareVisionPalette:Dynamic=null;
 public var nightmareVisionRGB:Main.NightmareVisionRGBGraphics=null;
 public var psychRGBShader:Main.PsychRGBShaderReference=new Main.PsychRGBShaderReference();
 public var isQuant:Bool=false;
 public var nightmareVisionQuantPrefs:Dynamic;
 public function new() {}
 public function playAnim(name:String) { animation.curAnim.name=name; }
 public function handleColors(anim:String=''):Void {}
 __RGB__
}
'''.replace('__RGB__', strums[rgb_start:rgb_end].replace(':NightmareVisionRGBGraphics', ':Main.NightmareVisionRGBGraphics').replace('new NightmareVisionRGBGraphics', 'new Main.NightmareVisionRGBGraphics'))
        # Bank/control/RGB stubs are not helper receivers; the real wrapper route is covered separately.
        fixture = fixture.replace('NightmareVisionSpriteMethods.bind', 'FixtureSpriteBinding.bind')
        fixture += '\nclass FixtureSpriteBinding {public static function bind(object:Dynamic,owner:Dynamic):Void {}}'
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            (work / 'Strumline.hx').write_text(line_fixture, newline='\n')
            write_nv_field_dependencies(work)
            (work / 'NightmareVisionNoteSkin.hx').write_text(
                'class NightmareVisionNoteSkin { public function new() {} '
                'public function applyReceptor(s:Dynamic, id:Int):Void {} }', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory,
                                     '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
