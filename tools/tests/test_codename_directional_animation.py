"""Exercise source directional hooks, fallback and cancellation on actual methods."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DirectionalAnimationTest(unittest.TestCase):
    def test_directional_callbacks(self):
        source = (ROOT / 'source/Character.hx').read_text()
        methods = source[source.index('\t@:keep public var codenameSingAnims:'):source.index('\t@:keep public function codenameTryDance')]
        actor = '''class Character {
public var codenameRuntime:Hooks = new Hooks();
public var animation:Animations = new Animations();
public var played:Array<Dynamic>;
public function new() {}
public function codenamePlayAnim(name:String, force:Null<Bool>, context:Dynamic, reverse:Bool, frame:Int) {
 played=[name,force,context,reverse,frame];
}
''' + methods + '}\n'
        fixture = '''class Main {
 static function check(v:Bool,s:String) if (!v) throw s;
 static function main() {
  var a=new Character();
  a.codenamePlaySingAnim(1,"-missing");
  check(a.played[0]=="singDOWN" && a.played[1]==true && a.codenameRuntime.calls.join(",")=="onPlaySingAnim,playSingAnimUnsafe","suffix fallback and hook order");
  a.codenameRuntime.callback=function(name,e) {
   if(name=="onPlaySingAnim") {e.direction=2;e.suffix="-alt";e.animName="singUP-alt";e.context="MISS";e.force=false;e.reversed=true;e.frame=3;}
   else e.animName="custom";
  };
  a.codenamePlaySingAnim(0);
  check(a.played.join(",")=="custom,false,MISS,true,3","both mutable hooks must affect final animation");
  a.played=null;
  a.codenameRuntime.callback=function(name,e) e.cancel();
  a.codenamePlaySingAnim(0);
  check(a.played==null,"safe cancellation");
  a.codenameRuntime.callback=function(name,e) if(name=="playSingAnimUnsafe") e.cancel();
  a.codenamePlaySingAnim(0);
  check(a.played==null,"unsafe cancellation");
  a.codenameRuntime.callback=null;
  a.codenameSingAnims=["one","two"];
  a.codenamePlaySingAnimUnsafe(3,"-alt","SING",true,false,2);
  check(a.played[0]=="two-alt"&&a.played[4]==2,"mutable directional names and unsafe suffix");
  var e=new CodenameDirectionAnimEvent("x",0,"","SING",false,0,null);
  e.cancel(false);e.data={old:true};e.recycle("y",1,"-alt","MISS",true,4,false);
  check(!e.cancelled&&!e.stopsPropagation()&&e.data.old==null&&e.animName=="y"&&e.frame==4,"recycle state");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='directional-') as temp:
            folder = Path(temp)
            (folder / 'Character.hx').write_text(actor)
            (folder / 'Hooks.hx').write_text('''class Hooks {
public var calls:Array<String>=[];public var callback:String->CodenameDirectionAnimEvent->Void;
public function new() {}
public function event(name:String,e:CodenameDirectionAnimEvent) {calls.push(name);if(callback!=null)callback(name,e);}
}''')
            (folder / 'Animations.hx').write_text('class Animations {public function new(){} public function exists(s:String) return s=="singUP-alt";}')
            for name in ('CodenameGameEvent', 'CodenameDirectionAnimEvent'):
                (folder / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text())
            (folder / 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', temp, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
