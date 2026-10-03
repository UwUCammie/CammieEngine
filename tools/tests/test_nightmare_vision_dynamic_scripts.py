"""Execute source-shaped dynamic script loading, recursive dedup and lifetime."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionDynamicScriptsTest(unittest.TestCase):
    def test_recursive_loader_main_group_order_owner_and_recovery(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(r'''
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
class Main {
 static function main() {
  var errors:Array<String> = [];
  var calls:Array<String> = [];
  var sources:Map<String,String> = [
   'owner/scripts/start.hx' => 'public var shared=5; function onLoad(){record("start");initScript("helper");initScript("helper");} function onCreatePost(){record("startPost");}',
   'owner/helper.hx' => 'function onLoad(){record("helper:"+shared);initScript("helper");initScript("start");} function onCreatePost(){record("helperPost");} function onDestroy(){record("destroy");}',
   'owner/events/e.hx' => 'function onTrigger(a,b){initScript("eventHelper");}',
   'owner/eventHelper.hx' => 'function onLoad(){record("eventHelper:"+shared);}',
   'owner/bad.hx' => 'throw "broken";'
  ];
  var entries:Array<NightmareVisionScriptEntry> = [{scope:'global',name:'start',path:'owner/scripts/start.hx',relative:'scripts/start.hx'}, {scope:'event',name:'e',path:'owner/events/e.hx',relative:'events/e.hx'}];
  var resolve = function(path:String):NightmareVisionScriptEntry {
   if(path=="../foreign")throw 'escaped';
   var rel = path == 'start' ? 'scripts/start.hx' : path+'.hx';
   if(!sources.exists('owner/'+rel))return null;
   return {scope:'dynamic',name:path,path:'owner/'+rel,relative:rel};
  };
  var host = new NightmareVisionGameplayScripts({}, {root:'owner',baseAssetsRoot:'',song:'song',stage:'stage',scripts:entries,coverageNotes:[]},
   function(path)return sources.get(path),
   function(interp,entry,actor){interp.variables.set('record',function(s:String)calls.push(s));},
   function(name,phase,error)errors.push(name+':'+phase), null,resolve);
  host.loadScope('global');host.loadScope('global');
  if(calls.join(',')!='start,helper:5'||host.group.members.length!=2)throw calls;
  host.call('onCreatePost');
  if(calls.join(',')!='start,helper:5,startPost,helperPost')throw 'lifecycle '+calls;
  host.callEvent('e','onTrigger',['','']);
  if(calls[calls.length-1]!='eventHelper:5'||host.eventGroup.members.length!=1)throw 'wrong event dynamic group';
  host.loadDynamic('missing');host.loadDynamic('../foreign');host.loadDynamic('bad');host.loadDynamic('eventHelper');
  if(errors.join(',')!='../foreign:initScript,bad.hx:module'||host.group.members.length!=4)throw errors;
  host.destroy();host.loadDynamic('helper');
  if(calls[calls.length-1]!='destroy'||!host.group.released)throw 'destroy';
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work), '--main', 'Main', '--interp'],
                cwd=work, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
