"""Execute the owner plugin lifecycle, including duplicate names and failures."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionPluginRuntimeTest(unittest.TestCase):
    def test_plugin_order_returns_repopulation_and_owner_release(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text(r'''
class Main {
 static function check(ok:Bool, reason:String) if (!ok) throw reason;
 static function main() {
  var log:Array<String> = [];
  var errors:Array<String> = [];
  var sources:Map<String,String> = [
   'core' => 'record("core-top"); function onLoad() record("core-load"); function value(x) return x+3; function onUpdate(t) record("core-tick"); function onDestroy() record("core-destroy");',
   'owner' => 'record("owner-top"); function onLoad() record("owner-load"); function value(x) return x+7; function onUpdate(t) record("owner-tick"); function onDestroy() record("owner-destroy");',
   'broken' => 'throw "broken";',
   'recover' => 'function onLoad() throw "load error"; function value(x) return x*2;'
  ];
  var clears = 0;
  var parent = {value:42};
  var runtime = new NightmareVisionPluginRuntime('owner-a', parent, function() return [
   {scope:'plugin', name:'Utils', path:'core', relative:'core'},
   {scope:'plugin', name:'Utils', path:'owner', relative:'owner'},
   {scope:'plugin', name:'bad', path:'broken', relative:'broken'},
   {scope:'plugin', name:'recovery', path:'recover', relative:'recover'}
  ], function(path) return sources[path], function(interp, entry) {
   interp.variables.set('record', function(value:String) log.push(value));
  }, function(name, phase, error) errors.push(name+'#'+phase), function() clears++);
  runtime.populate();
  check(log.join(',')=='core-top,core-load,owner-top,owner-load', 'top-level/load order');
  check(runtime.scripts.members.length==3, 'duplicate names preserved, failed top-level removed');
  check(errors.join(',')=='bad#module,recovery#onLoad', 'attributable failures');
  check(runtime.getPlugin('Utils').interp.parent==parent, 'plugin group parent');
  check(runtime.callPluginFunc('Utils','value',[8])==11, 'real first matching return');
  check(runtime.callOnPlugin('recovery','value',[8])==16, 'callback recovery');
  check(runtime.callOnPlugin('absent','value',[])==null, 'source absent lookup');
  runtime.callOnPlugins('onUpdate',[.02]);
  check(log.slice(4).join(',')=='core-tick,owner-tick', 'both duplicate names updated');
  var previous=runtime.getPlugin('Utils');
  log=[];
  runtime.populate();
  check(previous.released && previous.interp==null, 'repopulate releases old scopes');
  check(log.join(',')=='core-destroy,owner-destroy,core-top,core-load,owner-top,owner-load','destroy before load');
  check(runtime.canReuseFor('owner-a')&&!runtime.canReuseFor('owner-b'),'owner scope');
  runtime.destroy();
  check(runtime.released && runtime.scripts.released && clears==3,'native members cleared once per lifecycle');
  runtime.destroy();
  check(clears==3 && runtime.callPluginFunc('Utils','value',[8])==null,'idempotent release');
 }
}
''')
            result = subprocess.run([
                str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work),
                '--main', 'Main', '--interp'], cwd=work, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_discovery_enumerates_only_direct_plugin_scripts_in_source_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            owner = work / 'assets/imported_mods/owner'
            for name in ('__nmv_core/scripts/plugins/Utils.hx', 'scripts/plugins/Utils.hxs',
                         'scripts/plugins/other.hscript', 'scripts/plugins/sub/ignored.hx',
                         'scripts/plugins/ignored.lua', 'scripts/normal.hx'):
                path = owner / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('function onLoad() {}')
            (work / 'Main.hx').write_text(r'''
class Main {static function main() {
 var entries=NightmareVisionScriptDiscovery.discoverPlugins('assets/imported_mods/owner');
 if(entries.length!=3) throw 'unexpected plugin count';
 if(entries[0].relative!='__nmv_core/scripts/plugins/Utils.hx') throw 'core precedence';
 if(entries[0].name!='Utils') throw 'source script basename';
 var names=[for(entry in entries) entry.name];
 if(names.indexOf('other')<0 || names.filter(function(name) return name=='Utils').length!=2) throw 'duplicates lost';
}}
''')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(work), '--run', 'Main'], cwd=work,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_driver_persists_one_owner_and_detaches_signals_when_switching(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            stubs = {
                'flixel/FlxBasic.hx': '''package flixel; class FlxBasic {
public var active:Bool=true;public function new(){} public function update(elapsed:Float):Void{} public function destroy():Void{}}''',
                'flixel/group/FlxGroup.hx': '''package flixel.group; class FlxGroup extends flixel.FlxBasic {
public var members:Array<flixel.FlxBasic>=[];public function new(){super();}
public function clear():Void members.resize(0);public function add(v:flixel.FlxBasic):flixel.FlxBasic{members.push(v);return v;}
override public function destroy():Void{for(v in members)v.destroy();clear();}}''',
                'flixel/FlxG.hx': '''package flixel;
class Signal {public var listeners:Array<Void->Void>=[];public function new(){}
public function add(f:Void->Void):Void listeners.push(f);
public function remove(f:Void->Void):Void{for(v in listeners.copy())if(Reflect.compareMethods(v,f))listeners.remove(v);}
public function dispatch():Void for(f in listeners.copy())f();}
class Plugins {public var list:Array<FlxBasic>=[];public function new(){}
public function addPlugin<T:FlxBasic>(v:T):T{list.push(v);return v;}
public function remove<T:FlxBasic>(v:T):T{list.remove(v);return v;}}
class FlxG {public static var state:Dynamic='first';public static var plugins=new Plugins();
public static var signals={preStateSwitch:new Signal(),postStateSwitch:new Signal()};}'''
            }
            for name, value in stubs.items():
                path = work / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
            for owner in ('a', 'b'):
                path = work / 'assets/imported_mods' / owner / 'scripts/plugins/probe.hx'
                path.parent.mkdir(parents=True)
                path.write_text('''function onLoad() record("load");
function onStateSwitch(state) record("pre:"+state);
function onStateSwitchPost(state) record("post:"+state);
function onUpdate(elapsed) record("tick");function onDestroy() record("destroy");''')
            (work / 'Main.hx').write_text(r'''
class Main {
 static var log:Array<String>=[];
 static function seed(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry, runtime:NightmareVisionPluginRuntime) {
  interp.variables.set('record',function(value:String)log.push(runtime.ownerRoot+':'+value));
 }
 static function main(){
  var a='assets/imported_mods/a'; var b='assets/imported_mods/b';
  var first=NightmareVisionPluginHost.mount(a,seed);
  if(first!=NightmareVisionPluginHost.mount(a,seed)||log.length!=1)throw 'same owner reloaded';
  if(flixel.FlxG.plugins.list.length!=1)throw 'duplicate native plugin';
  flixel.FlxG.signals.preStateSwitch.dispatch();flixel.FlxG.state='second';
  flixel.FlxG.signals.postStateSwitch.dispatch();NightmareVisionPluginHost.activeHost.update(.1);
  if(log.join(',')!=a+':load,'+a+':pre:first,'+a+':post:second,'+a+':tick')throw 'source callbacks';
  var second=NightmareVisionPluginHost.mount(b,seed);
  if(!first.released||second==first||flixel.FlxG.plugins.list.length!=1)throw 'owner handoff';
  if(log.slice(4).join(',')!=a+':destroy,'+b+':load')throw 'destroy before replacement';
  NightmareVisionPluginHost.releaseOtherOwner('');
  var length=log.length;flixel.FlxG.signals.postStateSwitch.dispatch();
  if(!second.released||NightmareVisionPluginHost.activeHost!=null||flixel.FlxG.plugins.list.length!=0
   ||flixel.FlxG.signals.preStateSwitch.listeners.length!=0||flixel.FlxG.signals.postStateSwitch.listeners.length!=0||log.length!=length)throw 'native cleanup';
 }
}
''')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work),
                                     '--run', 'Main'], cwd=work, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
