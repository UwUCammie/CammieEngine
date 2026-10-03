"""Compile the production visual builder with lightweight actor/asset doubles."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameCharacterVisualTests(unittest.TestCase):
    def run_fixture(self, main_source):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "flixel/util").mkdir(parents=True)
            (folder / "flixel/util/FlxColor.hx").write_text('''
package flixel.util;
class FlxColor {
 public static function fromString(value:String):Int return 0x123456;
}
''', newline='\n')
            (folder / "Character.hx").write_text('''
class Character {
 public var xml:CodenameXmlAccess;
 public var globalOffset = new FakePoint();
 public var cameraOffset = new FakePoint();
 public var playerOffsets = false;
 public var flipX = false;
 public var holdTime:Float = 0;
 public var beatInterval:Int = 0;
 public var antialiasing = false;
 public var scale = new FakePoint();
 public var applyStageMatrix(default,set):Bool = false;
 public var animateLoadedForMatrix:Bool = false;
 public var matrixValuesAfterAtlas:Array<Bool> = [];
 public var frames(default,set):Dynamic;
 public var animation = new FakeAnimation();
 public var animOffsets:Map<String, Array<Dynamic>> = new Map();
 public var icon:String;
 public var iconColor:Null<Int>;
 public var gameOverCharacter:String;
 public var loadedTextureAtlas:String;
 public function new() {}
 function set_frames(value:Dynamic):Dynamic {
  animation.destroyAnimations();
  return frames=value;
 }
 function set_applyStageMatrix(value:Bool):Bool {
  this.applyStageMatrix=value;
  if(animateLoadedForMatrix) matrixValuesAfterAtlas.push(value);
  return value;
 }
 public function updateHitbox():Void {}
 public function loadTextureAtlas(path:String):Character {
  loadedTextureAtlas=path;animateLoadedForMatrix=true;frames=path;
  // FlxAnimate's frames setter reapplies this property to refresh atlas bounds.
  applyStageMatrix=applyStageMatrix;
  return this;
 }
}
class FakePoint {
 public var x:Float = 0;
 public var y:Float = 0;
 public function new() {}
 public function set(x:Float, y:Float):Void {this.x=x;this.y=y;}
}
class FakeAnimation {
 public var calls:Array<String> = [];
 public function new() {}
 public function destroyAnimations():Void calls.push("reset");
 public function add(name:String, indices:Array<Int>, fps:Float, loop:Bool):Void
  calls.push(name+":"+indices.join(",")+":"+fps+":"+loop);
 public function addByIndices(name:String, prefix:String, indices:Array<Int>, suffix:String, fps:Float, loop:Bool):Void
  calls.push(name+":"+prefix+":"+indices.join(",")+":"+fps+":"+loop);
 public function addByPrefix(name:String, prefix:String, fps:Float, loop:Bool):Void
  calls.push(name+":"+prefix+":"+fps+":"+loop);
 public function addBySymbol(name:String, symbol:String, fps:Float, loop:Bool):Void
  calls.push("symbol:"+name+":"+symbol+":"+fps+":"+loop);
 public function addBySymbolIndices(name:String, symbol:String, indices:Array<Int>, fps:Float, loop:Bool):Void
  calls.push("symbolIndices:"+name+":"+symbol+":"+indices.join(",")+":"+fps+":"+loop);
}
''', newline='\n')
            (folder / "CodenamePaths.hx").write_text('''
class CodenamePaths {
 public var requests:Array<String> = [];
 public var atlasPath:String;
 public function new() {}
 public function animateAtlasPath(key:String):String return atlasPath;
 public function getFrames(key:String):Dynamic {requests.push(key);return key;}
}
''', newline='\n')
            (folder / "CodenameScriptDiscovery.hx").write_text('''
class CodenameScriptDiscovery {
 public static function safeRelativeName(value:String):Bool {
  if(value==null || value=="" || StringTools.startsWith(value,"/")) return false;
  for(part in value.split("/")) if(part=="" || part=="." || part=="..") return false;
  return true;
 }
}
''', newline='\n')
            (folder / "Main.hx").write_text(main_source, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder),
                 "--run", "Main"], cwd=ROOT, capture_output=True, text=True)

    def test_live_mutated_xml_and_ordered_node_callbacks(self):
        main = '''
class Main {
 static function check(ok:Bool, message:String):Void if(!ok) throw message;
 static function main():Void {
  var xml=Xml.parse('<character x="3" y="4" camx="5" camy="6" scale="2" isPlayer="true" flipX="true" holdTime="7" interval="3" icon="face" color="#FFFFFF" gameOverChar="dead" custom="value"><anim name="idle" anim="idle" x="8" y="9"/><anim name="sing" anim="sing" indices="1..3,5,8..6" fps="12" loop="true"/><ext script="extra.hx"/></character>').firstElement();
  xml.set("x","11"); // create/onCharacterXMLParsed changed the current XML.
  var actor=new Character(); var paths=new CodenamePaths(); var seen:Array<String>=[];
  var meta=CodenameCharacterVisual.build(actor,"team/Hero",xml,paths,function(node) {
   seen.push(node.nodeName);
   check(actor.globalOffset.x==11 && actor.cameraOffset.y==6 && actor.playerOffsets && actor.flipX,
    "root properties unavailable at callback");
   if(node.get("name")=="idle") {
    check(actor.animOffsets.get("idle")[0]==8,"callback before first animation applied");
    for(next in xml.elements()) if(next.get("name")=="sing") next.set("x","13");
   }
   if(node.get("name")=="sing") check(actor.animOffsets.get("sing")[0]==13,"later node mutation ignored");
  });
  check(paths.requests.join(",")=="characters/team/Hero","wrong source atlas");
  check(actor.frames=="characters/team/Hero" && actor.scale.x==2 && actor.holdTime==7
   && actor.beatInterval==3 && actor.icon=="face" && actor.iconColor==0x123456
   && actor.gameOverCharacter=="dead" && actor.xml.x==xml, "root state");
  check(seen.join(",")=="anim,anim,ext","callback order");
  check(actor.animation.calls[0]=="reset" && actor.animation.calls[1]=="idle:idle:24:false"
   && actor.animation.calls[2]=="sing:sing:1,2,3,5,8,7,6:12:true", "animation parse");
  check(meta.animOffsets.get("sing")[0]==13 && meta.extra.custom=="value", "metadata");
  check(meta.diagnostics.length==1 && StringTools.startsWith(meta.diagnostics[0],"Unsupported character XML extension"),"extension diagnostic");
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_sprite_and_invalid_identity(self):
        main = '''
class Main {
 static function main():Void {
  var actor=new Character();var paths=new CodenamePaths();
  var xml=Xml.parse('<character sprite="Other/Atlas"><anim name="still" indices="2,4"/></character>').firstElement();
  CodenameCharacterVisual.build(actor,"team/Hero",xml,paths);
  if(paths.requests.join(",")!="characters/Other/Atlas" || actor.animation.calls[1]!="still:2,4:24:false")
   throw "explicit sprite or direct indices";
  xml.set("sprite","../escape");
  var failed=false;
  try CodenameCharacterVisual.build(actor,"team/Hero",xml,paths) catch(_:Dynamic) failed=true;
  if(!failed) throw "unsafe source sprite accepted";
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_mutations_survive_omitted_xml_fields(self):
        main = '''
class Main {
 static function check(ok:Bool, message:String):Void if(!ok) throw message;
 static function main():Void {
  var actor=new Character(); var paths=new CodenamePaths();
  // These represent fields a donor create callback changed before XML load.
  actor.globalOffset.set(12, 34); actor.cameraOffset.set(56, 78);
  actor.playerOffsets=true; actor.flipX=true; actor.holdTime=9;
  actor.beatInterval=4; actor.antialiasing=true; actor.scale.set(2, 3);
  actor.animOffsets.set('manual', [23, 24]);
  actor.animOffsets.set('idle', [99, 99]);
  var omitted=Xml.parse('<character><anim name="idle" indices="0"/></character>').firstElement();
  var meta=CodenameCharacterVisual.build(actor,'hero',omitted,paths);
  check(actor.globalOffset.x==12 && actor.globalOffset.y==34
   && actor.cameraOffset.x==56 && actor.cameraOffset.y==78,'offset mutation lost');
  check(actor.playerOffsets && actor.flipX && actor.holdTime==9
   && actor.beatInterval==4 && actor.antialiasing,'create state lost');
  check(actor.scale.x==2 && actor.scale.y==3,'nonuniform scale overwritten');
  check(actor.animOffsets.get('manual')[0]==23 && actor.animOffsets.get('idle')[0]==0,
   'pre-create offsets not retained or XML offset not applied');
  check(meta.x==12 && meta.y==34 && meta.camx==56 && meta.camy==78
   && meta.playerOffsets && meta.flipX && meta.holdTime==9
   && meta.interval==null,'metadata missed live create state');
  check(paths.requests.join(',')=='characters/hero','authored sprite default');
  var explicit=Xml.parse('<character x="1" y="2" camx="3" camy="4" '
   +'isPlayer="false" flipX="false" holdTime="5" interval="6" '
   +'antialiasing="false" scale="1.5"/>').firstElement();
  CodenameCharacterVisual.build(actor,'hero',explicit,paths);
  check(actor.globalOffset.x==1 && actor.globalOffset.y==2
   && actor.cameraOffset.x==3 && actor.cameraOffset.y==4,'explicit offsets');
  check(!actor.playerOffsets && !actor.flipX && actor.holdTime==5
   && actor.beatInterval==6 && !actor.antialiasing
   && actor.scale.x==1.5 && actor.scale.y==1.5,'explicit root fields');
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_loop_type_plays_during_node_before_descriptor_and_node_callback(self):
        main = '''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var xml=Xml.parse('<character>'
   +'<anim name="idle" anim="idle" type=" LOOP " x="3"/>'
   +'<anim name="wave" anim="wave" type="loop" loop="false"/>'
   +'<anim name="wave" anim="wave2" type="loop" loop="true" forced="false"/>'
   +'<anim name="plain" anim="plain" loop="true"/>'
   +'<anim name="up" anim="up" type="loop" forced="true"/>'
   +'</character>').firstElement();
  var actor=new Character(), paths=new CodenamePaths();
  var descriptors:Array<Dynamic>=[], order:Array<String>=[], forces:Array<Bool>=[];
  var nodeCount=0;
  var result=CodenameCharacterVisual.build(actor,'hero',xml,paths,function(node) {
   order.push('node:'+node.get('name'));
   nodeCount++;
   check(descriptors.length==nodeCount,'descriptor unavailable to node callback');
  },function(name:String,forced:Bool) {
   order.push('play:'+name);forces.push(forced);
   check(actor.animOffsets.exists(name),'offset absent during loop playback');
   check(actor.animation.calls[actor.animation.calls.length-1].indexOf(name+':')==0,
    'loop played before animation registration');
   check(descriptors.length==[0,1,2,4][forces.length-1],
    'current descriptor published before node-time playback');
  },descriptors);
  check(order.join(',')=='play:idle,node:idle,play:wave,node:wave,'
   +'play:wave,node:wave,node:plain,play:up,node:up','node-time order');
  check(forces.join(',')=='false,true,false,true','resolved initial forces');
  check(result.animations==descriptors && descriptors.length==5,'shared descriptor array');
  check(descriptors[0].forced==null && descriptors[1].forced==null
   && descriptors[2].forced==false && descriptors[4].forced==true,
   'nullable raw forced metadata changed');
  check(actor.animation.calls[2]=='wave:wave:24:false'
   && actor.animation.calls[3]=='wave:wave2:24:true'
   && actor.animation.calls[4]=='plain:plain:24:true',
   'type=loop confused with Flixel looping flag');
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_animate_atlas_uses_symbol_animations_and_owner_path(self):
        main = '''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var actor=new Character(),paths=new CodenamePaths();
  paths.atlasPath='/private/owner/images/characters/BF/BF_assets';
  var xml=Xml.parse('<character sprite="BF/BF_assets">'
   +'<anim name="idle" anim="Boyfriend/BFIdle" fps="24" loop="true" x="2" y="-3"/>'
   +'<anim name="singUP" anim="Boyfriend/BFSingUP" indices="0,2,4" fps="30"/>'
   +'</character>').firstElement();
  var meta=CodenameCharacterVisual.build(actor,'bf',xml,paths);
  check(actor.loadedTextureAtlas==paths.atlasPath && actor.frames==paths.atlasPath,
   'Animate atlas was not loaded from the selected owner');
  check(paths.requests.length==0,'Animate atlas fell back to a Sparrow image');
  check(actor.animation.calls.join('|').indexOf('symbol:idle:Boyfriend/BFIdle:24:true')>=0,
   'Animate symbol animation missing: '+actor.animation.calls.join('|'));
  check(actor.animation.calls.join('|').indexOf('symbolIndices:singUP:Boyfriend/BFSingUP:0,2,4:30:false')>=0,
   'Animate symbol indices missing: '+actor.animation.calls.join('|'));
  check(actor.animOffsets.get('idle')[0]==2 && actor.animOffsets.get('idle')[1]==-3,
   'Animate animation offsets missing');
  check(meta.animations.length==2 && meta.animations[1].anim=='Boyfriend/BFSingUP',
   'Animate metadata lost authored symbols');
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_apply_stage_matrix_matches_codename_default_and_xml_override(self):
        main = '''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var paths=new CodenamePaths();paths.atlasPath='/private/owner/images/characters/BF/BF_assets';

  var omittedActor=new Character();
  CodenameCharacterVisual.initializeSourceDefaults(omittedActor);
  check(omittedActor.applyStageMatrix,'Codename default was not enabled before create');
  // Represent a create callback deliberately overriding the source default.
  omittedActor.applyStageMatrix=false;
  var omitted=Xml.parse('<character sprite="BF/BF_assets"><anim name="idle" anim="BFIdle"/></character>').firstElement();
  var omittedMeta=CodenameCharacterVisual.build(omittedActor,'bf',omitted,paths);
  check(!omittedActor.applyStageMatrix && omittedMeta.applyStageMatrix==false,
   'omitted XML did not preserve the create override');
  check(omittedActor.matrixValuesAfterAtlas.join(',')=='false',
   'atlas did not refresh bounds with the current value');
  check(omittedMeta.extra.applyStageMatrix==null,'recognized stage-matrix flag leaked into extra');

  var enabled=new Character();CodenameCharacterVisual.initializeSourceDefaults(enabled);
  var enabledXml=Xml.parse('<character sprite="BF/BF_assets" applyStageMatrix="true"/>').firstElement();
  var enabledMeta=CodenameCharacterVisual.build(enabled,'bf',enabledXml,paths);
  check(enabled.applyStageMatrix && enabledMeta.applyStageMatrix==true,'explicit true was ignored');
  check(enabled.matrixValuesAfterAtlas.join(',')=='true,true',
   'explicit true was not applied after atlas bounds initialized');
  check(enabledMeta.extra.applyStageMatrix==null,'explicit true leaked into extra');

  var disabled=new Character();CodenameCharacterVisual.initializeSourceDefaults(disabled);
  var disabledXml=Xml.parse('<character sprite="BF/BF_assets" applyStageMatrix="false"/>').firstElement();
  var disabledMeta=CodenameCharacterVisual.build(disabled,'bf',disabledXml,paths);
  check(!disabled.applyStageMatrix && disabledMeta.applyStageMatrix==false,'explicit false was ignored');
  check(disabled.matrixValuesAfterAtlas.join(',')=='true,false',
   'explicit false was not applied after atlas bounds initialized');
 }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_initializes_codename_stage_matrix_before_create(self):
        source = (ROOT / "source/Character.hx").read_text()
        start = source.index("if (codename != null && codename.nativeName == curCharacter)")
        end = source.index("\n\t\t}", start)
        construction = source[start:end]
        self.assertLess(
            construction.index("CodenameCharacterVisual.initializeSourceDefaults(this);"),
            construction.index("codenameRuntime.call('create', []);"),
        )


if __name__ == "__main__":
    unittest.main()
