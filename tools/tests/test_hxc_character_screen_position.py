"""Returned HXC screen positions must survive native/accessor field reflection."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HxcCharacterScreenPositionTest(unittest.TestCase):
    def test_replacement_point_actor_scope_and_failure_cleanup(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = source.split('\tpublic function dispatchHxcCharacterScreenPosition(', 1)[1].split(
            '\n\t/** Notify character companions', 1)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text('''
class Character { public function new() {} }
class FlxCamera { public function new() {} }
class FlxPoint {
 public var x(get,never):Float;
 public var y(get,never):Float;
 var px:Float; var py:Float;
 public function new(x:Float,y:Float) { px=x; py=y; }
 function get_x():Float return px;
 function get_y():Float return py;
}
class Host {
 public var actor = new Character();
 public var hxcCharacterDispatchDepth:Int = 0;
 var hxcCharacterScopeNames = ['scope'=>'actor'];
 public var active = true;
 public var fail = false;
 public var calls = 0;
 public var returned:Dynamic;
 public function new() {}
 function hxcCharacterScopeIsActive(scope:String):Bool return active;
 function hxcCharacterForScope(scope:String):Array<Character> return [actor];
 function callHscript(name:String,args:Array<Dynamic>,scope:String,optional:Bool,out:Array<Dynamic>):Void {
  calls++;
  if (fail) throw 'fixture callback failure';
  out.push(returned);
 }
 public function dispatchHxcCharacterScreenPosition(''' + method + '''
}
class Main {
 static function main() {
  var host = new Host(); var input = new FlxPoint(10,20); var camera = new FlxCamera();
  var replacement = new FlxPoint(0,-2.5);
  if (Reflect.hasField(replacement,'x')) throw 'fixture needs accessor point';
  host.returned = replacement;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != replacement)
   throw 'valid replacement point was discarded';
  if (input.x != 10 || input.y != 20) throw 'input point was changed';
  host.returned = null;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != input)
   throw 'null return lost original position';
  host.returned = {unrelated:0};
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != input)
   throw 'unrelated return replaced position';
  host.returned = replacement;
  host.active = false;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != input)
   throw 'inactive scope changed position';
  host.active = true;
  if (host.dispatchHxcCharacterScreenPosition(new Character(),input,camera) != input)
   throw 'other actor received callback';
  var count = host.calls;
  host.hxcCharacterDispatchDepth = 1;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != input || host.calls != count)
   throw 'recursive callback was not suppressed';
  host.hxcCharacterDispatchDepth = 0;
  host.fail = true;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != input
      || host.hxcCharacterDispatchDepth != 0) throw 'failure leaked callback depth';
  host.fail = false;
  if (host.dispatchHxcCharacterScreenPosition(host.actor,input,camera) != replacement)
   throw 'callback did not recover after failure';
 }
}
''')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(work),
                                     '--main', 'Main', '--interp'], cwd=work,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
