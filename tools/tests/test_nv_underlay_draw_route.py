"""Execute the production FIELD draw route at its real receptor-bank draw slot."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvUnderlayDrawRouteTest(unittest.TestCase):
    def test_live_draw_geometry_preferences_camera_modifiers_and_bank_order(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        strums = (ROOT / 'source/Strumline.hx').read_text()
        draw = method(play, 'function drawNightmareVisionFieldUnderlay(').replace(
            'field:NightmareVisionPlayFieldView', 'field:Dynamic')
        attach = method(play, 'function attachNightmareVisionFieldDisplay(').replace(
            'field:NightmareVisionPlayFieldView', 'field:Dynamic')
        enable = method(play, 'function enableNightmareVisionFieldAttachment():Void')
        register = method(play, 'function attachNightmareVisionPlayField(').replace(
            'field:NightmareVisionPlayFieldView', 'field:Dynamic').replace(
            "new Strumline(field.baseX, field.baseY, SONG == null ? 'normal' : SONG.uiType)", 'new Bank()')
        setup = play[play.index('enemyStrums = new Strumline(92,'):play.index('comboBreakThingies(0);', play.index('enemyStrums = new Strumline(92,'))]
        self.assertLess(setup.index('add(playerStrums);'), setup.index('enableNightmareVisionFieldAttachment();'))
        bank_draw = method(strums, 'override public function draw():Void')
        self.assertIn('sourceFieldBeforeDraw = null;', method(strums, 'override public function destroy():Void'))
        fixture = r'''
class Point {
 public var x:Float=1;public var y:Float=1;
 public function new() {}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Sprite {
 public var exists:Bool=true;public var x:Float=0;public var alpha:Float=0;
 public var scale:Point=new Point();public var cameras:Array<Dynamic>;
 public var draws:Int=0;public var centers:Int=0;public var hitboxes:Int=0;
 public function new() {}
 public function screenCenter(axis:Dynamic):Void centers++;
 public function updateHitbox():Void hitboxes++;
 public function draw():Void {draws++;Main.events.push('underlay');}
}
class BankBase {
 public function new() {}
 public function draw():Void Main.events.push('receptors');
}
class Bank extends BankBase {
 public var cameras:Array<Dynamic>=[];public var noteHoldCovers:Dynamic=null;
 public var members:Array<Dynamic>=[];
 public var sourceFieldBeforeDraw:Void->Void;
 public function new() super();
 function drawAttachedEffects():Void Main.events.push('effects');
 __BANK_DRAW__
}
class Manager {
 public var calls:Array<String>=[];
 public function new() {}
 public function getValue(name:String,player:Int):Float {
  calls.push(name+':'+player);return name=='alpha'?0.2:0.5;
 }
}
class Main {
 public static var events:Array<String>=[];
 static var Y:String='Y';
 public var nightmareVisionPrefs:Dynamic={view:{underlayType:'Lane Underlay',underlayOpacity:0.8}};
 public var camHUD:Dynamic={viewWidth:800.0,viewHeight:600.0,angle:0.0};
 public var modManager:Manager=new Manager();public var members:Array<Dynamic>=[];
 public var nightmareVisionFieldAttachmentEnabled:Bool=false;
 public var nightmareVisionDefaultGenerationDepth:Int=0;
 public var grpNoteSplashes:Dynamic={};
 public var nightmareVisionFields:Array<Dynamic>=[];
 public var nightmareVisionOwnedStrumlines:Array<Bank>=[];
 public var SONG:Dynamic={uiType:'default'};
 public function new() {}
 function bindNightmareVisionPlayFieldLifecycle(field:Dynamic):Void {}
 function nightmareVisionGenerateFieldReceptors(field:Dynamic):Void {}
 function nightmareVisionSkinForField(id:Int):Dynamic return {};
 function nightmareVisionConfigureFieldReceptors(field:Dynamic):Void {}
 function syncNightmareVisionPlayFieldCollection():Void {}
 function add(value:Dynamic):Void members.push(value);
 function insert(index:Int,value:Dynamic):Void members.insert(index,value);
 __ENABLE__
 __REGISTER__
 __DRAW__
 __ATTACH__
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function near(a:Float,b:Float,label:String):Void check(Math.abs(a-b)<0.001,label+': '+a+' != '+b);
 static function main():Void {
  var ordered=new Main();ordered.nightmareVisionDefaultGenerationDepth=1;
  var hud={};ordered.members=[ordered.grpNoteSplashes,hud];var generatedBank=new Bank();
  ordered.attachNightmareVisionFieldDisplay({strumline:generatedBank});
  check(ordered.members[0]==generatedBank && ordered.members[1]==ordered.grpNoteSplashes && ordered.members[2]==hud,
   'late default generation retains existing bank slot before splash and HUD');
  var host=new Main();var bank=new Bank();var sprite=new Sprite();
  var receptor:Dynamic={x:100.0,width:50.0,exists:true,visible:true};
  var note:Dynamic={x:50.0,width:20.0,exists:true,alive:true,isOnScreen:function()return true};
  var field:Dynamic={strumline:bank,underlaySpr:sprite,underlayAlphaMult:0.75,
   members:[receptor],notes:[note],player:7};
  // Default fields register before the existing setup adds banks/notes/covers.
  var otherBank=new Bank();var otherSprite=new Sprite();
  bank.noteHoldCovers={cameras:[]};otherBank.noteHoldCovers={cameras:[]};
  var other:Dynamic={strumline:otherBank,underlaySpr:otherSprite,underlayAlphaMult:1.0,
   members:[{x:500.0,width:50.0,exists:true,visible:true}],notes:[],player:1};
  host.nightmareVisionFields=[field,other,null];
  host.attachNightmareVisionPlayField(field);host.attachNightmareVisionPlayField(other);
  check(bank.sourceFieldBeforeDraw==null && otherBank.sourceFieldBeforeDraw==null && host.members.length==0,
   'default field registration while disabled must not attach display');
  var notes={name:'notes'};var overlay={name:'overlay'};
  host.members=[otherBank,bank,overlay,notes,otherBank.noteHoldCovers,bank.noteHoldCovers];
  var order=host.members.copy();
  host.enableNightmareVisionFieldAttachment();host.enableNightmareVisionFieldAttachment();
  check(host.nightmareVisionFieldAttachmentEnabled && bank.sourceFieldBeforeDraw!=null && otherBank.sourceFieldBeforeDraw!=null,
   'enabling attachment installs both existing default draw hooks');
  check(host.members.length==order.length,'enabling attachment duplicates no groups');
  for(i in 0...order.length)check(host.members[i]==order[i],'enabling attachment preserves bank/note/cover ordering');
  otherBank.cameras=[host.camHUD];otherBank.draw();
  near(otherSprite.x,485,'default hooks retain distinct field geometry');
  events=[];host.modManager.calls=[];
  host.attachNightmareVisionFieldDisplay(field);host.attachNightmareVisionFieldDisplay(field);
  check(host.members.length==order.length&&bank.cameras[0]==host.camHUD,'bank attachment and camera fallback');
  bank.draw();check(events.join(',')=='underlay,receptors,effects','underlay is immediately before bank draw');
  near(sprite.x,35,'combined left edge');near(sprite.scale.x,130,'combined width');
  near(sprite.scale.y,600,'camera view height');near(sprite.alpha,0.24,'source modifier alpha');
  check(sprite.cameras[0]==host.camHUD && sprite.centers==1 && sprite.hitboxes==1,'camera and hitbox update');
  check(host.modManager.calls.join(',')=='alpha:7,dark:7','modifier uses current field.player');
  // Draw after live receptor/note mutations, without requiring an update tick.
  receptor.x=300;note.x=200;field.player=3;events=[];
  bank.cameras=[{viewWidth:1000.0,viewHeight:700.0,angle:90.0}];
  bank.draw();near(sprite.x,185,'live changed geometry');near(sprite.scale.x,180,'live changed span');
  near(sprite.scale.y,1000,'live bank camera angle and dimensions');
  check(sprite.cameras[0]==bank.cameras[0] && host.modManager.calls[2]=='alpha:3','live camera/player selection');
  host.modManager=null;bank.draw();near(sprite.alpha,0.6,'no modifier manager uses unmodified alpha');
  var before=sprite.draws;
  host.nightmareVisionPrefs.view.underlayType='Screen Dim';bank.draw();
  host.nightmareVisionPrefs.view.underlayType='Lane Underlay';host.nightmareVisionPrefs.view.underlayOpacity=0;bank.draw();
  host.nightmareVisionPrefs.view.underlayOpacity=0.8;sprite.exists=false;bank.draw();
  sprite.exists=true;field.underlaySpr=null;bank.draw();
  check(sprite.draws==before,'SCREEN/zero opacity/dead/null sprite skip FIELD draw');
  var replacement=new Sprite();field.underlaySpr=replacement;bank.draw();
  check(replacement.draws==1 && sprite.draws==before,'public sprite replacement used by existing closure');
  receptor.visible=false;note.alive=false;bank.draw();
  check(replacement.draws==1,'empty geometry skips safely');
  receptor.visible=true;bank.cameras=[{viewWidth:Math.NaN,viewHeight:600.0,angle:0.0}];bank.draw();
  check(replacement.draws==1,'invalid viewport skips safely');
  host.nightmareVisionPrefs=null;bank.draw();check(replacement.draws==1,'missing owner preferences skips safely');
  trace('NV_UNDERLAY_DRAW_ROUTE_OK');
 }
}
'''.replace('__DRAW__', draw).replace('__ATTACH__', attach).replace('__BANK_DRAW__', bank_draw).replace('__ENABLE__', enable).replace('__REGISTER__', register)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                                     '-main', 'Main', '-dce', 'full', '--interp'],
                                    capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NV_UNDERLAY_DRAW_ROUTE_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
