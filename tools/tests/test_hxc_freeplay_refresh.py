"""Live HXC refresh preserves real interpreter state and blocks parked proxies."""
import os,subprocess,tempfile,unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND,TEST_TMP
ROOT=Path(__file__).resolve().parents[2]
class HxcFreeplayRefreshTest(unittest.TestCase):
 def run_haxe(self,body):
  with tempfile.TemporaryDirectory(dir=TEST_TMP if os.environ.get('CAMMIE_TEST_TMP') else None) as tmp:
   base=Path(tmp);source=(ROOT/'source/HxcFreeplayRuntime.hx').read_text(encoding='utf-8')
   start=source.index('\tfunction seedInterpreter(');brace=source.index('{',start);depth=1;end=brace+1
   while depth:
    if source[end]=='{':depth+=1
    elif source[end]=='}':depth-=1
    end+=1
   source=source[:brace]+'''{
    interp.variables.set('record',function(message:String) owner.events.push(scope.path+':'+message));
    interp.variables.set('sibling',function(name:String) return moduleProxy(scope,name));
   }'''+source[end:]
   (base/'HxcFreeplayRuntime.hx').write_text(source,encoding='utf-8')
   stubs={
   'PluginManager.hx':'''typedef HscriptGlobals=Dynamic;class PluginManager {public static function createSimpleInterp():hscript.Interp return new hscript.Interp();public static function addVarsToInterp<T:hscript.Interp>(i:T):T return i;}''',
   'CodenameScriptInterp.hx':'''class CodenameScriptInterp extends hscript.Interp {public function new(p:CodenamePaths){super();}public function bindScriptObject(o:Dynamic):Void{}public function tweenFacade():Dynamic return {};public function release():Void variables.clear();public function setPaused(v:Bool):Void{}}''',
   'CodenamePaths.hx':'''class CodenamePaths {public function new(p:String){}}''',
   'ImportedMenuEntry.hx':'''class ImportedMenuEntry {public static function requiredOwnerRoots(r:String):Array<String>return [r];}''',
   'ImportRefreshManager.hx':'''class ImportRefreshManager {public static function tryAcquireRuntimeOwnerLease(r:Array<String>):String return 'lease';public static function releaseRuntimeOwnerLease(t:String):Void{}}''',
   'hscript/ParserEx.hx':'''package hscript;class ParserEx extends Parser {public function new(){super();allowTypes=true;}}''',
   'FreeplayState.hx':'''class FreeplayState {public static var currentSongList:Array<{name:String}>=[];public var events:Array<String>=[];public function new(){}public function hxcPushAssetScope(s:String):String return '';public function hxcPopAssetScope(s:String):Void {}}''',
   'RuntimeSmokeHarness.hx':'''class RuntimeSmokeHarness {public static function enabled():Bool return false;public static function profileSection(s:String,t:Float):Void {}}''',
   'EngineCompat.hx':'''class EngineCompat {public static function callbackNames(s:String):Array<String> return [s];public static function callbackArguments(a:String,b:String,args:Array<Dynamic>,c:Bool):Array<Dynamic> return args;}''',
   'FNFAssets.hx':'''class FNFAssets {public static var reads:Map<String,Int>=[];public static function exists(p:String):Bool return sys.FileSystem.exists(p);public static function getText(p:String):String {reads.set(p,reads.exists(p)?reads.get(p)+1:1);return sys.io.File.getContent(p);}}''',
   'CompatScriptManifest.hx':'''typedef Entry={var path:String;}typedef Manifest={var roots:Array<Entry>;}class CompatScriptManifest {public static inline var FILE_NAME='compatScripts.json';public static function parse(s:String):Manifest return cast haxe.Json.parse(s);public static function rootsInPrecedence(m:Manifest):Array<Entry> return m.roots;}''',
   'HxcScriptDiscovery.hx':'''typedef Plan={var families:Map<String,Array<String>>;}class HxcScriptDiscovery {public static var discovery:Map<String,Int>=[];public static function stem(p:String):String return haxe.io.Path.withoutExtension(haxe.io.Path.withoutDirectory(p));public static function normalizeToken(s:String):String return s==null?'':s.toLowerCase();public static function discoverRoot(root:String,song:String):Plan {discovery.set(root,discovery.exists(root)?discovery.get(root)+1:1);var paths:Array<String>=[];for(n in sys.FileSystem.readDirectory(root))if(StringTools.endsWith(n,'.hxc'))paths.push(root+'/'+n);paths.sort(Reflect.compare);var families:Map<String,Array<String>>=[];families.set('module',paths);return {families:families};}}''',
   'HxcCompat.hx':'''typedef Analysis={var kind:String;var moduleInitializationSafe:Bool;var generatedHscript:String;var identifier:String;var className:String;var callbackAdapters:Array<{safe:Bool,canonicalName:String}>;}class HxcCompat {public static var analyzed:Map<String,Int>=[];public static function analyze(s:String,path:String):Analysis {analyzed.set(path,analyzed.exists(path)?analyzed.get(path)+1:1);var raw:Dynamic=haxe.Json.parse(s);return {kind:'module',moduleInitializationSafe:raw.safe!=false,generatedHscript:raw.code,identifier:'',className:'',callbackAdapters:[{safe:true,canonicalName:'update'},{safe:true,canonicalName:'subStateOpenEnd'}]};}}'''}
   for relative,text in stubs.items():
    target=base/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
   program=r'''import sys.FileSystem;import sys.io.File;@:access(HxcFreeplayRuntime) class Main {
    static function check(v:Bool,s:String){if(!v)throw s;}
    static function module(root:String,name:String,code:String,safe:Bool=true){FileSystem.createDirectory(root);File.saveContent(root+'/'+name+'.hxc',haxe.Json.stringify({code:code,safe:safe}));}
    static function song(name:String,roots:Array<String>){var folder='assets/data/'+name;FileSystem.createDirectory(folder);File.saveContent(folder+'/compatScripts.json',haxe.Json.stringify({roots:[for(root in roots){path:root}]}));FreeplayState.currentSongList.push({name:name});}
    static function main(){Sys.setCwd(Sys.args()[0]);var owner=new FreeplayState();'''+body+'}}'
   (base/'Main.hx').write_text(program)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'source'),'-cp',tmp,'--run','Main',tmp],cwd=ROOT,capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_changed_and_new_code_wait_for_natural_entry(self):
  self.run_haxe(r'''var root='assets/imported_mods/a';song('one',[root]);
   module(root,'Shared',"counter=0; function update(p){counter++;} function subStateOpenEnd(p){record('init');}");
   var runtime=new HxcFreeplayRuntime(owner);var scope=runtime.scopes[0];var interp=scope.interp;
   var proxy=HxcFreeplayRuntime.moduleProxyForRoot(root,'Shared');runtime.dispatch('update',{capsule:{name:'one'}});
   module(root,'Shared',"counter=20; function update(p){counter++;}");module(root,'New',"counter=3; function update(p){counter++;}");
   var discoveries=HxcScriptDiscovery.discovery.get(root);runtime.refresh({capsule:{name:'one'}});
   check(runtime.scopes[0]==scope && runtime.scopes[0].interp==interp && proxy.scriptGet('counter')==1,'module snapshot replaced');
   check(owner.events.length==0 && HxcCompat.analyzed.get(root+'/Shared.hxc')==1 && HxcScriptDiscovery.discovery.get(root)==discoveries,'live code discovered/reexecuted');
   check(HxcFreeplayRuntime.moduleProxyForRoot(root,'New')==null,'new code loaded in existing menu');
   runtime.dispatch('update',{capsule:{name:'one'}});check(proxy.scriptGet('counter')==2,'ready old snapshot did not resume');
   runtime.dispose();var next=new HxcFreeplayRuntime(owner);
   check(HxcFreeplayRuntime.moduleProxyForRoot(root,'Shared').scriptGet('counter')==20 && HxcFreeplayRuntime.moduleProxyForRoot(root,'New').scriptGet('counter')==3,'natural entry failed to load current source');''')
 def test_pending_parking_keeps_variables_and_skips_reads(self):
  self.run_haxe(r'''var root='assets/imported_mods/a';song('one',[root]);module(root,'Shared',"counter=0; function update(p){counter++;}");
   var ready=true;var runtime=new HxcFreeplayRuntime(owner,function(r)return r!=root||ready,function(s)return ready);
   var scope=runtime.scopes[0];var proxy=HxcFreeplayRuntime.moduleProxyForRoot(root,'Shared');
   var held=scope.interp.variables.get('update');ready=false;runtime.setRootReadiness(function(r)return r!=root||ready);
   var reads=FNFAssets.reads.get('assets/data/one/compatScripts.json');var discoveries=HxcScriptDiscovery.discovery.get(root);
   module(root,'Shared',"counter=7; function update(p){counter++;}");runtime.refresh();runtime.dispatch('update',{capsule:{name:'one'}});
   check(scope.interp.variables.get('counter')==0 && proxy.scriptGet('counter')==null,'pending callbacks/proxies ran');
   check(FNFAssets.reads.get('assets/data/one/compatScripts.json')==reads && HxcScriptDiscovery.discovery.get(root)==discoveries,'pending owner read');
   check(scope.interp.variables.get('update')==held,'pending interpreter variables cleared');
   ready=true;runtime.setRootReadiness(function(r)return r!=root||ready);check(proxy.scriptGet('counter')==null,'unparked before routing adoption');
   runtime.refresh();check(runtime.scopes[0]==scope && proxy.scriptGet('counter')==0,'snapshot replaced on resumption');''')
 def test_manifest_association_and_precedence_update(self):
  self.run_haxe(r'''var a='assets/imported_mods/a';var b='assets/imported_mods/b';song('one',[a,b]);
   module(a,'Shared',"count=0; function update(p){count++;}");module(b,'Shared',"count=0; function update(p){count++;}");
   var runtime=new HxcFreeplayRuntime(owner);runtime.dispatch('update',{capsule:{name:'one'}});
   var pa=HxcFreeplayRuntime.moduleProxyForRoot(a,'Shared');var pb=HxcFreeplayRuntime.moduleProxyForRoot(b,'Shared');
   check(pa.scriptGet('count')==1 && pb.scriptGet('count')==0,'initial priority wrong');
   FreeplayState.currentSongList=[];song('one',[b,a]);runtime.refresh();runtime.dispatch('update',{capsule:{name:'one'}});
   check(pa.scriptGet('count')==1 && pb.scriptGet('count')==1,'new precedence ignored');
   FreeplayState.currentSongList=[];song('two',[a]);runtime.refresh();runtime.dispatch('update',{capsule:{name:'one'}});
   check(pa.scriptGet('count')==1,'old song dispatched');runtime.dispatch('update',{capsule:{name:'two'}});
   check(pa.scriptGet('count')==2 && pb.scriptGet('count')==null,'association not updated or absent root active');''')
 def test_parked_primary_blocks_fallback_removed_owner_disposes_resources(self):
  self.run_haxe(r'''var a='assets/imported_mods/a';var b='assets/imported_mods/b';song('one',[a,b]);
   module(a,'Shared',"count=0; function update(p){count++;}");module(b,'Shared',"count=0; function update(p){count++;}");
   var ready=true;var known=true;var runtime=new HxcFreeplayRuntime(owner,function(r)return r!=a||ready,null,function(r)return r!=a||known);
   var scope=runtime.scopes[0];var old=HxcFreeplayRuntime.moduleProxyForRoot(a,'Shared');var fallback=HxcFreeplayRuntime.moduleProxyForRoot(b,'Shared');
   ready=false;runtime.setRootReadiness(function(r)return r!=a||ready);runtime.refresh();runtime.dispatch('update',{capsule:{name:'one'}});
   check(fallback.scriptGet('count')==0 && old.scriptGet('count')==null,'pending primary leaked to fallback');
   known=false;FreeplayState.currentSongList=[];song('one',[b]);runtime.refresh();runtime.dispatch('update',{capsule:{name:'one'}});
   check(fallback.scriptGet('count')==1 && old.scriptGet('count')==null && scope.interp==null,'removed owner retained interpreter or still dispatched');
   module(a,'Shared',"count=9; function update(p){count++;}");known=true;ready=true;FreeplayState.currentSongList=[];song('one',[a,b]);runtime.refresh();
   check(HxcFreeplayRuntime.moduleProxyForRoot(a,'Shared')==null && scope.interp==null,'re-added owner revived retired snapshot');
   runtime.dispose();check(scope.interp==null && fallback.scriptGet('count')==null,'disposal retained interpreter');''')
 def test_rejected_source_also_waits_for_natural_entry(self):
  self.run_haxe(r'''var root='assets/imported_mods/a';song('one',[root]);module(root,'Unsafe',"count=0; function update(p){count++;}",false);
   var runtime=new HxcFreeplayRuntime(owner);module(root,'Unsafe',"count=8; function update(p){count++;}",true);runtime.refresh();
   check(HxcFreeplayRuntime.moduleProxyForRoot(root,'Unsafe')==null && HxcCompat.analyzed.get(root+'/Unsafe.hxc')==1,'rejected source retried in current menu');
   runtime.dispose();var next=new HxcFreeplayRuntime(owner);check(HxcFreeplayRuntime.moduleProxyForRoot(root,'Unsafe').scriptGet('count')==8,'new entry kept rejected snapshot');''')
if __name__=='__main__':unittest.main()
