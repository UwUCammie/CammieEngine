"""Historical receptor pointers through real Iris and source Flixel group drawing."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from nv_field_fixture_support import write_nv_field_dependencies
from test_nv_multifield_routes import method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT=Path(__file__).resolve().parents[2]

class LegacyReceptorTest(unittest.TestCase):
    def test_live_pointer_array_reflection_and_camera_inheritance(self):
        group_source=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text()
        draw=method(group_source,'override public function draw():Void').replace('override ','')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            write_nv_field_dependencies(work)
            write_flixel_point_stub(work)
            (work/'flixel/FlxCamera.hx').write_text('package flixel;class FlxCamera {public static var _defaultCameras:Array<FlxCamera>=[];public var name:String;public function new(n:String)name=n;}')
            (work/'Strumline.hx').write_text(r'''import flixel.FlxCamera;
class Strumline {
 public var group:FixtureGroup=new FixtureGroup();public var members(get,never):Array<StrumNote>;
 public function new(){}function get_members()return group.members;
 public var cameraWrites:Int=0;public var cameras(get,set):Array<FlxCamera>;
 function get_cameras()return group.cameras;
 function set_cameras(v:Array<FlxCamera>):Array<FlxCamera> {cameraWrites++;group.cameras=v;for(child in members)child.cameras=v;return v;}
}
class FixtureGroup {
 public var members:Array<StrumNote>=[];var _cameras:Array<FlxCamera>;
 public var cameras(get,set):Array<FlxCamera>;
 public function new(){}function get_cameras()return _cameras==null?FlxCamera._defaultCameras:_cameras;
 function set_cameras(v:Array<FlxCamera>)return _cameras=v;
 __DRAW__
}
class StrumNote {
 public var cameras:Array<FlxCamera>;public var seen:String;public var exists=true;public var visible=true;
 public var resetAnim:Float=0;public function playAnim(s:String):Void{}public function new(){}
 public function draw():Void {seen=(cameras==null?FlxCamera._defaultCameras:cameras)[0].name;}
}
'''.replace('__DRAW__',draw))
            (work/'Main.hx').write_text(r'''import flixel.FlxCamera;import Strumline.StrumNote;
class Main {
 static function check(v:Bool,s:String){if(!v)throw s;}
 static function field(id:Int):NightmareVisionPlayFieldView {var f=new NightmareVisionPlayFieldView(id,function()return false);f.legacyGroupCameras=true;f.strumline=new Strumline();f.strumline.members.push(new StrumNote());return f;}
 static function main(){
  var main=new FlxCamera('main'),hud=new FlxCamera('hud'),world=new FlxCamera('world'),custom=new FlxCamera('custom');
  FlxCamera._defaultCameras=[main];
  var player=field(0),opponent=field(1),third=field(2);
  var fields=[opponent,player];var refs=new NightmareVisionLegacyReceptors();refs.capture(0,player);refs.capture(1,opponent);
  var state={playerStrums:'native',strumLineNotes:'native'};
  var i=new NightmareVisionScriptInterp(state);NightmareVisionLegacyReceptorBindings.install(i,state,refs,function()return fields);
  i.variables.set('game',state);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  i.variables.set('world',[world]);i.variables.set('custom',[custom]);i.variables.set('third',third);
  var parser=new NightmareVisionScriptParser();
  i.execute(parser.parseString("before=playerStrums;opponentStrums.cameras=world;opponentStrums.members[0].cameras=custom;first=strumLineNotes;reflected=Reflect.field(game,'opponentStrums');"));
  check(i.variables.get('before')==player&&i.variables.get('reflected')==opponent,'source globals and reflected field identity');
  var inherited=new StrumNote();opponent.strumline.members.push(inherited);
  opponent.strumline.group.draw();
  check(opponent.strumline.cameraWrites==0,'legacy group must bypass native child propagation');
  check(opponent.members[0].seen=='custom'&&inherited.seen=='world'&&FlxCamera._defaultCameras[0]==main,'group camera inheritance, explicit child override, default restored');
  opponent.initializeCameras([hud]);opponent.strumline.group.draw();check(inherited.seen=='world','reattachment preserves authored camera');
  opponent.ID=72;fields.reverse();
  i.execute(parser.parseString("stable=opponentStrums;second=game.strumLineNotes;again=Reflect.getProperty(game,'strumLineNotes');game.playerStrums=third;assigned=playerStrums;"));
  check(i.variables.get('stable')==opponent&&i.variables.get('assigned')==third,'ID/order changes preserve pointers and source assignment stays live');
  var first:Array<Dynamic>=cast i.variables.get('first'),second:Array<Dynamic>=cast i.variables.get('second'),again:Array<Dynamic>=cast i.variables.get('again');
  check(first.length==2&&second.length==3&&second[0]==player.members[0]&&first!=second&&again!=second,'flattened array freshly follows field order and membership');
  check(state.playerStrums=='native'&&state.strumLineNotes=='native','native gameplay pointers unchanged');
  check(refs.readProperty('opponentStrums',fields)==opponent,'shared property route reads captured source pointer');
  refs.writeProperty('opponentStrums',third);i.execute(parser.parseString("sharedWrite=opponentStrums;"));check(i.variables.get('sharedWrite')==third,'shared writes visible to HScript');
  refs.writeProperty('opponentStrums',opponent);
  var combined:Array<Dynamic>=cast refs.readProperty('strumLineNotes',fields);check(combined.length==3&&combined[0]==player.members[0],'shared flattened field order');

  var blocked=false;try i.execute(parser.parseString("Reflect.setProperty(game,'strumLineNotes',[]);"))catch(_:Dynamic)blocked=true;
  check(blocked&&state.strumLineNotes=='native','read-only reflected getter');
  var late=new NightmareVisionPlayFieldView(3,function()return false);late.legacyGroupCameras=true;late.cameras=[world];late.strumline=new Strumline();late.strumline.members.push(new StrumNote());late.strumline.group.draw();check(late.members[0].seen=='world','camera assignment before bank binding retained');
  var modern=new NightmareVisionPlayFieldView(4,function()return false);modern.cameras=[hud];modern.strumline=new Strumline();modern.strumline.members.push(new StrumNote());
  modern.cameras=[world];check(modern.strumline.cameraWrites==2&&modern.members[0].cameras[0]==world,'modern/native SpriteGroup camera propagation preserved');
  modern.initializeCameras([hud]);check(modern.members[0].cameras[0]==world,'defaults preserve authored modern cameras');
  refs.release();i.execute(parser.parseString("released=opponentStrums;"));check(i.variables.get('released')==null,'host teardown clears captured pointers');i.release();
 }
}
''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
