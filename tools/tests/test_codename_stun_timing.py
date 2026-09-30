"""Source stun uses actor elapsed time and resets when reassigned, without timers."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    start = source.index('\tfunction ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameStunTimingTest(unittest.TestCase):
    def test_elapsed_reset_and_native_option(self):
        source = (ROOT / 'source/Character.hx').read_text()
        body = '\n'.join(method(source, name) for name in ('get_stunned', 'set_stunned', 'codenameUpdateAfterSuper'))
        main = '''class OptionsHandler { public static var options={useMissStun:false}; }
class Actor {
 @:isVar public var stunned(get,set):Bool=false; var codenameStunnedTime:Float=0;
 public var codenameLiveDefinition:Dynamic={};
 var codenameRuntime={call:function(name:String,args:Array<Dynamic>) {}};
 var codenameAnimationLock=false;var lastAnimContext='DANCE';
 public function new(){}
 function codenameAdvanceLoop(){} function codenameTryDance(){}
 public function update(dt:Float) codenameUpdateAfterSuper(dt);
''' + body + '''}
class Main {
 static function check(b:Bool,s:String) if(!b)throw s;
 static function main() {
  for(fps in [60,240,480]) {
   var a=new Actor();a.stunned=true;
   check(a.stunned,'source stun must not depend on native miss option');
   var elapsed:Float=0;
   while(elapsed+1/fps<=5/60) {a.update(1/fps);elapsed+=1/fps;check(a.stunned,'early expiry');}
   a.update(1/fps);check(!a.stunned,'stun fails to expire');
   a.stunned=true;a.update(4/60);a.stunned=true;a.update(2/60);
   check(a.stunned,'reassignment failed to reset lease');
   a.update(4/60);check(!a.stunned,'reset lease never expires');
   a.codenameLiveDefinition=null;a.stunned=true;check(!a.stunned,'native option changed');
   OptionsHandler.options.useMissStun=true;check(a.stunned,'native stun changed');
   OptionsHandler.options.useMissStun=false;
  }
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='stun-') as folder:
            (Path(folder) / 'Main.hx').write_text(main)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
