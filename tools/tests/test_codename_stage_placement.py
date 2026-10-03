"""Execute Codename's pure stage placement model against upstream cases."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameStagePlacementTest(unittest.TestCase):
    def test_stage_script_only_disables_actor_placement_when_it_writes_pose(self):
        source = r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var harmless='function postCreate(){ overlay.cameras=[camHUD]; overlay.updateHitbox(); FlxG.camera.zoom=1.25; }';
  check(!CodenameStagePlacement.scriptMayChangeActorPlacement(harmless),
   'HUD and camera-only stage hooks must retain XML actor placement');
  var literalsAndComments='// boyfriend.x = 1;\nvar note="dad.y = 2"; /* gf.scale.set(2,2); */';
  check(!CodenameStagePlacement.scriptMayChangeActorPlacement(literalsAndComments),
   'comments and strings must not look like executable actor placement');
  check(CodenameStagePlacement.scriptMayChangeActorPlacement('boyfriend.x += 12;'),
   'direct actor coordinate write was not detected');
  check(CodenameStagePlacement.scriptMayChangeActorPlacement('FlxTween.tween(dad, {y: 250, alpha: 0.5}, 1);'),
   'actor pose tween was not detected');
  check(CodenameStagePlacement.scriptMayChangeActorPlacement('stage.addCharPos("dad", 100, 100);'),
   'stage placement API mutation was not detected');
 }
}'''
        self._run(source)

    def test_delayed_pose_callbacks_do_not_invalidate_initial_xml_slots(self):
        source = r'''import CodenameStagePlacement;
import haxe.Json;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var delayed='function songEvents(eventName:String) {\n'
   + ' if (eventName == "grab") new FlxTimer().start(1, () -> {\n'
   + ' boyfriend.y += boyfriend.height;\n'
   + ' FlxTween.tween(boyfriend, {y: boyfriend.y - 10}, 1);\n'
   + ' });\n'
   + '}\nfunction stepHit(step) { dad.x += 170; }';
  var effects=CodenameStagePlacement.scriptPlacementEffects(delayed);
  check(!effects.initial, 'delayed callback writes were treated as startup slot changes');
  check(effects.runtimeMutationHooks.length==2
   && effects.runtimeMutationHooks[0]=='songEvents'
   && effects.runtimeMutationHooks[1]=='stepHit', 'delayed mutation hooks were not identified');
  check(CodenameStagePlacement.scriptMayChangeActorPlacement(delayed),
   'broad actor-pose diagnostic stopped reporting delayed writes');
  var model=CodenameStagePlacement.parse('<stage/>');
  CodenameStagePlacement.applyScriptPlacementEffects(model, delayed);
  check(model.unsupported.length==0, 'delayed callbacks invalidated the static XML slots');
  var restored=CodenameStagePlacement.fromData(Json.parse(
   Json.stringify(CodenameStagePlacement.toData(model))));
  check(restored.runtimeMutationHooks.length==2
   && restored.runtimeMutationHooks[0]=='songEvents'
   && restored.runtimeMutationHooks[1]=='stepHit', 'dynamic diagnostics were lost in sidecar metadata');

  var startup='function postCreate() { dad.alpha = 0; }';
  effects=CodenameStagePlacement.scriptPlacementEffects(startup);
  check(!effects.initial && effects.runtimeMutationHooks.length==0,
   'postCreate opacity change was mistaken for actor geometry');
  model=CodenameStagePlacement.parse('<stage/>');
  CodenameStagePlacement.applyScriptPlacementEffects(model, startup);
  check(model.unsupported.length==0
   && CodenameStagePlacement.select(model,'dad',0,null,0).supported,
   'postCreate opacity change must keep static actor slots available');

  var primaryOnly='function postCreate() { dad.x += 12; }';
  check(CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(primaryOnly),
   'direct named-primary writes should allow unrelated actors to use XML slots');
  var MonsterStageShape='function postCreate() { dad.x += 12; warning.x = 20; bgCam.angle = 2; monster.alpha = 0; }';
  check(CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(MonsterStageShape),
   'ordinary stage props and cameras must not block an unrelated XML actor');
  var primaryAlias='function postCreate() { var mainActor:Character = dad; mainActor.x = 12; }';
  check(CodenameStagePlacement.scriptMayChangeActorPlacement(primaryAlias)
   && CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(primaryAlias),
   'an alias initialized directly from a named primary should remain classified as primary-only');
  var indexedAlpha='function postCreate() {\n'
   + ' var firstDark;\n var secondDark;\n'
   + ' firstDark = strumLines.members[0].characters[1];\n'
   + ' secondDark = strumLines.members[1].characters[1];\n'
   + ' for (char in [firstDark, secondDark]) char?.alpha = 0;\n'
   + ' for (char in [firstDark, secondDark]) char.alpha = 1;\n'
   + ' for (char in [firstDark, secondDark]) FlxTween.tween(char, {alpha: 0}, 1);\n'
   + '}';
  effects=CodenameStagePlacement.scriptPlacementEffects(indexedAlpha);
  check(!effects.initial && !CodenameStagePlacement.hasUnclassifiedPlacementAlias(indexedAlpha)
   && !CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(indexedAlpha),
   'alpha-only writes through indexed actor aliases must not classify as geometry writes');
  model=CodenameStagePlacement.parse('<stage/>',true);
  CodenameStagePlacement.resolveScriptPlacement(model,indexedAlpha);
  check(model.unsupported.length==0
   && CodenameStagePlacement.select(model,'dad',0,null,0).supported
   && CodenameStagePlacement.select(model,'Bambino',3,null,0).supported,
   'indexed actor opacity writes should preserve primary and extra XML slots');
  var indexedGeometry='function postCreate() {\n'
   + ' var dark; dark = strumLines.members[0].characters[1];\n dark.x += 8;\n}';
  check(CodenameStagePlacement.hasUnclassifiedPlacementAlias(indexedGeometry)
   && !CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(indexedGeometry),
   'geometry writes through indexed actor aliases must remain unresolved');
  var directIndexedGeometry='function postCreate() { strumLines.members[0].characters[1].y = 5; }';
  check(CodenameStagePlacement.hasUnclassifiedPlacementAlias(directIndexedGeometry)
   && !CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(directIndexedGeometry),
   'direct indexed actor geometry writes must remain unresolved');
  var getterAlpha='function postCreate() { var selected = getCharacter("extra"); selected.alpha = 1; }';
  check(!CodenameStagePlacement.hasUnclassifiedPlacementAlias(getterAlpha)
   && !CodenameStagePlacement.scriptMayChangeActorPlacement(getterAlpha),
   'opacity writes through unknown character getters must not gate geometry');
  var getterGeometry='function postCreate() { var selected = getCharacter("extra"); selected.x = 1; }';
  check(CodenameStagePlacement.hasUnclassifiedPlacementAlias(getterGeometry)
   && !CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(getterGeometry),
   'geometry writes through unknown character getters must stay gated');
  var isolated=CodenameStagePlacement.parse(
   '<stage><dad x="100"/><character name="Bambino" x="330"/></stage>',true);
  CodenameStagePlacement.resolveScriptPlacement(isolated,primaryOnly);
  check(CodenameStagePlacement.onlyStageScriptUnsupported(isolated),
   'primary-only script write should retain the stage-script warning');
  var extra=CodenameStagePlacement.select(isolated,'Bambino',3,null,0,true);
  check(extra.supported && extra.x==330,
   'unrelated extra actor should use its exact XML slot');
  check(!CodenameStagePlacement.select(isolated,'dad',0,null,0).supported,
   'primary actor placement must remain unsupported');
  var unknown='function postCreate() { dad.alpha = 0; character.x = 20; }';
  check(!CodenameStagePlacement.scriptWritesConfinedToPrimaryActors(unknown),
   'unclassified script alias must not enable static extra placement');
  var unknownModel=CodenameStagePlacement.parse('<stage/>',true);
  CodenameStagePlacement.resolveScriptPlacement(unknownModel,unknown);
  check(unknownModel.unsupported.indexOf('stage-script-unclassified-placement-alias')>=0,
   'unknown placement aliases need a bounded dependency diagnostic');
  var derived='function postCreate() { var selected = strumLines.members[3].characters[0]; selected.x = 10; }';
  check(CodenameStagePlacement.hasUnclassifiedPlacementAlias(derived),
   'pose writes through an indexed native actor alias must remain unresolved');
  var conditional=CodenameStagePlacement.parse(
   '<stage><char name="Bambino" x="330"/><extension/></stage>',true);
  check(!CodenameStagePlacement.select(conditional,'Bambino',3,null,0,true).supported,
   'static extra placement must remain unavailable with other stage dependencies');

  var startupOpacityThenStepGeometry='function postCreate() { dad.alpha = 0; }\n'
   + 'function stepHit(step) { dad.x += 170; boyfriend.y += 400; }';
  effects=CodenameStagePlacement.scriptPlacementEffects(startupOpacityThenStepGeometry);
  check(!effects.initial && effects.runtimeMutationHooks.length==1
   && effects.runtimeMutationHooks[0]=='stepHit',
   'startup opacity must not mask delayed stepHit geometry mutations');
  model=CodenameStagePlacement.parse('<stage/>',true);
  CodenameStagePlacement.resolveScriptPlacement(model,startupOpacityThenStepGeometry);
  check(model.unsupported.length==0
   && CodenameStagePlacement.select(model,'dad',0,null,0).supported,
   'delayed stepHit geometry must retain supported constructor-time XML slots');

  effects=CodenameStagePlacement.scriptPlacementEffects(startup + '\n' + delayed);
  check(!effects.initial && effects.runtimeMutationHooks.indexOf('songEvents')>=0
   && effects.runtimeMutationHooks.indexOf('stepHit')>=0,
   'startup opacity and delayed geometry were not separated');
 }
}'''
        self._run(source)

    def test_defaults_named_precedence_spacing_and_extended_properties(self):
        source = r'''import CodenameStagePlacement;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var empty=CodenameStagePlacement.parse('<stage/>');
  var bf=CodenameStagePlacement.select(empty,"bf",1,null,0);
  var dad=CodenameStagePlacement.select(empty,"dad",0,null,0);
  var gf=CodenameStagePlacement.select(empty,"gf",2,null,0);
  check(bf.x==770 && bf.y==100 && bf.isPlayer && bf.flip, "BF upstream default");
  check(dad.x==100 && dad.y==100 && !dad.isPlayer, "dad upstream default");
  check(gf.x==400 && gf.y==130 && gf.scrollX==0.95 && gf.scrollY==0.95,
   "GF upstream default");
  check(empty.startCamera.x==null && empty.startCamera.y==null, "optional start camera");
  var data=CodenameStagePlacement.parse('<stage startCamPosX="0" startCamPosY="250">'
   + '<bf x="800" y="110" spacingx="35" spacingy="-5" camxoffset="9" camyoffset="-4"/>'
   + '<character name="Named" x="20" y="30" spacingx="4" spacingy="6" flip="true"'
   + ' scale="2" scalex="3" scroll="0.8" scrolly="0.7" alpha="0.5" angle="12"'
   + ' skewx="7" skewy="8" zoomfactor="1.2" camxoffset="13"/>'
   + '<dad x="99"/><opponent x="111"/><dad x="123"/></stage>');
  check(data.startCamera.x==0 && data.startCamera.y==250, "stage start camera");
  var named=CodenameStagePlacement.select(data,"Named",0,"boyfriend",2);
  check(named.slotKey=="Named" && named.x==28 && named.y==42 && named.flip
   && named.isPlayer && named.scaleX==3 && named.scaleY==2
   && named.scrollX==0.8 && named.scrollY==0.7 && named.alpha==0.5
   && named.angle==12 && named.skewX==7 && named.skewY==8
   && named.zoomFactor==1.2 && named.cameraX==13 && named.cameraY==0,
   "named actor overrides role and applies occurrence properties");
  var role=CodenameStagePlacement.select(data,"Other",1,null,2);
  check(role.slotKey=="boyfriend" && role.x==870 && role.y==100 && role.cameraX==9
   && role.cameraY==-4 && role.isPlayer, "role spacing and camera offsets");
  check(CodenameStagePlacement.select(data,"Other",0,null,0).x==123,
   "last duplicate placeholder wins");
  var unknown=CodenameStagePlacement.select(data,"Other",3,null,0);
  check(unknown.slotKey=="" && unknown.x==0 && !unknown.isPlayer,
   "unknown type without slot");
 }
}'''
        self._run(source)

    def test_explicit_position_flip_fallback_and_unsupported_extensions(self):
        source = r'''import CodenameStagePlacement;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var data=CodenameStagePlacement.parse('<stage><player flip="false"/>'
   + '<character name="Named" flipX="true"><property name="x" value="5"/></character>'
   + '<use-extension script="other"/><high-memory><dad x="200"/></high-memory></stage>',true);
  var player=CodenameStagePlacement.select(data,"Other",1,"boyfriend",0);
  check(player.x==770 && !player.flip && !player.isPlayer,
   "explicit stage flip overrides player type");
  var custom=CodenameStagePlacement.select(data,"Named",0,"dad",0);
  check(custom.flip && !custom.supported, "named flip / unsupported status");
  check(data.unsupported.indexOf("stage-script")>=0
   && data.unsupported.indexOf("stage-extension")>=0
   && data.unsupported.indexOf("memory-conditional")>=0
   && data.unsupported.indexOf("slot-property")>=0,
   "unsupported placement mutations silently treated as exact");
  var noSlot=CodenameStagePlacement.select(CodenameStagePlacement.parse('<stage/>'),
   "Other",1,"custom",3);
  check(noSlot.slotKey=="custom" && noSlot.isPlayer && noSlot.x==0,
   "explicit missing position uses constructor fallback");
  var namedRole=CodenameStagePlacement.parse('<stage><character name="boyfriend"/>'
   + '<char name="folder/actor" x="14"/><dad x="bad"/></stage>');
  var overridden=CodenameStagePlacement.select(namedRole,"boyfriend",1,null,1);
  check(overridden.x==20 && overridden.y==0 && !overridden.flip && !overridden.isPlayer,
   "named role ID inherited role defaults");
  check(CodenameStagePlacement.select(namedRole,"folder/actor",0,null,0).x==14,
   "nested character ID rejected as map key");
  check(CodenameStagePlacement.select(namedRole,"Other",0,null,0).x==100,
   "malformed numeric attribute should keep prior default");
  var failed=false;
  try CodenameStagePlacement.parse('<stage><dad camxoffset="1e999"/></stage>')
  catch (_:Dynamic) failed=true;
  check(failed,"nonfinite camera offset accepted");
 }
}'''
        self._run(source)

    def test_serialized_slots_preserve_occurrences_and_reject_partial_models(self):
        source = r'''import haxe.Json;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function rejected(value:Dynamic):Bool {
  try { CodenameStagePlacement.fromData(value); return false; }
  catch (_:Dynamic) return true;
 }
 static function main():Void {
  var model=CodenameStagePlacement.parse('<stage startCamPosX="0"><bf spacingx="-12"/>'
   + '<character name="folder/actor" x="13" y="17" spacingx="5" spacingy="7"'
   + ' flip="true" camxoffset="31" scale="2" alpha="0.4" skewx="3"/>'
   + '<extension/></stage>', true);
  var raw=Json.stringify(CodenameStagePlacement.toData(model));
  var decoded=CodenameStagePlacement.fromData(Json.parse(raw));
  for (id in ['folder/actor','Other']) for (k in 0...3) {
   var before=CodenameStagePlacement.select(model,id,1,null,k);
   var after=CodenameStagePlacement.select(decoded,id,1,null,k);
   for(field in Reflect.fields(before))
    check(Reflect.field(before,field)==Reflect.field(after,field),'changed occurrence '+id+':'+k+':'+field);
  }
  check(decoded.startCamera.x==0 && decoded.startCamera.y==null,
   'absent start axis became zero');
  check(decoded.unsupported.indexOf('stage-extension')>=0
   && decoded.unsupported.indexOf('stage-script')>=0,
   'unresolved runtime dependencies were lost');
  var data:Dynamic=Json.parse(raw);
  Reflect.deleteField(data.slots,'boyfriend');
  check(rejected(data),'incomplete role slots silently defaulted');
  data=Json.parse(raw); Reflect.field(data.slots,'folder/actor').spacingY='7';
  check(rejected(data),'string numeric placement accepted');
  data=Json.parse(raw); data.slots.dad.flip=1;
  check(rejected(data),'numeric flip accepted');
  data=Json.parse(raw); data.slots.dad.x=Math.POSITIVE_INFINITY;
  check(rejected(data),'nonfinite placement accepted');
  data=Json.parse(raw); data.slots.dad.name='different';
  check(rejected(data),'slot identity silently changed');
  data=Json.parse(raw); data.unsupported=[false];
  check(rejected(data),'invalid dependency diagnostic accepted');
 }
}'''
        self._run(source)

    def test_order_preserves_prop_gaps_duplicate_anchors_and_default_role_append(self):
        source = r'''import haxe.Json;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function rejected(value:Dynamic):Bool {
  try { CodenameStagePlacement.fromData(value); return false; }
  catch (_:Dynamic) return true;
 }
 static function main():Void {
  var xml='<stage><sprite name="back" sprite="back"/><character name="Named" x="10"/>'
   + '<unknown/><sprite name="middle" sprite="middle"/><char name="Named" x="20"/>'
   + '<bf flip="false"/><sprite name="front" sprite="front"/></stage>';
  var model=CodenameStagePlacement.parse(xml);
  var order=model.order;
  check(order!=null && order.length==8,'XML/default stage order count');
  check(order[0].kind=='prop' && order[0].ordinal==0 && order[0].key=='0',
   'first prop ordinal');
  check(order[1].kind=='anchor' && order[1].ordinal==1 && order[1].key=='Named',
   'first named anchor');
  check(order[2].kind=='prop' && order[2].ordinal==3 && order[2].key=='3',
   'unsupported XML child ordinal gap');
  check(order[3].kind=='anchor' && order[3].ordinal==4 && order[3].key=='Named',
   'duplicate named anchor removed');
  check(order[4].kind=='anchor' && order[4].ordinal==5 && order[4].key=='boyfriend',
   'role alias anchor key');
  check(order[5].kind=='prop' && order[5].ordinal==6 && order[5].key=='6',
   'post-actor prop order');
  check(order[6].kind=='anchor' && order[6].ordinal==7 && order[6].key=='girlfriend'
   && order[7].kind=='anchor' && order[7].ordinal==8 && order[7].key=='dad',
   'missing roles did not append GF then dad after XML');
  check(model.slots.get('Named').x==20 && !model.slots.get('boyfriend').flip,
   'slot map no longer last-wins');
  check(model.unsupported.indexOf('stage-order-unknown-node')>=0,
   'unknown child order gap not diagnosed');
  var round=CodenameStagePlacement.fromData(Json.parse(Json.stringify(CodenameStagePlacement.toData(model))));
  check(round.order!=null && round.order.length==order.length,'order codec lost records');
  for (i in 0...order.length)
   check(round.order[i].kind==order[i].kind && round.order[i].ordinal==order[i].ordinal
    && round.order[i].key==order[i].key,'order codec changed record '+i);
  var old:Dynamic=CodenameStagePlacement.toData(model);
  Reflect.deleteField(old,'order');
  check(CodenameStagePlacement.fromData(old).order==null,
   'old sidecar invented stage order');
  var data:Dynamic=CodenameStagePlacement.toData(model);
  data.order[2].ordinal=1;
  check(rejected(data),'duplicate ordinal accepted');
  data=CodenameStagePlacement.toData(model); data.order[2].key='wrong';
  check(rejected(data),'mismatched prop key accepted');
  data=CodenameStagePlacement.toData(model); data.order[1].key='other';
  check(rejected(data),'unknown anchor key accepted');
  data=CodenameStagePlacement.toData(model); data.order[1].kind='script';
  check(rejected(data),'unknown order kind accepted');
  data=CodenameStagePlacement.toData(model); data.order[7].ordinal='8';
  check(rejected(data),'non-integer ordinal accepted');
  data=CodenameStagePlacement.toData(model); data.order.pop();
  check(rejected(data),'missing default role anchor accepted');
  var aliases=CodenameStagePlacement.parse('<stage><player/><opponent/>'
   + '<gf/><character name="folder/actor"/><solid name="box" width="10" height="10"/></stage>');
  check(aliases.order[0].key=='boyfriend' && aliases.order[1].key=='dad'
   && aliases.order[2].key=='girlfriend' && aliases.order[3].key=='folder/actor'
   && aliases.order[4].kind=='prop' && aliases.order[4].key=='4'
   && aliases.unsupported.indexOf('stage-order-unconverted-prop')>=0,
   'aliases or unconverted prop order lost');
  var skipped=CodenameStagePlacement.parse('<stage><sprite color="#fff"/>'
   + '<sprite name="valid" sprite="valid"/></stage>');
  check(skipped.order[0].kind=='prop' && skipped.order[0].ordinal==1
   && skipped.unsupported.indexOf('stage-order-skipped-prop')>=0,
   'upstream-skipped prop was assigned a stage order anchor');
  var empty=CodenameStagePlacement.parse('<stage><character name="" x="37"/>'
   + '<character x="99"/></stage>');
  check(CodenameStagePlacement.slotKey(Xml.parse('<character name=""/>').firstElement())=='',
   'explicit empty character name was discarded');
  check(CodenameStagePlacement.slotKey(Xml.parse('<character/>').firstElement())==null,
   'missing character name became an empty named slot');
  check(empty.slots.get('').x==37 && empty.order[0].kind=='anchor'
   && empty.order[0].key=='' && empty.order[0].ordinal==0,
   'empty named stage slot or anchor lost');
  var emptyRound=CodenameStagePlacement.fromData(
   Json.parse(Json.stringify(CodenameStagePlacement.toData(empty))));
  check(emptyRound.slots.get('').x==37 && emptyRound.order[0].key=='',
   'empty named stage slot failed metadata roundtrip');
 }
}'''
        self._run(source)

    def _run(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            path = Path(work)
            (path / "Main.hx").write_text(source, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                                     "-cp", str(path), "--run", "Main"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
