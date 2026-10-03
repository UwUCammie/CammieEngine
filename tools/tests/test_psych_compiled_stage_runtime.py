"""Owner-scoped compiled Psych stage lifecycle adapter fixture."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychCompiledStageRuntimeTest(unittest.TestCase):
    def test_native_group_foreach_restores_owner_script_objects(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/SceneSprite.hx"
            module.parent.mkdir(parents=True)
            module.write_text(
                "package demo; import flixel.FlxSprite; class SceneSprite extends FlxSprite { public function new() super(); public function dance() {} }\n",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                """import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function main():Void {
  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('flixel.FlxSprite',FlxSprite);
  var loaded = CodenameScriptClassLoader.load(Sys.args()[0],['demo.SceneSprite'],bindings,bindings);
  if (loaded.diagnostics.length != 0) throw 'load failed: '+loaded.diagnostics;
  var owner = loaded.scope.createInstance('demo.SceneSprite');
  var group = new FlxTypedGroup<FlxBasic>();
  var addArgs = loaded.scope.unwrapNativeGroupArguments(group,'add',[owner]);
  group.add(cast addArgs[0]);
  var seen:Dynamic = null;
  var forEachArgs = loaded.scope.unwrapNativeGroupArguments(group,'forEach',[
   function(value:Dynamic):Void { seen = value; }
  ]);
  group.forEach(cast forEachArgs[0]);
  if (seen != owner) throw 'native group callback lost its script owner';
  group.destroy();
  loaded.scope.release();
 }
}""",
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "Main", str(owner)],
                cwd=ROOT, env=haxe_env(), capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_group_member_index_read_and_write_uses_owner_object(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            source = owner / "source/demo"
            source.mkdir(parents=True)
            (source / "IndexedSprite.hx").write_text(
                """package demo;
import flixel.FlxSprite;
class IndexedSprite extends FlxSprite {
 public function new() super();
}
""",
                encoding="utf-8",
             newline='\n')
            (source / "GroupProbe.hx").write_text(
                """package demo;
import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import demo.IndexedSprite;
class GroupProbe extends FlxSprite {
 public var memberGroup:FlxTypedGroup<FlxBasic>;
 public function new() {
  super();
  memberGroup = new FlxTypedGroup<FlxBasic>();
  var sprite = new IndexedSprite();
  sprite.x = 17;
  memberGroup.add(sprite);
  if (memberGroup.members.length != 1 || memberGroup.members[0].x != 17)
   throw 'indexed native group read did not restore its owner sprite';
  memberGroup.members[0].x = 29;
  if (sprite.x != 29 || memberGroup.members[0].x != 29)
   throw 'indexed native group write did not reach its owner sprite';
 }
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "PsychNativeGroupIndexProbe.hx").write_text(
                r'''import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
class PsychNativeGroupIndexProbe {
 static function main():Void {
  var owner = Sys.args()[0];
  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('flixel.FlxBasic',FlxBasic);
  bindings.set('FlxSprite',FlxSprite);
  bindings.set('flixel.FlxSprite',FlxSprite);
  bindings.set('FlxTypedGroup',FlxTypedGroup);
  bindings.set('flixel.group.FlxGroup.FlxTypedGroup',FlxTypedGroup);
  var loaded = CodenameScriptClassLoader.load(owner,
   ['demo.GroupProbe','demo.IndexedSprite'],bindings,bindings);
  if (loaded.diagnostics.length != 0)
   throw 'native group index fixture source did not load: ' + loaded.diagnostics;
  var probe = loaded.scope.createInstance('demo.GroupProbe');
  if (probe == null) throw 'native group index fixture class was not constructed';
  var scriptProbe:hscript.AbstractScriptClass = cast probe;
  var group:FlxTypedGroup<FlxBasic> = cast scriptProbe.memberGroup;
  if (group.members.length != 1
   || !Std.isOfType(group.members[0],PsychScriptClassBasicBridge)
   || Std.isOfType(group.members[0],hscript.ScriptClass))
   throw 'indexed property access replaced the native bridge in group storage';
  var bridge:PsychScriptClassBasicBridge = cast group.members[0];
  var scriptOwner = loaded.scope.unwrapIndexedMember(bridge);
  if (scriptOwner != bridge.scriptOwner())
   throw 'indexed member did not resolve to its owner-scoped script object';
  var nativeSprite:FlxSprite = cast scriptOwner.superClass;
  if (nativeSprite.x != 29)
   throw 'indexed member write did not update the composed native sprite';

  var foreign = CodenameScriptClassLoader.load(owner,
   ['demo.IndexedSprite'],bindings,bindings);
  if (foreign.diagnostics.length != 0)
   throw 'foreign owner fixture source did not load: ' + foreign.diagnostics;
  var foreignOwner = foreign.scope.createInstance('demo.IndexedSprite');
  var foreignBridge = foreign.scope.nativeFlixelSceneObject(foreignOwner,true);
  if (loaded.scope.unwrapIndexedMember(foreignBridge) != foreignBridge)
   throw 'indexed member unwrapped a bridge owned by another scope';
  foreign.scope.release();
  group.destroy();
  loaded.scope.release();
 }
}''',
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "PsychNativeGroupIndexProbe", str(owner)],
                cwd=ROOT, env=haxe_env(), capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_implicit_global_source_import_resolves_cross_package_superclass(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            background = owner / "source/objects/Background.hx"
            child = owner / "source/states/stages/objects/Child.hx"
            background.parent.mkdir(parents=True)
            child.parent.mkdir(parents=True)
            background.write_text(
                "package objects; class Background { public var value:Int = 7; public function new() {} public function ping():Int return value; }\n",
                encoding="utf-8",
             newline='\n')
            child.write_text(
                "package states.stages.objects; class Child extends Background { public function new() { super(); } }\n",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                """class Main {
 static function main():Void {
  var loaded = CodenameScriptClassLoader.load(Sys.args()[0],
   ['states.stages.objects.Child', 'objects.Background'], new Map(), new Map());
  if (loaded.diagnostics.length != 0) throw 'load failed: ' + loaded.diagnostics;
  var child = loaded.scope.createInstance('states.stages.objects.Child');
  if (child == null || child.superClass == null)
   throw 'implicit source import did not resolve the owner superclass';
  if (child.callFunction('ping') != 7)
   throw 'inherited script method did not dispatch through the owner class chain';
  loaded.scope.release();
 }
}""",
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "Main", str(owner)],
                cwd=ROOT, env=haxe_env(), capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_stage_interpolates_haxe_single_quoted_animation_prefixes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/VizInterpolationStage.hx"
            module.parent.mkdir(parents=True)
            module.write_text(
                """package demo;
class VizInterpolationStage extends BaseStage {
	final VIZ_MAX = 7;
	override public function create():Void {
		game.comboLabel = 'combo${game.combo}';
		for (i in 1...VIZ_MAX+1) {
			var viz:Dynamic = game.makeViz();
			viz.animation.addByPrefix('VIZ', 'viz$i', 0);
			viz.animation.curAnim.finish();
		}
	}
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "CodenameScriptInterp.hx").write_text(
                """class CodenameScriptInterp {
	public var variables:Map<String,Dynamic>=new Map();
	public function new() {}
	public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}""",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                r"""class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var prefixes:Array<String>=[];
  var finishCount=0;
  var atlasFrames=['viz10000','viz20000','viz30000','viz40000','viz50000','viz60000','viz70000'];
  var host:Dynamic={members:[],combo:42,comboLabel:'',makeViz:function():Dynamic {
   var animation:Dynamic={curAnim:null};
   Reflect.setField(animation,'addByPrefix',function(_name:String,prefix:String,_fps:Int):Void {
    prefixes.push(prefix);
    var found=false;
    for(frameName in atlasFrames) if(frameName.indexOf(prefix)==0) found=true;
    if(found)
     Reflect.setField(animation,'curAnim',{finish:function():Void finishCount++});
   });
   return {animation:animation};
  }};
  var runtime=new PsychCompiledStageRuntime(owner,'demo.VizInterpolationStage',host);
  if(!runtime.create() || !runtime.active)
   throw 'owner stage failed to create from viz atlas prefixes: '+runtime.diagnostics;
  if(prefixes.join(',')!='viz1,viz2,viz3,viz4,viz5,viz6,viz7')
   throw 'single-quoted Haxe interpolation was not applied to owner class source: '+prefixes;
  if(finishCount!=7) throw 'the viz atlas did not provide a matching animation for every sprite';
  if(Reflect.field(host,'comboLabel')!='combo42')
   throw 'braced property interpolation did not preserve owner-stage string semantics: '+Reflect.field(host,'comboLabel');
  runtime.destroy();
 }
}""",
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "Main", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_base_stage_lifecycle_and_host_delegation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/CompiledStage.hx"
            module.parent.mkdir(parents=True)
            module.write_text(
                """package demo;
import backend.BaseStage;
import backend.BaseStage.Countdown;
class CompiledStage extends BaseStage {
	override public function create():Void {
		defaultCamZoom = 1.35;
		add('created');
	}
	override public function createPost():Void { add('post-created'); }
	override public function countdownTick(count:Countdown, num:Int):Void {
		add('countdown:' + Std.string(count) + ':' + num);
	}
	override public function startSong():Void { add('song-start'); }
	override public function update(elapsed:Float):Void { add('update:' + elapsed); }
	override public function eventCalled(eventName:String, value1:String, value2:String,
		flValue1:Null<Float>, flValue2:Null<Float>, strumTime:Float):Void {
		add('event:' + eventName + ':' + value1);
	}
	override public function stepHit():Void { add('step:' + Std.string(curStep) + ':' + curSection); }
	override public function destroy():Void { add('destroyed'); }
}
""",
                encoding="utf-8",
             newline='\n')
            package_relative = owner / "source/states/stages/PackageRelativeStage.hx"
            package_relative.parent.mkdir(parents=True)
            package_relative.write_text(
                """package states.stages;
class PackageRelativeStage extends BaseStage {
	override public function create():Void { add('package-relative-create'); }
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "CodenameScriptInterp.hx").write_text(
                """class CodenameScriptInterp {
	public var variables:Map<String,Dynamic>=new Map();
	public function new() {}
	public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}""",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                r"""class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var added:Array<String>=[];
  var host:Dynamic={
   defaultCamZoom:1.05,
   curStep:0,
   curSection:2,
   members:[],
   getSection:function():Int { return 9; },
   openSubState:function(_subState:Dynamic):Void { added.push('host-open'); },
   closeSubState:function():Void { added.push('host-close'); },
   add:function(value:Dynamic):Dynamic { added.push(Std.string(value)); return value; },
   insert:function(index:Int,value:Dynamic):Dynamic { added.push('insert:'+index+':'+Std.string(value)); return value; },
   remove:function(value:Dynamic,splice:Bool=false):Dynamic { added.push('remove:'+Std.string(value)); return value; }
  };
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('backend.BaseStage.Countdown',PsychBaseStageCountdown);
  bindings.set('Countdown',PsychBaseStageCountdown);
  var runtime=new PsychCompiledStageRuntime(owner,'demo.CompiledStage',host,bindings);
  if(!runtime.create() || !runtime.active)
   throw 'owner stage failed to create: '+runtime.diagnostics;
  if(Reflect.field(host,'defaultCamZoom')!=1.35 || added.join(',')!='created')
   throw 'BaseStage create properties or scene operations did not reach the host: '+added;
  if(!runtime.createPost()) throw 'createPost did not dispatch';
  if(!runtime.dispatch('countdownTick',[PsychBaseStageCountdown.THREE,0]))
   throw 'typed Psych countdown callback did not dispatch';
  if(!runtime.dispatch('startSong',[])) throw 'startSong did not dispatch';
  if(!runtime.update(0.25)) throw 'update did not dispatch';
  if(!runtime.dispatch('eventCalled',['Glow','source-value','',null,null,123.0]))
   throw 'event callback did not dispatch';
  Reflect.setField(host,'curStep',17);
  if(!runtime.dispatch('stepHit',[])) throw 'step callback did not dispatch';
  if(!runtime.dispatch('openSubState',[{}]) || !runtime.dispatch('closeSubState',[]))
   throw 'substate callbacks did not dispatch';
  if(added.join(',')!='created,post-created,countdown:THREE:0,song-start,update:0.25,event:Glow:source-value,step:17:9')
   throw 'BaseStage callbacks were reordered or lost: '+added;
  if(added.indexOf('host-open')>=0 || added.indexOf('host-close')>=0)
   throw 'default substate callbacks must not recurse into the PlayState host';
  runtime.destroy();
  if(runtime.active || added[added.length-1]!='destroyed')
   throw 'destroy hook or owner scope teardown did not run';
  if(runtime.dispatch('stepHit',[])) throw 'released owner scope accepted another callback';
  var packageRuntime=new PsychCompiledStageRuntime(owner,'states.stages.PackageRelativeStage',host,bindings);
  if(!packageRuntime.create() || !packageRuntime.active)
   throw 'package-relative superclass did not resolve through an explicit compatibility binding: '+packageRuntime.diagnostics;
  if(added[added.length-1]!='package-relative-create')
   throw 'package-relative stage did not dispatch create: '+added;
  packageRuntime.destroy();
 }
}""",
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp",
                str(ROOT / "source"),
                "-cp",
                str(base),
                "-cp",
                str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp",
                str(ROOT / ".haxelib/hscript-ex/git/src"),
                *FLIXEL_ARGS,
                "--run",
                "Main",
                str(owner),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actor_group_proxy_preserves_psych_start_anchor_and_layer_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            stage = owner / "source/demo/GroupStage.hx"
            stage.parent.mkdir(parents=True)
            stage.write_text(
                """package demo;
import backend.BaseStage;
import flixel.FlxBasic;
class GroupStage extends BaseStage {
 override public function create():Void {
  if (gfGroup.x != 100 || gfGroup.y != 200 || gfGroup.members.length != 1)
   throw 'Psych group did not expose its stage anchor and live actor';
  var seen = 0;
  for (member in gfGroup) {
   if (member != gf) throw 'Psych group iteration returned another actor';
   seen++;
  }
  if (seen != 1) throw 'Psych group iteration did not yield one actor';
  gfGroup.x = 125;
  gfGroup.y = 230;
  if (gfGroup.x != 125 || gfGroup.y != 230 || gf.x != 142 || gf.y != 237)
   throw 'group translation did not update the anchor and preserve actor offsets';
  addBehindGF(new FlxBasic());
 }
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "PsychActorGroupProbe.hx").write_text(
                r"""import flixel.FlxBasic;
class PsychActorGroupProbe {
 static function main():Void {
  var owner=Sys.args()[0];
  var actor:Dynamic={x:117.0,y:207.0};
  var hostMembers:Array<Dynamic>=[actor];
  var insertedAt=-99;
  var synced:Array<String>=[];
  var host:Dynamic={
   gf:actor,
   boyfriend:{x:770.0,y:450.0},
   dad:{x:100.0,y:100.0},
   curStage:{gfInfo:{x:100.0,y:200.0},bfInfo:{x:770.0,y:450.0},dadInfo:{x:100.0,y:100.0}},
   members:hostMembers,
   syncPsychStageGroupAnchor:function(role:String,axis:String,value:Float):Void {
    synced.push(role+':'+axis+':'+value);
   },
   add:function(value:Dynamic):Dynamic { hostMembers.push(value); return value; },
   insert:function(index:Int,value:Dynamic):Dynamic {
    insertedAt=index;
    hostMembers.insert(index,value);
    return value;
   },
   remove:function(value:Dynamic,splice:Bool=false):Dynamic { hostMembers.remove(value); return value; }
  };
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('flixel.FlxBasic',FlxBasic);
  bindings.set('FlxBasic',FlxBasic);
  var runtime=new PsychCompiledStageRuntime(owner,'demo.GroupStage',host,bindings);
  if(!runtime.create() || !runtime.active)
   throw 'Psych group source stage failed: '+runtime.diagnostics;
  var info=Reflect.field(Reflect.field(host,'curStage'),'gfInfo');
  if(Reflect.field(info,'x')!=125 || Reflect.field(info,'y')!=230
   || Reflect.field(actor,'x')!=142 || Reflect.field(actor,'y')!=237)
   throw 'group movement did not persist to StageHelper placement and the live actor';
  if(insertedAt!=0 || hostMembers.length!=2 || hostMembers[1]!=actor)
   throw 'addBehindGF did not use the direct actor layer position';
  if(synced.join(',')!='gf:x:125,gf:y:230')
   throw 'group movement did not synchronize the later-swap anchor: '+synced;
  runtime.destroy();
 }
}""",
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "PsychActorGroupProbe", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not (ROOT.parent / 'FNF-Example-Mods/misc/psych_source_code/source/states/stages/StageWeek1.hx').is_file(), 'mounted Psych StageWeek1 fixture is unavailable')
    def test_mounted_stageweek1_source_loads_through_the_production_owner_loader(self):
        owner = ROOT / "tmp/psych-archive-source/FNF-PsychEngine-main"
        self.assertTrue((owner / "source/states/stages/StageWeek1.hx").is_file())
        fixture = r'''class PsychArchiveStageLoadProbe {
 static function main() {
  var owner = Sys.args()[0];
  var bindings:Map<String,Dynamic> = new Map();
  var external = [
   "FlxBasic", "FlxCamera", "FlxG", "FlxObject", "FlxSprite", "FlxSubState",
   "FlxTiledSprite", "FlxAtlasFrames", "FlxTypedGroup", "FlxSpriteGroup",
   "FlxSound", "FlxText", "FlxEase", "FlxTween", "FlxColor", "FlxTimer",
   "BlendMode", "ADD", "Math", "Std", "Reflect", "StringTools", "Paths",
   "states.PlayState", "objects.Character", "objects.Note", "backend.Conductor",
   "backend.CoolUtil", "backend.Paths", "flixel.FlxBasic", "flixel.FlxCamera",
   "flixel.FlxG", "flixel.FlxObject", "flixel.FlxSprite", "flixel.FlxSubState",
   "flixel.addons.display.FlxTiledSprite", "flixel.graphics.frames.FlxAtlasFrames",
   "flixel.group.FlxGroup", "flixel.group.FlxGroup.FlxTypedGroup",
   "flixel.group.FlxSpriteGroup", "flixel.sound.FlxSound", "flixel.text.FlxText",
   "flixel.tweens.FlxEase", "flixel.tweens.FlxTween", "flixel.util.FlxColor",
   "flixel.util.FlxTimer", "openfl.display.BlendMode", "backend.BaseStage.Countdown",
   "Countdown"
  ];
  for (name in external) bindings.set(name, name);
  bindings.set("BaseStage", PsychBaseStageCompat);
  bindings.set("backend.BaseStage", PsychBaseStageCompat);
  bindings.set("ClientPrefs", PsychClientPrefsCompat);
  bindings.set("backend.ClientPrefs", PsychClientPrefsCompat);
  var symbols:Map<String,Dynamic> = new Map();
  for (name in bindings.keys()) symbols.set(name, bindings.get(name));
  var loaded = CodenameScriptClassLoader.load(owner, ["states.stages.StageWeek1"], bindings, symbols);
  if (loaded.diagnostics.length > 0)
   throw "mounted Psych StageWeek1 owner module failed: " + loaded.diagnostics.join("; ");
  if (!loaded.imports.exists("states.stages.StageWeek1"))
   throw "mounted Psych StageWeek1 did not register in its selected owner scope";
  var host:Dynamic={defaultCamZoom:0.9, members:[], add:function(value:Dynamic):Dynamic return value};
  var stage=loaded.scope.createInstance("states.stages.StageWeek1",[host]);
  if(stage==null || !Std.isOfType(stage.superClass,PsychBaseStageCompat))
   throw "mounted Psych StageWeek1 did not instantiate against the explicitly bound BaseStage adapter";
  var baseStage:PsychBaseStageCompat=cast stage.superClass;
  if(baseStage.game!=host)
   throw "mounted Psych StageWeek1 lost its owner PlayState host during superclass construction";
  loaded.scope.release();
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "PsychArchiveStageLoadProbe.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS, "--run",
                 "PsychArchiveStageLoadProbe", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_shader_metadata_uniforms_and_psych_camera_filter_bridge(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            source = owner / "source"
            (source / "demo").mkdir(parents=True)
            (source / "shaders").mkdir(parents=True)
            (source / "shaders/RainShader.hx").write_text(
                '''package shaders;
import flixel.system.FlxAssets.FlxShader;
import openfl.display.ShaderParameter;
import openfl.display.ShaderParameterType;
typedef Light = { var radius:Float; }
class RainShader extends FlxShader {
 @:glFragmentHeader("uniform vec2 uScreenResolution; uniform vec4 uCameraBounds;")
 @:glFragmentSource("
  #pragma header
  uniform float uScale;
  uniform float uIntensity;
  uniform float uTime;
  uniform float uPuddleY;
  uniform float uPuddleScaleY;
  uniform sampler2D uBlurredScreen;
  uniform sampler2D uMask;
  uniform sampler2D uLightMap;
  uniform int numLights;
  void main(void) { gl_FragColor = vec4(uIntensity + uTime); }
 ")
 public function new() {
  super();
  this.uScreenResolution.value = [640.0, 480.0];
  this.uCameraBounds.value = [1.0, 2.0, 639.0, 479.0];
  this.uScale.value = [1.25];
  this.uIntensity.value = [0.625];
  this.uTime.value = [2.5];
  this.uPuddleY.value = [0.75];
  this.uPuddleScaleY.value = [0.5];
  this.numLights.value = [3];
 }
}
''',
                encoding="utf-8",
             newline='\n')
            (source / "demo/FilterStage.hx").write_text(
                '''package demo;
import backend.BaseStage;
import flixel.FlxG;
import openfl.filters.ShaderFilter;
import shaders.RainShader;
class FilterStage extends BaseStage {
 override public function create():Void {
  var shader = new RainShader();
  if (shader.uScreenResolution.value[0] != 640.0 || shader.uScreenResolution.value[1] != 480.0
   || shader.uCameraBounds.value[3] != 479.0 || shader.uScale.value[0] != 1.25
   || shader.uIntensity.value[0] != 0.625 || shader.uTime.value[0] != 2.5
   || shader.uPuddleY.value[0] != 0.75 || shader.uPuddleScaleY.value[0] != 0.5
   || shader.numLights.value[0] != 3 || shader.uBlurredScreen == null
   || shader.uMask == null || shader.uLightMap == null)
   throw 'generated RainShader uniform wrappers were not readable';
  FlxG.camera.setFilters([new ShaderFilter(shader)]);
 }
}
''',
                encoding="utf-8",
             newline='\n')
            fixture = r'''import flixel.FlxCamera;
import flixel.FlxG;
import openfl.filters.ShaderFilter;
import PsychFlxCameraCompat.PsychFlxGCompat;
import PsychFlxShaderCompat.PsychShaderParameterTypeCompat;
class PsychCompiledShaderBridgeProbe {
 static function main():Void {
  var owner = Sys.args()[0];
  var nativeCamera = new FlxCamera(0, 0, 640, 480, 1);
  FlxG.camera = nativeCamera;
  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('BaseStage', PsychBaseStageCompat);
  bindings.set('backend.BaseStage', PsychBaseStageCompat);
  bindings.set('flixel.FlxG', PsychFlxGCompat);
  bindings.set('FlxG', PsychFlxGCompat);
  bindings.set('flixel.system.FlxAssets.FlxShader', PsychFlxShaderCompat);
  bindings.set('FlxShader', PsychFlxShaderCompat);
  bindings.set('openfl.filters.ShaderFilter', PsychShaderFilterCompat);
  bindings.set('ShaderFilter', PsychShaderFilterCompat);
  bindings.set('openfl.display.ShaderParameter', openfl.display.ShaderParameter);
  bindings.set('ShaderParameter', openfl.display.ShaderParameter);
  bindings.set('FLOAT', PsychShaderParameterTypeCompat.FLOAT);
  bindings.set('FLOAT2', PsychShaderParameterTypeCompat.FLOAT2);
  bindings.set('Math', Math);
  bindings.set('Std', Std);
  bindings.set('Reflect', Reflect);
  bindings.set('StringTools', StringTools);
  var runtime = new PsychCompiledStageRuntime(owner, 'demo.FilterStage', {
   defaultCamZoom: 1.0,
   members: [],
   add: function(value:Dynamic):Dynamic return value,
   remove: function(value:Dynamic, splice:Bool = false):Dynamic return value
  }, bindings);
  if (!runtime.create() || !runtime.active)
   throw 'shader stage failed to create: ' + runtime.diagnostics;
  if (nativeCamera.filters == null || nativeCamera.filters.length != 1
   || !Std.isOfType(nativeCamera.filters[0], ShaderFilter))
   throw 'Psych camera setFilters did not attach one native ShaderFilter';
  var shader = (cast nativeCamera.filters[0]:ShaderFilter).shader;
  if (!Std.isOfType(shader, PsychFlxShaderCompat))
   throw 'ShaderFilter retained an HScript proxy instead of its native FlxShader';
  var shaderData = Reflect.getProperty(shader, 'data');
  var uniform = shaderData == null ? null : Reflect.field(shaderData, 'uIntensity');
  if (uniform == null || Reflect.field(uniform, 'value') == null
   || (cast Reflect.field(uniform, 'value'):Array<Float>)[0] != 0.625)
   throw 'GLSL uniform did not expose OpenFL value-array semantics';
  var screenResolution = Reflect.field(shaderData, 'uScreenResolution');
  var cameraBounds = Reflect.field(shaderData, 'uCameraBounds');
  var lightCount = Reflect.field(shaderData, 'numLights');
  if (screenResolution == null || cameraBounds == null || lightCount == null
   || Reflect.field(shaderData, 'uBlurredScreen') == null
   || Reflect.field(shaderData, 'uMask') == null || Reflect.field(shaderData, 'uLightMap') == null
   || (cast Reflect.field(screenResolution, 'value'):Array<Float>)[0] != 640.0
   || (cast Reflect.field(cameraBounds, 'value'):Array<Float>)[2] != 639.0
   || (cast Reflect.field(lightCount, 'value'):Array<Int>)[0] != 3)
   throw 'real RainShader uniforms were missing from OpenFL ShaderData';
  var source:String = Reflect.getProperty(shader, 'glFragmentSource');
  if (source == null || source.indexOf('uniform vec2 uScreenResolution;') < 0
   || source.indexOf('uniform float uIntensity;') < 0
   || source.indexOf('gl_FragColor = vec4(uIntensity + uTime)') < 0)
   throw 'owner shader metadata was not expanded into runtime GLSL';
  runtime.destroy();
 }
}'''
            (base / "PsychCompiledShaderBridgeProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "PsychCompiledShaderBridgeProbe", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_scene_proxy_is_unwrapped_at_native_group_boundary(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            stage = owner / "source/demo/SceneStage.hx"
            stage.parent.mkdir(parents=True)
            stage.write_text(
                """package demo;
import backend.BaseStage;
import demo.SceneSprite;
class SceneStage extends BaseStage {
	override public function create():Void {
		var sprite = new SceneSprite();
		if (add(sprite) != sprite) throw 'scene insertion changed the HScript proxy identity';
	}
}
""",
                encoding="utf-8",
             newline='\n')
            (owner / "source/demo/SceneSprite.hx").write_text(
                """package demo;
import flixel.FlxBasic;
class SceneSprite extends FlxBasic {
	public function new() { super(); }
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                r"""import flixel.FlxBasic;
class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var nativeAdded:Array<Dynamic>=[];
  var host:Dynamic={
   members:[],
   add:function(value:Dynamic):Dynamic {
    if(!Std.isOfType(value,FlxBasic) || Std.isOfType(value,hscript.ScriptClass))
     throw 'host received an HScript proxy instead of its FlxBasic superclass';
    nativeAdded.push(value);
    return value;
   }
  };
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('flixel.FlxBasic',FlxBasic);
  bindings.set('FlxBasic',FlxBasic);
  var runtime=new PsychCompiledStageRuntime(owner,'demo.SceneStage',host,bindings);
  if(!runtime.create() || !runtime.active)
   throw 'scene stage failed to create: '+runtime.diagnostics;
  if(nativeAdded.length!=1 || !Std.isOfType(nativeAdded[0],FlxBasic))
   throw 'host did not receive exactly one native FlxBasic';
  runtime.destroy();
 }
}""",
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                "--run", "Main", str(owner),
            ]
            result = subprocess.run(
                command, cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_owner_script_classes_cross_native_group_mutation_as_flxbasic(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            source = owner / "source/demo"
            source.mkdir(parents=True)
            (source / "GroupProbe.hx").write_text(
                """package demo;
import flixel.group.FlxSpriteGroup;
import demo.NestedSprite;
class GroupProbe extends FlxSpriteGroup {
 public function new() {
  super();
  var sprite = new NestedSprite();
  add(sprite);
  if (length != 1) throw 'native group add did not receive the nested sprite';
  this.remove(sprite, true);
  if (length != 0) throw 'native group remove did not receive the nested sprite';
  var peer = new FlxSpriteGroup();
  peer.add(sprite);
  if (peer.length != 1) throw 'native object member call did not receive the nested sprite';
  peer.remove(sprite, true);
  insert(0, sprite);
  if (length != 1) throw 'native group insert did not receive the nested sprite';
 }
}
""",
                encoding="utf-8",
             newline='\n')
            (source / "NestedSprite.hx").write_text(
                """package demo;
import demo.ScriptSpriteParent;
class NestedSprite extends ScriptSpriteParent {
 public function new() super();
}
""",
                encoding="utf-8",
             newline='\n')
            (source / "ScriptSpriteParent.hx").write_text(
                """package demo;
import flixel.FlxSprite;
class ScriptSpriteParent extends FlxSprite {
 public function new() super();
}
""",
                encoding="utf-8",
             newline='\n')
            fixture = r'''import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class PsychNativeGroupBridgeProbe {
 static function main():Void {
  var owner = Sys.args()[0];
  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('FlxSprite', FlxSprite);
  bindings.set('flixel.FlxSprite', FlxSprite);
  bindings.set('FlxSpriteGroup', FlxTypedSpriteGroup);
  bindings.set('flixel.group.FlxSpriteGroup', FlxTypedSpriteGroup);
  var loaded = CodenameScriptClassLoader.load(owner, ['demo.GroupProbe'], bindings, bindings);
  if (loaded.diagnostics.length > 0)
   throw 'native group fixture source did not load: ' + loaded.diagnostics.join('; ');
  var probe = loaded.scope.createInstance('demo.GroupProbe');
  if (probe == null) throw 'native group fixture class was not constructed';
  var group:FlxTypedSpriteGroup<FlxSprite> = cast probe.superClass;
  if (group.length != 1 || group.members.length != 1
   || !Std.isOfType(group.members[0], FlxBasic)
   || Std.isOfType(group.members[0], hscript.ScriptClass))
   throw 'group mutation retained a script proxy instead of one native FlxBasic';
  loaded.scope.release();
 }
}'''
            (base / "PsychNativeGroupBridgeProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "PsychNativeGroupBridgeProbe", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_flxtween_unwraps_only_same_owner_native_script_targets(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            source = owner / "source/demo"
            source.mkdir(parents=True)
            (source / "TweenSprite.hx").write_text(
                """package demo;
import flixel.FlxSprite;
class TweenSprite extends FlxSprite {
 public function new() super();
}
""",
                encoding="utf-8",
             newline='\n')
            (source / "TweenStage.hx").write_text(
                """package demo;
import backend.BaseStage;
import demo.TweenSprite;
import flixel.tweens.FlxTween;
class TweenStage extends BaseStage {
 override public function create():Void {
  var sprite = new TweenSprite();
  FlxTween.tween(sprite, {alpha: 0.5}, 0.75, {startDelay: 0.25});
  add(sprite);
 }
}
""",
                encoding="utf-8",
             newline='\n')
            (source / "ForeignSprite.hx").write_text(
                """package demo;
import flixel.FlxSprite;
class ForeignSprite extends FlxSprite {
 public function new() super();
}
""",
                encoding="utf-8",
             newline='\n')
            fixture = r'''import flixel.FlxBasic;
import flixel.FlxSprite;
import flixel.tweens.FlxTween;
class PsychNativeTweenBridgeProbe {
 static function main():Void {
  var owner = Sys.args()[0];
  var manager = new flixel.tweens.FlxTween.FlxTweenManager();
  FlxTween.globalManager = manager;

  var bindings:Map<String,Dynamic> = new Map();
  bindings.set('backend.BaseStage',PsychBaseStageCompat);
  bindings.set('BaseStage',PsychBaseStageCompat);
  bindings.set('flixel.FlxSprite',FlxSprite);
  bindings.set('FlxSprite',FlxSprite);
  bindings.set('flixel.tweens.FlxTween',FlxTween);
  bindings.set('FlxTween',FlxTween);
  var nativeAdded:Array<Dynamic> = [];
  var host:Dynamic = {
   members: [],
   add: function(value:Dynamic):Dynamic {
    if (!Std.isOfType(value,FlxBasic) || Std.isOfType(value,hscript.ScriptClass))
     throw 'stage host received an HScript proxy instead of FlxBasic';
    nativeAdded.push(value);
    return value;
   }
  };
  var runtime = new PsychCompiledStageRuntime(owner,'demo.TweenStage',host,bindings);
  if (!runtime.create() || !runtime.active)
   throw 'tween stage failed to create: ' + runtime.diagnostics;
  var tweens:Array<Dynamic> = cast Reflect.field(manager,'_tweens');
  if (tweens == null || tweens.length != 1)
   throw 'native FlxTween did not register exactly one tween';
  var tween = tweens[0];
  var tweenTarget = Reflect.field(tween,'_object');
  if (nativeAdded.length != 1
   || !Std.isOfType(nativeAdded[0],PsychScriptClassBasicBridge)
   || (cast nativeAdded[0]:PsychScriptClassBasicBridge).scriptOwner().superClass != tweenTarget
   || !Std.isOfType(tweenTarget,FlxSprite)
   || Std.isOfType(tweenTarget,hscript.ScriptClass))
   throw 'FlxTween did not receive the native target of the stage lifecycle bridge';
  var tweenValues = Reflect.field(tween,'_properties');
  if (Reflect.field(tweenValues,'alpha') != 0.5
   || Reflect.field(tween,'duration') != 0.75 || Reflect.field(tween,'startDelay') != 0.25)
   throw 'FlxTween values, duration, or options changed at the owner boundary';

  var primaryLoad = CodenameScriptClassLoader.load(owner,['demo.TweenSprite'],bindings,bindings);
  if (primaryLoad.diagnostics.length > 0)
   throw 'primary scope target fixture failed to load: ' + primaryLoad.diagnostics;
  var primary = primaryLoad.scope.createInstance('demo.TweenSprite');
  var foreignLoad = CodenameScriptClassLoader.load(owner,['demo.ForeignSprite'],bindings,bindings);
  if (foreignLoad.diagnostics.length > 0)
   throw 'foreign owner proxy fixture failed to load: ' + foreignLoad.diagnostics;
  var foreign = foreignLoad.scope.createInstance('demo.ForeignSprite');
  var rejected = false;
  try primaryLoad.scope.unwrapNativeTweenArguments(FlxTween,'tween',[foreign])
  catch (_:Dynamic) rejected = true;
  if (!rejected) throw 'native tween accepted a ScriptClass target from a different owner scope';
  var nonTargetArgs:Array<Dynamic> = [foreign, 1.0, 2.0];
  if (primaryLoad.scope.unwrapNativeTweenArguments(FlxTween,'num',nonTargetArgs)[0] != foreign)
   throw 'non-target FlxTween methods changed their first argument';
  var nativePrimary = primaryLoad.scope.unwrapNativeTweenArguments(FlxTween,'tween',[primary]);
  if (nativePrimary[0] != (cast primary:hscript.ScriptClass).superClass
   || !Std.isOfType(nativePrimary[0],FlxBasic))
   throw 'same-scope helper did not return the native FlxBasic target';
  primaryLoad.scope.release();
  foreignLoad.scope.release();
  runtime.destroy();
 }
}'''
            (base / "PsychNativeTweenBridgeProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                 "--run", "PsychNativeTweenBridgeProbe", str(owner)],
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
