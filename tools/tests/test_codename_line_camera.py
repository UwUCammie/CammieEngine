"""Execute the live Codename actor-line camera against the production method."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameLineCameraTest(unittest.TestCase):
    def test_visible_average_scene_event_and_control_precedence(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        match = re.search(r'\tpublic function moveCodenameCamera\(\):Bool \{', source)
        self.assertIsNotNone(match)
        brace = source.index('{', match.start())
        depth = 0
        method = None
        for at in range(brace, len(source)):
            depth += (source[at] == '{') - (source[at] == '}')
            if depth == 0:
                method = source[match.start():at + 1]
                break
        self.assertIsNotNone(method)
        self.assertIn('curCameraTarget = 0;', source)
        self.assertIn("scriptableCamera == 'false' && moveCodenameCamera()", source)
        fixture = r'''
import flixel.math.FlxPoint;
class Actor {
 public var visible:Bool=true;
 public var x:Float;public var y:Float;
 public function new(x:Float,y:Float,visible=true) {this.x=x;this.y=y;this.visible=visible;}
 public function getCameraPosition():FlxPoint return FlxPoint.get(x,y);
}
class Runtime {
 public var lines:Map<Int,Array<Actor>>=[];
 public function new() {}
 public function lineCharacters(index:Int):Array<Actor> return lines.exists(index)?lines.get(index):[];
}
class Main {
 var codenameActors:Runtime=new Runtime();
 var inputLines:Map<Int,CodenameInputLine<Actor>>=[];
 function getCodenameInputLine(index:Int):CodenameInputLine<Actor> return inputLines.get(index);
 public var curCameraTarget=0;
 var camFollow=FlxPoint.get(900,900);
 var codenameCameraControlled=false;
 var codenameCameraFollowSuspended=false;
 var forceCamera=false;
 var codenameCameraLineViews:Map<Int,Dynamic>=new Map();
 var codenameScriptScopes:Array<Dynamic>=[];
 public function new() {}
 function getCodenameLineCharacters(index:Int):Array<Actor> return codenameActors.lineCharacters(index);
 function callCodenameScript(scope:Dynamic,name:String,args:Array<Dynamic>):Bool {
  scope.callback(args[0]);return true;
 }
''' + method + r'''
 static function check(ok:Bool,msg:String):Void if(!ok)throw msg;
 static function near(actual:Float,expected:Float,msg:String):Void
  if(Math.abs(actual-expected)>.0001)throw msg+': '+actual+' != '+expected;
 public function run():Void {
  var scriptPointEvent=new CodenameCameraMoveEvent(FlxPoint.get(1,2),null,1,0);
  var scriptPointInterp=new hscript.Interp();
  scriptPointInterp.variables.set('event',scriptPointEvent);
  scriptPointInterp.variables.set('movement',FlxPoint.get(3,4));
  scriptPointInterp.execute(new hscript.Parser().parseString('event.position.addPoint(movement);'));
  near(scriptPointEvent.position.x,4,'HScript addPoint x');
  near(scriptPointEvent.position.y,6,'HScript addPoint y');
  var first=new Actor(100,200), duplicate=new Actor(300,400), hidden=new Actor(999,999,false);
  codenameActors.lines.set(0,[first,duplicate,hidden]);
  var calls=0;var line:Dynamic=null;
  codenameScriptScopes.push({callback:function(e:CodenameCameraMoveEvent) {
   calls++;check(e.focusedCharacters==2,'visible count');
   check(e.lineIndex==0 && e.strumLine.lineIndex==0,'line index');
   check(e.strumLine.characters[0]==first && e.strumLine.characters[1]==duplicate,'actor order');
   if(line==null)line=e.strumLine;else check(line==e.strumLine,'stable line view');
  }});
  check(moveCodenameCamera(),'default target');near(camFollow.x,200,'mean x');near(camFollow.y,300,'mean y');
  check(calls==1,'callback count');
  // Rebinding an actor preserves the line view but refreshes its identities.
  var replacement=new Actor(500,600);first=replacement;
  codenameActors.lines.set(0,[replacement,duplicate,hidden]);
  check(moveCodenameCamera(),'rebound target');near(camFollow.x,400,'rebound mean');
  codenameScriptScopes[0].callback=function(e:CodenameCameraMoveEvent) {
   e.position.addPoint(FlxPoint.get(23,-11));
  };
  check(moveCodenameCamera(),'script addPoint');near(camFollow.x,423,'script point x');near(camFollow.y,489,'script point y');
  codenameScriptScopes[0].callback=function(e:CodenameCameraMoveEvent) {
   e.position=FlxPoint.get(12,34);
  };
  check(moveCodenameCamera(),'mutable target');near(camFollow.x,12,'mutated x');near(camFollow.y,34,'mutated y');
  codenameScriptScopes[0].callback=function(e:CodenameCameraMoveEvent) e.preventDefault();
  check(moveCodenameCamera(),'cancelled target handled');near(camFollow.x,12,'cancel x');
  curCameraTarget=-1;check(moveCodenameCamera(),'negative target owned');
  near(camFollow.x,12,'negative target leaves focus');
  curCameraTarget=4;check(moveCodenameCamera(),'invalid target owned');
  near(camFollow.x,12,'invalid target leaves focus');
  curCameraTarget=0;codenameActors.lines.set(0,[hidden]);
  check(moveCodenameCamera(),'invisible-only target owned');
  near(camFollow.x,12,'invisible-only leaves focus');
  codenameActors.lines.set(0,[replacement,duplicate]);
  codenameCameraControlled=true;check(moveCodenameCamera(),'authored position control');
  codenameCameraControlled=false;codenameCameraFollowSuspended=true;
  check(moveCodenameCamera(),'tween suspension');
  codenameCameraFollowSuspended=false;forceCamera=true;
  check(moveCodenameCamera(),'script camera control');
  forceCamera=false;
  var model=new CodenameInputLine<Actor>(0,1,false,false,false,{},null,null,getCodenameLineCharacters);
  inputLines.set(0,model);
  var edited=new Actor(75,85);
  model.characters=[null,edited];
  codenameScriptScopes[0].callback=function(e:CodenameCameraMoveEvent) {
   check(e.strumLine==model,'camera and input expose different line objects');
   check(e.focusedCharacters==1,'camera ignored mutable input actor slots');
   e.strumLine.cpu=true;e.strumLine.ID=99;
  };
  check(moveCodenameCamera(),'shared input model');near(camFollow.x,75,'mutable actors camera x');
  check(model.cpu&&model.ID==99,'camera model writes not visible to input');
  model.characters=[duplicate];
  codenameCameraFollowSuspended=true;
  check(moveCodenameCamera(),'model persists during scroll tween');near(camFollow.x,300,'scroll tween suppressed live focus updates');
  codenameCameraFollowSuspended=false;
  model.characters=[];
  check(moveCodenameCamera(),'empty model keeps focus');near(camFollow.x,300,'empty model resurrected metadata actors');
  model.release();
  check(moveCodenameCamera(),'released model remains empty');near(camFollow.x,300,'released model resurrected actors');
  codenameActors=null;
  check(!moveCodenameCamera(),'non-Codename chart');
 }
 static function main():Void new Main().run();
}
'''
        point = r'''
package flixel.math;
class FlxPoint {
 public var x:Float;public var y:Float;
 public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}
 public static function get(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function setPosition(x:Float,y:Float):Void{this.x=x;this.y=y;}
 public function put():Void {}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            path = Path(work)
            (path / 'Main.hx').write_text(fixture, newline='\n')
            (path / 'flixel/math').mkdir(parents=True)
            (path / 'flixel/math/FlxPoint.hx').write_text(point, newline='\n')
            for name in ('CodenameGameEvent', 'CodenameCameraMoveEvent',
                         'CodenameCameraMovePoint', 'CodenameStrumlineLayout', 'CodenameInputLine',
                         'CodenameStrumlineNoteCollection', 'CodenameLineNoteQuery',
                         'CodenameLineNoteIndex'):
                (path / f'{name}.hx').write_text((ROOT / f'source/{name}.hx').read_text(), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'tools/tests/haxe_stubs'),
                                     '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(path),
                                     '--run', 'Main'], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
