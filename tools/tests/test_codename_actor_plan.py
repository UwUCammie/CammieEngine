"""Execute occurrence identity and the real initial actor-plan loader."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MONSTER_STAGE = (Path("/run/media/cammie/External Storage/FNF-Example-Mods")
                 / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/data/stages/spookyEvil.hx")
GHASTLY_STAGE = (Path("/run/media/cammie/External Storage/FNF-Example-Mods")
                 / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/data/stages/spookyMansion.hx")


def method(source, name):
    start = source.index("\tfunction " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        depth += (source[i] == "{") - (source[i] == "}")
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError(name)


class CodenameActorPlanTest(unittest.TestCase):
    def test_occurrences_selected_owner_and_constructor_orientation(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(method(source, name) for name in (
            "getCodenameScriptPlan", "getCodenameActorPlan", "codenameInitialActorIsPlayer",
            "codenameStageIdentityMatches", "codenameMissingCharacterFallback",
            "codenameSourceFolder", "codenameDifficulty"))
        fixture = r'''
import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CodenameScriptPlan.CodenameScriptPlanData;
class EngineCompat {
 public static function resolveStageAlias(name:String):String
  return name != null && name.toLowerCase()=="halloween" ? "spooky" : name;
}
class FNFAssets {
 public static function exists(path:String):Bool return FileSystem.exists(path);
 public static function getText(path:String):String return File.getContent(path);
}
class Song {public static function storageFolder(chart:Dynamic):String
 return Std.string(Reflect.field(chart,"compatStorageFolder"));}
class Main {
 static var SONG:Dynamic = {song:"Improbable Outset",
  compatStorageFolder:"improbable-outset--codename-engine-1234",stage:"native-stage"};
 var root:String;
 var storyDifficultyText:String="hard";
 var codenameActorPlanChecked=false;
 var cachedCodenameActorPlan:CodenameActorPlan=null;
 var codenamePlanChecked=false;
 var cachedCodenameScriptPlan:CodenameScriptPlanData=null;
 public function new(root:String) {
  this.root=root;
 }
 function codenameSelectedRoot():String return root;
 static function check(ok:Bool, message:String):Void if(!ok) throw message;
''' + methods + r'''
 static function main():Void {
  Sys.setCwd(Sys.args()[0]);
  var root="assets/imported_mods/codename-owner";
  FileSystem.createDirectory("assets");
  FileSystem.createDirectory("assets/imported_mods");
  FileSystem.createDirectory(root);
  FileSystem.createDirectory(root+"/songs");
  FileSystem.createDirectory(root+"/songs/Fixture");
  FileSystem.createDirectory(root+"/data");
  FileSystem.createDirectory(root+"/data/stages");
  var storage=Song.storageFolder(SONG);
  FileSystem.createDirectory("assets/data");
  FileSystem.createDirectory("assets/data/"+storage);
  File.saveContent("assets/data/"+storage+"/importProvenance.json",Json.stringify({
   version:1,sourceFolder:"Fixture",sourceEngine:"Codename Engine",sourceOwner:root,
   destinationFolder:storage}));
  var stage=CodenameStagePlacement.toData(CodenameStagePlacement.parse(
   '<stage><char name="Hero Name" x="10" spacingx="35" flip="false"/>'
   + '<character name="Bambino" x="330"/>'
   + '<dad flip="true"/><girlfriend flip="true"/></stage>'));
  var entry:Dynamic={stage:"authored-stage",nativeStage:"native-stage",lines:[
   {role:"player",type:1,position:null,visible:true,characters:[],keyCount:3,
    strumLinePos:0.65,strumPos:[0,80],strumScale:0.85,strumSpacing:1.25},
   {role:"player",type:1,position:null,visible:false,characters:["Hero Name","Hero Name"]},
   {role:"opponent",type:0,position:null,visible:true,characters:["Foe"]},
   {role:"gf",type:2,position:null,visible:true,characters:["Dancer"]},
   {role:"extra",type:3,position:null,visible:true,characters:["Missing"]},
   {role:"extra",type:3,position:null,visible:true,characters:["Bambino"]}],
   nativeCharacters:{},characters:{},missingCharacters:["Hero Name","Foe","Dancer","Missing"],
   stageOffsets:{},stageOffsetsKnown:true,stagePlacement:stage};
  Reflect.setField(entry.nativeCharacters,"Hero Name","hero-name");
  Reflect.setField(entry.nativeCharacters,"Foe","foe");
  Reflect.setField(entry.nativeCharacters,"Dancer","dancer");
  Reflect.setField(entry.nativeCharacters,"Missing",null);
  Reflect.setField(entry.nativeCharacters,"Bambino","bambino");
  Reflect.setField(entry.characters,"Bambino",{globalX:0.0,globalY:0.0,
   cameraX:0.0,cameraY:0.0,centeredCamera:null,playerOffsets:null});
  var data=CodenameScriptPlan.createCamera("Fixture",{Hard:entry});
  var scripts=CodenameScriptPlan.create("Fixture",{Hard:"authored-stage"});
  File.saveContent(CodenameScriptPlan.metadataPath(root,"Fixture"),CodenameScriptPlan.stringify(scripts));
  var selected=CodenameScriptPlan.selectedCamera(data,"Hard");
  var indexed=new CodenameActorPlan(selected);
  check(indexed.lines.length==6 && indexed.lines[0].characters.length==0
   && indexed.lines[1].visible==false && indexed.lines[4].type==3,
   "empty and hidden authored lines must retain their original indices");
  check(indexed.lines[0].keyCount==3 && indexed.lines[0].strumLinePos==0.65
   && indexed.lines[0].strumPos[1]==80 && indexed.lines[0].strumScale==0.85
   && indexed.lines[0].strumSpacing==1.25,
   "actor plan must retain authored source-line geometry");
  check(indexed.lines[1].keyCount==4 && indexed.lines[1].strumLinePos==0.75
   && indexed.lines[1].strumPos[1]==50 && indexed.lines[1].strumScale==1
   && indexed.lines[1].strumSpacing==1,
   "old sidecar lines must receive deterministic Codename defaults");
  check(indexed.nativeStage=="native-stage" && indexed.stagePlacement!=null,
   "actor plan must retain its verified stage identity and XML model");
  var cameraRoundTrip:Dynamic=Json.parse(CodenameScriptPlan.stringifyCamera(data));
  var cameraLine:Dynamic=cameraRoundTrip.difficulties.Hard.lines[0];
  check(cameraLine.keyCount==3 && cameraLine.strumLinePos==0.65
   && cameraLine.strumPos[1]==80 && cameraLine.strumScale==0.85
   && cameraLine.strumSpacing==1.25,
   "camera sidecar serializer dropped source-line geometry");
  var snapshotInput:Dynamic=Json.parse(Json.stringify(selected));
  var snapshotPlan=new CodenameActorPlan(snapshotInput);
  snapshotInput.lines[1].characters[0]="changed";
  check(snapshotPlan.lines[1].characters[0]=="Hero Name",
   "actor-plan line snapshot aliases mutable input metadata");
  check(indexed.occurrences.length==6,"all occurrences including unresolved");
  check(indexed.occurrences[0]!=indexed.occurrences[1]
   && indexed.occurrences[0].lineIndex==1 && indexed.occurrences[1].occurrenceIndex==1
   && indexed.occurrences[1].placement.x==45,"distinct repeated ID and spacing");
  check(indexed.primaryFor("player","hero-name")==indexed.occurrences[0]
   && indexed.primaryFor("player","Hero Name")==null,"exact mapped primary identity");
  check(indexed.primaryFor("extra","Missing")==null,"unresolved is not guessed");
  var fallbackPlan=new CodenameActorPlan(selected,null,"bf");
  var fallbackOccurrence=fallbackPlan.occurrences[4];
  check(fallbackOccurrence.authoredId=="Missing" && fallbackOccurrence.nativeName=="bf"
   && fallbackOccurrence.sourceFallbackId=="bf",
   "explicit source fallback keeps authored occurrence identity");
  var fallbackPrimary:Dynamic=Json.parse(Json.stringify(selected));
  fallbackPrimary.lines=[{role:"player",type:1,position:null,visible:true,
   characters:["Missing"]}];
  var primaryFallbackPlan=new CodenameActorPlan(fallbackPrimary,null,"bf");
  check(primaryFallbackPlan.primaryFor("player","Missing")==primaryFallbackPlan.occurrences[0]
   && primaryFallbackPlan.primaryFor("player","bf")==primaryFallbackPlan.occurrences[0]
   && primaryFallbackPlan.primaryIdentityMatches("player","Missing")
   && primaryFallbackPlan.primaryIdentityMatches("player","bf")
   && !primaryFallbackPlan.primaryIdentityMatches("player","unrelated"),
   "fallback primary accepts exact authored identity and runtime host identity");
  var importedFallback:Dynamic=Json.parse(Json.stringify(fallbackPrimary));
  importedFallback.nativeCharacters.Missing="bf";
  var importedFallbackPlan=new CodenameActorPlan(importedFallback,null,"bf");
  check(importedFallbackPlan.primaryFor("player","Missing")==importedFallbackPlan.occurrences[0]
   && importedFallbackPlan.occurrences[0].sourceFallbackId=="bf",
   "precomputed importer fallback host keeps authored primary identity");
  var unmarked:Dynamic=Json.parse(Json.stringify(selected));
  unmarked.missingCharacters=[];
  var unmarkedPlan=new CodenameActorPlan(unmarked,null,"bf");
  check(unmarkedPlan.occurrences[4].authoredId=="Missing"
   && unmarkedPlan.occurrences[4].nativeName==null
   && unmarkedPlan.occurrences[4].sourceFallbackId==null,
   "fallback must not invent mappings for IDs absent from source missing diagnostics");
  var nullLine:Dynamic=Json.parse(Json.stringify(selected));
  nullLine.lines.insert(0,null);
  var indexedNull=new CodenameActorPlan(nullLine);
  check(indexedNull.lines.length==7 && indexedNull.lines[0]==null
   && indexedNull.occurrences[0].lineIndex==2
   && indexedNull.primaryFor("player","hero-name").lineIndex==2,
   "null donor line preserves later actor indices");
  var unresolvedFirst:Dynamic=Json.parse(Json.stringify(selected));
  unresolvedFirst.lines[0].characters=["Missing"];
  check(new CodenameActorPlan(unresolvedFirst).primaryFor("player","hero-name")==null,
   "unresolved primary must not borrow a later line");
  var path=CodenameScriptPlan.cameraMetadataPath(root,"Fixture");
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(data));
  var state=new Main(root);
  check(state.codenameSourceFolder(root)=="Fixture",
   "selected provenance must map a presentation title to the source song id");
  check(state.getCodenameScriptPlan()!=null,
   "script plan identity must use source id rather than chart presentation title");
  check(!state.codenameInitialActorIsPlayer("player","hero-name",true),"player named-slot flip");
  check(state.codenameInitialActorIsPlayer("opponent","foe",false),"opponent slot flip");
  check(state.codenameInitialActorIsPlayer("gf","dancer",false),"dancer slot flip");
  check(state.codenameInitialActorIsPlayer("player","edited-native-id",true),"edited chart fallback");
  var cached=state.getCodenameActorPlan();
  SONG.stage="legacy-stage-default";
  SONG.compatStageAuthored=false;
  var inferredStagePlan=new Main(root).getCodenameActorPlan();
  check(inferredStagePlan!=null && SONG.stage=="native-stage",
   "a loader-inferred chart stage must resolve to the selected owner's native stage");
  SONG.stage="native-stage";
  SONG.compatStageAuthored=true;
  File.saveContent(path,"malformed");
  check(state.getCodenameActorPlan()==cached,"one immutable construction snapshot");
  check(new Main(root).getCodenameActorPlan()==null,"malformed new load");
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(data));
  var wrongDiff=new Main(root); wrongDiff.storyDifficultyText="Easy";
  check(wrongDiff.getCodenameActorPlan()==null,"no sibling difficulty fallback");
  var wrongStage=new Main(root); wrongStage.cachedCodenameScriptPlan=CodenameScriptPlan.create("Fixture",{Hard:"other-stage"});
  wrongStage.codenamePlanChecked=true;
  check(wrongStage.getCodenameActorPlan()==null,"authored stage mismatch");
  SONG.stage="edited-stage";
  check(new Main(root).getCodenameActorPlan()==null,"native stage mismatch");
  SONG.stage="native-stage";
  var wrongSource=Json.parse(Json.stringify(data));
  wrongSource.song="other-song";
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(wrongSource));
  check(new Main(root).getCodenameActorPlan()==null,"camera plan must match source id");
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(data));
  var legacy:Dynamic=Json.parse(Json.stringify(data));
  legacy.difficulties.Hard.stagePlacement.unsupported=["stage-script"];
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(legacy));
  var stageSource=root+"/data/stages/authored-stage.hx";
  File.saveContent(stageSource,
   "function postCreate() { camGame.visible = false; boyfriend.shader = shade; }");
  var verified=new Main(root).getCodenameActorPlan();
  check(verified!=null && verified.occurrences.length>0
   && verified.occurrences[0].placement.supported,
   "verified camera/shader-only stage source must recover legacy XML slots");
  File.saveContent(stageSource,"function postCreate() { dad.x += 12; }");
  var mutating=new Main(root).getCodenameActorPlan();
  check(mutating!=null && !mutating.occurrences[2].placement.supported
   && mutating.occurrences[5].placement.supported
   && mutating.staticXmlPlacementForExtras,
   "primary-only stage mutation should preserve its warning and allow unrelated XML slots");
  var liveStageModel=CodenameStagePlacement.fromData(legacy.difficulties.Hard.stagePlacement);
  var liveBambino=mutating.selectStagePlacement(liveStageModel,mutating.occurrences[5]);
  var liveDad=mutating.selectStagePlacement(liveStageModel,mutating.occurrences[2]);
  check(liveBambino.supported && liveBambino.x==330 && !liveDad.supported,
   "current stage selection must exempt only the unrelated XML actor occurrence");
  File.saveContent(stageSource,"function postCreate() { dad.alpha = 0; }\n"
   + "function stepHit(step) { dad.x += 170; }");
  var opacityOnly=new Main(root).getCodenameActorPlan();
  var opacityActorsSupported=opacityOnly!=null;
  if (opacityOnly!=null) for (actor in opacityOnly.occurrences)
   if (!actor.placement.supported) opacityActorsSupported=false;
  check(opacityActorsSupported && opacityOnly.stagePlacement.unsupported.length==0
   && opacityOnly.stagePlacement.runtimeMutationHooks.indexOf("stepHit")>=0,
   "startup opacity should preserve initial slots while stepHit geometry stays recorded");
  if (Sys.args().length > 1) {
   if (Sys.args()[1] != "") {
    var mountedScript=File.getContent(Sys.args()[1]);
    var monsterEntry:Dynamic=Json.parse(Json.stringify(selected));
    monsterEntry.stagePlacement.unsupported=["stage-script"];
    var mountedPlan=new CodenameActorPlan(monsterEntry,mountedScript);
    var monsterActorsSupported=true;
    for (actor in mountedPlan.occurrences)
     if (!actor.placement.supported) monsterActorsSupported=false;
    check(monsterActorsSupported && mountedPlan.stagePlacement.unsupported.length==0
     && mountedPlan.stagePlacement.runtimeMutationHooks.indexOf("stepHit")>=0,
     "mounted spookyEvil alpha startup should preserve slots and track stepHit geometry");
    var mountedBambino=mountedPlan.selectStagePlacement(
     mountedPlan.stagePlacement,mountedPlan.occurrences[5]);
    check(mountedBambino.supported && mountedBambino.x==330,
     "mounted spookyEvil script should preserve Bambino's XML slot");
   }
  }
  if (Sys.args().length > 2 && Sys.args()[2] != "") {
   var ghastlyEntry:Dynamic=Json.parse(Json.stringify(selected));
   ghastlyEntry.stagePlacement.unsupported=["stage-script"];
   var ghastlySource=File.getContent(Sys.args()[2]);
   var ghastlyPlan=new CodenameActorPlan(ghastlyEntry,ghastlySource);
   var ghastlyActorsSupported=true;
   for (actor in ghastlyPlan.occurrences)
    if (!actor.placement.supported) ghastlyActorsSupported=false;
   check(ghastlyActorsSupported && ghastlyPlan.stagePlacement.unsupported.length==0
    && ghastlyPlan.diagnostics.indexOf("stage-script-unclassified-placement-alias")<0,
    "mounted Ghastly indexed opacity writes should preserve primary and extra XML slots");
   var ghastlyDark=ghastlyPlan.selectStagePlacement(
    ghastlyPlan.stagePlacement,ghastlyPlan.occurrences[5]);
   check(ghastlyDark.supported && ghastlyDark.x==330,
    "mounted Ghastly alpha-only source should preserve the selected extra XML slot");
  }
  FileSystem.deleteFile(stageSource);
  var unverified=new Main(root).getCodenameActorPlan();
  check(unverified!=null && !unverified.occurrences[0].placement.supported,
   "missing stage source must not clear the legacy dependency marker");
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(data));
  File.saveContent("assets/data/"+storage+"/importProvenance.json",Json.stringify({
   version:2,sourceFolder:"Fixture",sourceEngine:"Codename Engine",sourceOwner:root,
   destinationFolder:storage}));
  check(new Main(root).codenameSourceFolder(root)=="",
   "unknown provenance versions must not select a source folder");
  var foreign="assets/imported_mods/codename-foreign";
  FileSystem.createDirectory("assets/imported_mods/codename-foreign");
  FileSystem.createDirectory(foreign+"/songs");
  FileSystem.createDirectory(foreign+"/songs/Fixture");
  File.saveContent(foreign+"/songs/Fixture/__cammie_compat_camera.json",
   CodenameScriptPlan.stringifyCamera(data));
  File.saveContent("assets/data/"+storage+"/importProvenance.json",Json.stringify({
   version:1,sourceFolder:"Fixture",sourceEngine:"Codename Engine",sourceOwner:foreign,
   destinationFolder:storage}));
  check(new Main(root).codenameSourceFolder(root)=="",
   "foreign provenance cannot select a donor folder from another owner");
  check(new Main(root).getCodenameActorPlan()==null,
   "foreign camera metadata must stay isolated from selected owner");
  var ambiguous:Dynamic=Json.parse(Json.stringify(data));
  Reflect.setField(ambiguous.difficulties,"HARD",ambiguous.difficulties.Hard);
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(ambiguous));
  var ambiguousState=new Main(root); ambiguousState.storyDifficultyText="hArD";
  check(ambiguousState.getCodenameActorPlan()==null,"ambiguous difficulty casing");
  var unsupported:Dynamic=Json.parse(Json.stringify(data));
  unsupported.difficulties.Hard.stagePlacement.unsupported=["stage-inheritance"];
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(unsupported));
  check(new Main(root).codenameInitialActorIsPlayer("player","hero-name",true),
   "unresolved stage dependencies cannot assert a static orientation");
  Reflect.setField(data.difficulties.Hard,"nativeCharacters",null);
  File.saveContent(path,CodenameScriptPlan.stringifyCamera(data));
  check(new Main(root).getCodenameActorPlan()==null,"old map is unknown");
  FileSystem.deleteFile(path);
  check(new Main(root).getCodenameActorPlan()==null,"missing sidecar");
  check(new Main("").getCodenameActorPlan()==null,"non-Codename owner");
 }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            command = [
                *HAXE_COMMAND, "-cp", str(ROOT / "source"),
                "-cp", str(folder), "--run", "Main", str(folder)]
            command.append(str(MONSTER_STAGE) if MONSTER_STAGE.is_file() else "")
            if GHASTLY_STAGE.is_file():
                command.append(str(GHASTLY_STAGE))
            result = subprocess.run(command, cwd=ROOT,
                env={**os.environ, "TMPDIR": work}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
