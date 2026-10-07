"""Real source modifier instances and owner-local Iris callback contracts."""
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
import subprocess
import tempfile
import unittest
ROOT = FixturePath(__file__).resolve().parents[2]

class CustomModifierTest(unittest.TestCase):
    def run_haxe(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work=Path(directory)
            write_flixel_point_stub(work)
            (work/"HxcCompatRuntime.hx").write_text("class HxcCompatRuntime { public static function getZIndex(o:Dynamic):Int return 0; public static function setZIndex(o:Dynamic,v:Dynamic,?op:String):Dynamic return v; }",encoding="utf-8")
            (work/"Main.hx").write_text(source,encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT/"source"),"-cp",str(ROOT/".haxelib/hscript-iris/1,1,3"),"-cp",str(ROOT/".haxelib/flixel/6,1,2"),"-cp",directory,"--run","Main"],cwd=work,capture_output=True,text=True,timeout=40)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_identity_activation_collisions_dimensions_timeline_and_destroy(self):
        self.run_haxe(r'''
import NightmareVisionModifier.ModifierType;
class Custom extends NightmareVisionModifier {
 public var name:String; public var type:ModifierType; public var destroys:Int=0; public var updates:Int=0; public var throwing:Bool=false;
 public function new(m:NightmareVisionModManager,name:String,type:ModifierType) { super(m);this.name=name;this.type=type; }
 override public function getName():String return name;
 override public function getModType():ModifierType return type;
 override public function shouldExecute(p:Int,v:Float):Bool return v>0.5;
 override public function getSubmods():Array<String> return ['threshold-child'];
 override public function update(e:Float):Void updates++;
 override public function destroy():Void { destroys++;if(throwing) throw 'release boom'; }
}
class Main {
 static function ok(v:Bool,m:String):Void if(!v) throw m;
 static function main() {
  var m=new NightmareVisionModManager(null,3,1,false);var diagnostics=[];
  m.reportModifierError=(n,p,e)->diagnostics.push(n+':'+p);
  ok(m.register.keys().hasNext()==false,'not empty');
  var c=new Custom(m,'custom',NOTE_MOD);m.quickRegister(c);
  ok(m.get('custom')==c && m.get('custom')==m.get('custom'),'instance identity');
  ok(c.submods.exists('threshold-child') && m.get('threshold-child')==c.submods.get('threshold-child'),'child ownership');
  m.setValue('custom',0.4);ok(m.activeMods[0].indexOf('custom')<0,'predicate threshold');
  m.setValue('custom',0.8);ok(m.activeMods[0].indexOf('custom')>=0,'nonzero threshold activation');
  m.setValue('threshold-child',0.9);m.setValue('custom',0);ok(m.activeMods[0].indexOf('custom')>=0,'child keeps parent');
  m.setValue('threshold-child',0);ok(m.activeMods[0].indexOf('custom')<0,'child clears parent');
  var registry=m.registry;var timeline=m.modifierTimeline;m.configureDimensions(1,3);
  ok(m.registry==registry&&m.modifierTimeline==timeline&&c.percents.length==3,'dimension identity');
  m.queueSet(1,'custom',0.7,2);m.updateTimeline(1);ok(c.getValue(2)==0.7&&m.activeMods[2].indexOf('custom')>=0,'custom timeline bridge');
  m.registerMod('alias',c,false);m.setValue('alias',0.8,0);ok(m.get('alias')==c,'alias identity');
  var dup=new Custom(m,'custom',NOTE_MOD);m.quickRegister(dup);ok(m.get('custom')==c,'same kind rejection');
  var cross=new Custom(m,'custom',MISC_MOD);m.quickRegister(cross);ok(m.get('custom')==cross&&m.notemodRegister.get('custom')==c,'cross kind maps');
  c.active=true;m.update(0.1);ok(c.updates==0,'NOTE doesUpdate false');cross.active=true;m.update(0.1);ok(cross.updates==1,'misc active update');
  var before=new Custom(m,'reverse',MISC_MOD);m.quickRegister(before);m.registerEssentialModifiers();
  ok(m.notemodRegister.exists('reverse')&&m.miscmodRegister.get('reverse')==before&&m.get('reverse')!=before,'builtin cross-kind collision');
  ok(m.get('reverse').submods.exists('split')&&m.get('split').parent==m.get('reverse'),'builtin children constructed before registration');
  c.throwing=true;var failed=false;try m.destroy() catch(e:Dynamic) failed=true;
  ok(failed&&c.destroys==1&&cross.destroys==1&&before.destroys==1,'all cleanup attempted');
  ok(m.destroyed&&m.modArray.length==0&&m.registry.executionNames==null&&m.loadModifierScript==null,'cleanup detached');
  m.destroy();ok(c.destroys==1,'idempotent teardown');
  var second=new NightmareVisionModManager(null,4,2,false);
  var customReverse=new Custom(second,'reverse',NOTE_MOD);second.quickRegister(customReverse);second.registerEssentialModifiers();
  ok(second.get('reverse')==customReverse&&!second.register.exists('split'),'same-kind builtin rejects children');second.destroy();
 }
}
''')

    def test_real_iris_metadata_callbacks_vectors_errors_duplicates_and_receiver(self):
        self.run_haxe(r'''
import nightmarevision.modchart.NightmareVisionModchartVector;
class Main {
 static function ok(v:Bool,m:String):Void if(!v) throw m;
 static function main() {
  var m=new NightmareVisionModManager(null,4,2,false);var errors:Array<String>=[];var records:Array<String>=[];
  var shared:Map<String,Dynamic>=['sharedCount'=>0];
  m.reportModifierError=(n,p,e)->errors.push(n+':'+p);
  m.loadModifierScript=function(mod,name) {
   if(name=='missing') return null;
   var i=new NightmareVisionScriptInterp(mod,shared);NightmareVisionModifierBindings.install(i);
   i.variables.set('record',(s:String)->records.push(s));
   var module=new NightmareVisionScriptModule(name,i,m.reportModifierError);
   var program=new NightmareVisionScriptParser().parseString('
    import funkin.backend.math.Vector3;
    function getName() return "script-note";
    function getModType() return NOTE_MOD;
    function getOrder() return PRE_REVERSE;
    function doesUpdate() return true;
    function getSubmods() return ["script-child"];
    function onLoad(manager,name,prefix,parent) { record(name+":"+prefix+":"+(this.modMgr==manager)+":"+this.submods.exists("script-child")); }
    function getPos(time,diff,tDiff,beat,pos,data,player,obj) { obj.touched=time; return Vector3.get(pos.x+this.getValue(player),diff,tDiff); }
    function updateNote(beat,obj,pos,player) { obj.alpha=0.25; record("note:"+(this==mod)); }
    function updateReceptor(beat,obj,pos,player) record("receptor");
    function updateNoteSplash(beat,obj,pos,player) record("splash");
    function updateSustainSplash(beat,obj,pos,player) record("hold");
    function onUpdate(elapsed) { sharedCount++; throw "update boom"; }
    function destroy() record("destroy:"+this.getName());
   ');
   i.variables.set('mod',mod);if(!module.executeProgram(program)) throw 'module load';return module;
  };
  var mod=new NightmareVisionScriptedModifier(m,'real','pre-');m.quickRegister(mod);
  ok(records[0]=='real:pre-:true:true'&&mod.getName()=='script-note'&&mod.getOrder()==-3,'metadata/load ordering');
  m.setValue('script-note',2,0);var native:Dynamic={alpha:1.0,touched:0.0};var p=new NightmareVisionModchartVector(4,5,6);
  var entry=m.registry.executionEntry('script-note');var returned=entry.getPosition(123,8,9,1,p,2,0,native);
  ok(returned!=p&&returned.x==6&&returned.y==8&&returned.z==9&&native.touched==123,'position args/native/replacement');
  for(kind in ['note','receptor','noteSplash','sustainSplash']) entry.updateObject(1,native,returned,0,kind);
  ok(native.alpha==0.25&&records.slice(1).join(',')=='note:true,receptor,splash,hold','typed object callbacks');
  mod.script.interp.variables.set('this','prior');entry.updateObject(1,native,p,0,'note');ok(mod.script.interp.variables.get('this')=='prior','receiver restore');
  m.update(0.1);ok(errors.length==0,'active independent gate');mod.active=true;m.update(0.1);m.update(0.1);
  ok(errors.length==2&&shared.get('sharedCount')==2&&mod.script.interp.variables.get('this')=='prior','error ownership/continued update/shared state');
  var duplicate=new NightmareVisionScriptedModifier(m,'real');m.quickRegister(duplicate);ok(m.get('script-note')==mod,'duplicate retains original');
  var missing=new NightmareVisionScriptedModifier(m,'missing');m.quickRegister(missing);ok(m.get('missing')==missing&&!missing.doesUpdate(),'missing fallback');
  var module=mod.script;var other=duplicate.script;m.destroy();
  ok(module.released&&other.released&&mod.script==null&&duplicate.script==null,'registered/rejected script release');
  ok(records.filter(s->s=='destroy:script-note').length==2,'exact destroy callbacks');
  returned.put();var recycled=NightmareVisionModchartVector.get(1,2,3);ok(recycled==returned,'pooling');
  ok(NightmareVisionModchartVector.X_AXIS.length==1&&recycled.clone().equals(recycled),'vector API');
  ok(!recycled.nearEquals(new NightmareVisionModchartVector(2,2,3),1),'strict nearEquals');
 }
}
''')

    def test_owner_constructor_and_recursive_source_manager_path(self):
        self.run_haxe(r'''
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
class Host {
 public var manager:NightmareVisionModManager;
 public function new() {}
 public function createNightmareVisionSourceModManager(args:Array<Dynamic>):Dynamic {
  if(args.length!=1 || args[0]!=this) throw 'wrong owner';manager=new NightmareVisionModManager(null,4,2,false);return manager;
 }
}
class Main {
 static function ok(v:Bool,m:String):Void if(!v) throw m;
 static function main() {
  var host=new Host();var live=true;
  var i=new NightmareVisionScriptInterp();NightmareVisionModifierBindings.install(i,'owner',owner->live?host:null);
  i.variables.set('game',host);i.variables.set('made',null);
  i.execute(new NightmareVisionScriptParser().parseString('import funkin.game.modchart.ModManager; made=new ModManager(game);'));
  ok(i.variables.get('made')==host.manager && !host.manager.register.keys().hasNext(),'source constructor signature/identity');
  live=false;var failed=false;try i.execute(new NightmareVisionScriptParser().parseString('new ModManager(game);')) catch(e:Dynamic) failed=true;
  ok(failed,'inactive owner rejected');
  var m=host.manager;m.renderContext=()->new NightmareVisionModchartContext(1280,720,4,112);
  m.sourceRenderer=new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(m.registry));m.registerEssentialModifiers();
  var native:Dynamic={active:true,ID:2,width:40.0,height:40.0,scale:{x:1.,y:1.},x:0.,y:0.,angle:0.,alpha:1.};
  var p=new NightmareVisionModchartVector(9,8,7);var result=m.getPos(123,30,50,1,2,0,native,['reverse'],p);
  ok(result==p&&result.x==m.getBaseX(2,0)&&result.y==136,'excluded source path/base geometry');
  ok(m.getVisPos(100,200,2)==90&&m.getBaseVisPosD(100,2)==90,'visual helper formulas');
  native.active=false;p.setTo(9,8,7);ok(m.getPos(123,30,50,1,2,0,native,null,p)==p&&p.x==9&&p.y==8,'inactive supplied vector preserved');
  native.active=true;p.setTo(300,200,0);m.updateObject(1,native,p,0);ok(native.x==280&&native.y==180,'explicit object update center');
  m.destroy();ok(m.sourceRenderer==null&&m.renderContext==null,'owner render delegation teardown');i.release();
 }
}
''')

    def test_actual_owner_loader_shares_state_and_fails_malformed_module(self):
        play=(ROOT/"source/PlayState.hx").read_text(encoding="utf-8")
        body=method(play,"function loadNightmareVisionModifierScript(mod:NightmareVisionModifier, name:String)")
        self.run_haxe(r'''
import sys.io.File;
class Host {
 public var nightmareVisionPaths:Dynamic;
 public var nightmareVisionScripts:Dynamic;
 public var errors:Array<String>=[];
 public function new() {
  var group=new NightmareVisionScriptGroup(this,(n,p,e)->errors.push(n+":"+p));
  group.sharedFields.set('ownedEvidence',{count:0});nightmareVisionScripts={group:group};
  nightmareVisionPaths={resolveScript:function(path:String):Dynamic return {path:path.substr(path.lastIndexOf('/')+1)+'.hx'}};
 }
 function reportNightmareVisionModifierError(n:String,p:String,e:Dynamic):Void errors.push(n+":"+p);
 function seedNightmareVision(i:NightmareVisionScriptInterp,entry:Dynamic,actor:Dynamic):Void NightmareVisionModifierBindings.install(i);
 __METHOD__
 public function loader(mod:NightmareVisionModifier,name:String):NightmareVisionScriptModule return loadNightmareVisionModifierScript(mod,name);
}
class Main {
 static function ok(v:Bool,m:String):Void if(!v) throw m;
 static function main() {
  File.saveContent('valid.hx','function getName() return "owned"; function onLoad(m,n,p,parent) { ownedEvidence.count++; }');
  File.saveContent('broken.hx','function broken( {');
  var h=new Host();var m=new NightmareVisionModManager(null,4,2,false);m.loadModifierScript=h.loader;
  var mod=new NightmareVisionScriptedModifier(m,'valid');m.quickRegister(mod);
  ok(mod.script.interp.parent==mod&&mod.script.interp.sharedFields==h.nightmareVisionScripts.group.sharedFields,'loader actual receiver/shareables');
  ok(h.nightmareVisionScripts.group.sharedFields.get('ownedEvidence').count==1,'initialized owner evidence before onLoad');
  var broken=new NightmareVisionScriptedModifier(m,'broken');m.quickRegister(broken);
  ok(broken.script==null&&h.errors.indexOf('broken:parse')>=0&&m.get('broken')==broken,'malformed attributable fallback');
  m.destroy();sys.FileSystem.deleteFile('valid.hx');sys.FileSystem.deleteFile('broken.hx');
 }
}
'''.replace('__METHOD__',body))

    def test_source_registration_gate_and_fixed_update_phase(self):
        play=(ROOT/"source/PlayState.hx").read_text(encoding="utf-8")
        update=method(play,"override public function update(elapsed:Float)")
        begin=update.index('if (modifiersRegistered && modManager != null)')
        tail=update[begin:update.index('// Drain the ready queue',begin)]
        self.assertIn('for (index in 0...sourceBatch.tickCount)',tail)
        self.assertIn('modManager.update(sourceBatch.tickElapsed)',tail)
        self.assertLess(tail.index('modManager.updateTimeline(curDecStep)'),tail.index('modManager.update(sourceBatch.tickElapsed)'))
        self.assertNotIn('modManager.update(elapsed)',update)
        self.run_haxe(r'''
class Manager {
 public var deltas:Array<Float>=[];public var steps:Array<Float>=[];
 public function new() {}
 public function updateTimeline(step:Float):Void steps.push(step);
 public function update(elapsed:Float):Void deltas.push(elapsed);
}
class NightmareVisionFlxGView {
 public static function runSourceTick(clock:Dynamic,index:Int,count:Int,callback:Void->Void):Void callback();
}
class Main {
 static var modifiersRegistered=false;static var modManager=new Manager();static var compatScriptClock:Dynamic={};static var curDecStep=2.;
 static function pass(sourceBatch:CompatScriptTickBatch):Void { __PHASE__ }
 static function main() {
  pass(new CompatScriptTickBatch(2,1/60));if(modManager.deltas.length!=0)throw 'pre-registration update';
  modifiersRegistered=true;pass(new CompatScriptTickBatch(0,1/60));if(modManager.deltas.length!=0)throw 'render-only frame';
  pass(new CompatScriptTickBatch(2,1/60));if(modManager.deltas.length!=2||modManager.deltas[0]!=1/60||modManager.steps.length!=2)throw 'source batch delta/count';
 }
}
'''.replace('__PHASE__',tail))

    def test_source_pre_generation_dimensions(self):
        play=(ROOT/"source/PlayState.hx").read_text(encoding="utf-8")
        self.assertNotIn('new NightmareVisionModManager(null, Note.NOTE_AMOUNT, nightmareVisionLaneCount(), false)',play)
        self.assertIn('modManager = new NightmareVisionModManager(null, 4, 2, false);',play)
        self.run_haxe(r'''
class Main {
 static function main() {
  var modManager = new NightmareVisionModManager(null,4,2,false);
  if(modManager.keys!=4||modManager.lanes!=2||modManager.registry.keys!=4||modManager.registry.players!=2||modManager.register.keys().hasNext())throw 'pre-generation dimensions/empty registration';
  var registry=modManager.registry;var timeline=modManager.modifierTimeline;
  modManager.configureDimensions(3,5);modManager.registerEssentialModifiers();modManager.registerDefaultModifiers();
  if(modManager.keys!=3||modManager.lanes!=5||modManager.registry!=registry||modManager.modifierTimeline!=timeline||modManager.getValue('xmod2',4)!=1)throw 'final source dimensions/indexed values/identity';
  if(modManager.get('xmod3')!=null)throw 'indexed dimensions used stale keys';modManager.destroy();
 }
}
''')
