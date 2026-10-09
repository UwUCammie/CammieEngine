"""Execute pinned historical broadcast and hit notification contracts."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'


class HistoricalHitNotificationTest(unittest.TestCase):
    def test_broadcast_values_filtering_and_global_then_attached_hit(self):
        donor = ROOT.parent / 'fnf_sources/NightmareVision'
        if not donor.is_dir():
            self.skipTest('pinned historical source unavailable')
        source = subprocess.check_output(['git', 'show', REV + ':source/meta/states/PlayState.hx'], cwd=donor, text=True)
        broadcast = method(source, 'public function callOnScripts(')
        hit = method(source, 'function goodNoteHit(')
        hit = hit[hit.index('var luaArgs:Array<Dynamic>'):hit.index('if (!note.isSustainNote)', hit.index('var luaArgs:Array<Dynamic>'))]
        hit = hit.replace("'goodNoteHit'", 'callback').replace('"goodNoteHit"', 'callback')
        miss = method(source, 'function noteMiss(')
        miss = miss[miss.index("callOnLuas('noteMiss'"):].rstrip()[:-1]
        miss = miss.replace('daNote', 'note')
        fixture = r"""
class Globals {public static var Function_Continue=0;public static var Function_Stop=1;public static var Function_Halt=2;}
class Entry {
 public var scriptName:String;public var value:Dynamic;public var log:Array<String>;
 public function new(n:String,v:Dynamic,l:Array<String>){scriptName=n;value=v;log=l;}
 public function call(n:String,a:Array<Dynamic>):Dynamic {log.push(scriptName);return value;}
}
class Reference {
 public var funkyScripts:Array<Dynamic>=[];
 public var notetypeScripts:Map<String,Dynamic>=[];
 public var eventScripts:Map<String,Dynamic>=[];
 public var notes:Dynamic;
 public var lua:(String,Array<Dynamic>)->Dynamic;
 public var hscript:(String,Array<Dynamic>)->Dynamic;
 public function new(){}
 __BROADCAST__
 function callOnLuas(n:String,a:Array<Dynamic>):Dynamic return lua(n,a);
 function callOnHScripts(n:String,a:Array<Dynamic>):Dynamic return hscript(n,a);
 function callScript(s:NightmareVisionScriptModule,n:String,a:Array<Dynamic>):Dynamic return s.callValue(n,a);
 public function notify(note:Dynamic,callback:String):Void {if(callback=="noteMiss"){__MISS__}else{__HIT__}}
}
class Main {
 static function check(ok:Bool,m:String):Void if(!ok)throw m;
 static function main(){
  var values:Array<Dynamic>=[0,1,2,null,'text',false,0.75,[3],{x:1}];
  for(a in values) for(b in values) for(c in values) for(ignore in [false,true]) {
   var ref=new Reference();ref.notetypeScripts.set('type',{});ref.eventScripts.set('event',{});
   var expected:Array<String>=[],actual:Array<String>=[];
   var make=function(log:Array<String>):Array<Dynamic> return [new Entry('one',a,log),new Entry('type',2,log),new Entry('two',b,log),new Entry('event',2,log),new Entry('three',c,log)];
   var result=ref.callOnScripts('hit',[],ignore,[],make(expected));
   var got=NightmareVisionScriptBroadcast.call(make(actual),function(e:Dynamic)return e.call('hit',[]),ignore,true,
    function(e:Dynamic)return ref.notetypeScripts.exists(e.scriptName)||ref.eventScripts.exists(e.scriptName));
   check(haxe.Json.stringify(result)==haxe.Json.stringify(got)&&actual.join(',')==expected.join(','),'pinned broadcast return/order');
  }
  var errors:Array<String>=[];
  var plan:NightmareVisionScriptDiscovery.NightmareVisionScriptPlan={root:'owner',baseAssetsRoot:'',song:'fixture',stage:'',coverageNotes:[],scripts:[]};
  var scripts=new NightmareVisionGameplayScripts({},plan,function(p)return '',function(i,e,a){},function(n,p,e)errors.push(Std.string(e)));
  var registry:Map<String,NightmareVisionScriptModule>=[];scripts.legacyNoteRegistry=function()return registry;
  var global=scripts.group.loadSource('global',"function goodNoteHit(n){n.events.push('global');n.noteScript=replacement;return 2;} function noteMiss(n){return goodNoteHit(n);} function opponentNoteHit(n){return goodNoteHit(n);}");
  var original=scripts.group.loadSource('original',"function goodNoteHit(n){n.events.push('WRONG-original');} function noteMiss(n){return goodNoteHit(n);} function opponentNoteHit(n){goodNoteHit(n);}");
  var attached=scripts.group.loadSource('replacement',"function goodNoteHit(n){n.events.push('attached');return 1;} function noteMiss(n){return goodNoteHit(n);} function opponentNoteHit(n){return goodNoteHit(n);}");
  var event=scripts.group.loadSource('event',"function goodNoteHit(n){n.events.push('WRONG-event');} function noteMiss(n){return goodNoteHit(n);} function opponentNoteHit(n){goodNoteHit(n);}");
  var later=scripts.group.loadSource('later',"function goodNoteHit(n){n.events.push('WRONG-after-halt');} function noteMiss(n){return goodNoteHit(n);} function opponentNoteHit(n){goodNoteHit(n);}");
  global.set('replacement',attached);registry.set('original',original);registry.set('replacement',attached);scripts.eventGroup.addScript(event);
  var runtime=new NightmareVisionNoteTypeRuntime(scripts);runtime.legacyNoteScripts=true;
  for(callback in ['goodNoteHit','opponentNoteHit','noteMiss']) for(ret in values) for(clear in [false,true]) {
   var actual:Dynamic={noteData:-3,noteType:'original',isSustainNote:true,ID:91,noteScript:original,events:[]};
   var expected:Dynamic={noteData:-3,noteType:'original',isSustainNote:true,ID:91,noteScript:original,events:[]};
   global.set('replacement',clear?null:attached);
   var lua=function(note:Dynamic):(String,Array<Dynamic>)->Dynamic return function(n,args){
    check(n==callback&&haxe.Json.stringify(args)==(callback=='noteMiss'?'[1,-3,"original",true,91]':'[1,3,"original",true,91]'),'five scalar Lua arguments');
    note.events.push('lua');note.noteType='changed-by-lua';return ret;
   };
   var hs=function(n:String,args:Array<Dynamic>):Dynamic {
    check(n==callback&&args.length==1,'one live HScript argument');return scripts.callHistorical(n,args);
   };
   var reference=new Reference();reference.notes={members:[null,expected]};reference.lua=lua(expected);reference.hscript=hs;
   reference.notify(expected,callback);
   runtime.legacyHit(actual,callback,1,lua(actual),hs);
   check(actual.events.join(',')==expected.events.join(',')&&actual.events.join(',')==(clear?'lua,global':'lua,global,attached'),
    'source global order, ignored family returns and live attachment');
  }
  // The historical filter reads current maps at each invocation, including changes mid-broadcast.
  global.set('replacement',attached);
  scripts.group.removeScript(later);
  var mutator=scripts.group.loadSource('mutator',"function probe(){registry.set('later',null);return 'historical-result';}",function(i)i.variables.set('registry',registry));
  later=scripts.group.loadSource('later',"function probe(){return 'WRONG-late-filter';}");
  check(scripts.callHistorical('probe',[])=='historical-result','live exclusion by map key, even when value null');
  check(scripts.call('probe',[])==0,'modern group still ignores non-Int values');
  check(errors.length==0,errors.join(','));scripts.destroy();
 }
}
""".replace('__BROADCAST__', broadcast).replace('__HIT__', hit).replace('__MISS__', miss)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work), '-main', 'Main', '--interp'], cwd=ROOT, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
