"""Execute the authored Codename camera metadata parser in portable Haxe."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CodenameCameraPlanTest(unittest.TestCase):
    def test_existing_sidecar_pair_is_preserved_and_missing_member_is_repaired_safely(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        method = extract_method(module, "static function mergeCodenameRuntimeAssets(")
        stage_match = extract_method(module, "static function codenameMetadataStagesMatch(")
        note_types = extract_method(module, "static function codenameNoteTypesByDifficulty(")
        write_note_types = extract_method(module, "static function writeCodenameNoteTypePlanIfMissing(")
        reconcile = extract_method(module, "static function reconcileCodenameOwnerMetadata(")
        owner_label = extract_method(module, "static function importOwnerDisplayLabel(")
        fixture = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef SongImport = {var sourceRoot:String; var engine:String; @:optional var sourceFolder:String;
 @:optional var sourceModName:String; @:optional var convertedCharts:Array<Dynamic>;};
typedef ImportAssetMergeResult = {var copied:Int; var skipped:Int; var failed:Int; var errors:Array<String>;};
class Main {
 static function importWorkCancelled():Bool return false;
 static function codenameRuntimeFiles(song:SongImport):Array<{source:String,relative:String,?content:String,?family:String}>
  return [{source:Path.join([song.sourceRoot,"script.hx"]),relative:"songs/Source Song/scripts/script.hx",content:null}];
 static function writeImportContentNonOverwriting(content:String,dest:String,result:ImportAssetMergeResult):Void {
  if (FileSystem.exists(dest)) { result.skipped++; return; }
  ensureDirectory(Path.directory(dest)); File.saveContent(dest,content); result.copied++;
 }
 static function copyImportFileNonOverwriting(source:String,dest:String,result:ImportAssetMergeResult):Void {
  if (FileSystem.exists(dest)) { result.skipped++; return; }
  ensureDirectory(Path.directory(dest)); File.saveContent(dest,File.getContent(source)); result.copied++;
 }
 static function ensureDirectory(path:String):Void {
  if (path==null || path=="" || FileSystem.exists(path)) return;
  var parent=Path.directory(path);
  if(parent!=null && parent!="" && parent!=path) ensureDirectory(parent);
  FileSystem.createDirectory(path);
 }
''' + owner_label + '\n' + stage_match + '\n' + note_types + '\n' + write_note_types + '\n' + reconcile + '\n' + method + '''
 static function main():Void {
  var stages:Dynamic={}; Reflect.setField(stages,"Hard Mode","stageA");
  var lines:Array<Dynamic>=[{role:"player",type:1,position:"boyfriend",visible:true,
   characters:["hero"]}];
  var chars:Dynamic={}; Reflect.setField(chars,"hero",{globalX:0,globalY:1,cameraX:2,cameraY:3});
  var diffs:Dynamic={}; Reflect.setField(diffs,"Hard Mode",{stage:"stageA",lines:lines,
   characters:chars,stageOffsets:{bf:{cameraX:4,cameraY:5}},
   missingCharacters:[],stageOffsetsKnown:true});
  var song:SongImport={sourceRoot:Sys.args()[0],engine:"Codename Engine",sourceFolder:"Source Song"};
  Reflect.setField(song,"codenameAuthoredStages",stages);
  Reflect.setField(song,"codenameAuthoredCamera",diffs);
  Reflect.setField(song,"codenameOriginalMeta",{displayName:"Source Display",
   customValues:{chapter:7,flags:([true,"authored"]:Array<Dynamic>)}});
  var resolvedEntries:Dynamic={};
  Reflect.setField(resolvedEntries,"Hard Mode",{selectedFile:"meta.json",
   fileMeta:{displayName:"Source Display",customValues:{chapter:7}},inlineMeta:null});
  Reflect.setField(song,"codenameResolvedMeta",CodenameSongMetadata.createResolved(
   "Source Song",["Hard Mode"],resolvedEntries));
  var root=CompatScriptManifest.destinationRoot(song.sourceRoot,song.engine);
  var stage=CodenameScriptPlan.metadataPath(root,"Source Song");
  var camera=CodenameScriptPlan.cameraMetadataPath(root,"Source Song");
  var songMeta=CodenameSongMetadata.path(root,"Source Song");
  var resolvedMeta=CodenameSongMetadata.resolvedPath(root,"Source Song");
  var script=Path.join([root,"songs/Source Song/scripts/script.hx"]);
  var first=mergeCodenameRuntimeAssets(song);
  if(first.failed!=0 || !FileSystem.exists(stage) || !FileSystem.exists(camera)
    || !FileSystem.exists(songMeta) || !FileSystem.exists(resolvedMeta)
    || !FileSystem.exists(script))
   throw "new metadata missing: " + first.errors.join(" | ");
  var original=CodenameSongMetadata.parse(File.getContent(songMeta),"Source Song");
  if(original.meta.displayName!="Source Display" || original.meta.customValues.chapter!=7)
   throw "original song metadata lost";
  if(CodenameSongMetadata.selectedResolved(CodenameSongMetadata.parseResolved(
   File.getContent(resolvedMeta),"Source Song"),"Hard Mode").customValues.chapter!=7)
   throw "resolved song metadata lost";
  if(CodenameScriptPlan.selectedCamera(CodenameScriptPlan.parseCamera(File.getContent(camera)),"Hard Mode")==null)
   throw "difficulty missing";
  var generatedStage=File.getContent(stage);
  var generatedCamera=File.getContent(camera);
  File.saveContent(stage,"stale stage plan");
  File.saveContent(camera,"custom camera plan");
  File.saveContent(resolvedMeta,"custom resolved meta plan");
  File.saveContent(script,"custom script");
  var second=mergeCodenameRuntimeAssets(song);
  if(second.failed!=0 || second.copied!=0 || second.skipped<2
   || File.getContent(stage)!="stale stage plan"
   || File.getContent(camera)!="custom camera plan"
   || File.getContent(resolvedMeta)!="custom resolved meta plan"
   || File.getContent(script)!="custom script") throw "existing paired sidecars were overwritten";
  FileSystem.deleteFile(camera);
  var blockedRepair=mergeCodenameRuntimeAssets(song);
  if(blockedRepair.failed!=0 || FileSystem.exists(camera)
   || File.getContent(stage)!="stale stage plan")
   throw "a missing pair member was generated beside a differing existing sidecar";
  File.saveContent(stage,generatedStage);
  var repair=mergeCodenameRuntimeAssets(song);
  if(repair.failed!=0 || File.getContent(stage)!=generatedStage
   || File.getContent(script)!="custom script"
   || File.getContent(camera)!=generatedCamera)
   throw "paired camera repair failed";
  FileSystem.deleteFile(stage);
  var scriptRepair=mergeCodenameRuntimeAssets(song);
  if(scriptRepair.failed!=0 || File.getContent(stage)!=generatedStage
   || File.getContent(camera)!=generatedCamera)
   throw "paired script repair failed";
  FileSystem.deleteFile(songMeta);
  var metaRepair=mergeCodenameRuntimeAssets(song);
  if(metaRepair.failed!=0 || File.getContent(camera)!=generatedCamera
   || File.getContent(resolvedMeta)!="custom resolved meta plan"
   || File.getContent(script)!="custom script"
   || CodenameSongMetadata.parse(File.getContent(songMeta),"Source Song").meta.customValues.chapter!=7)
   throw "missing-only original meta repair failed";
  FileSystem.deleteFile(resolvedMeta);
  var resolvedRepair=mergeCodenameRuntimeAssets(song);
  if(resolvedRepair.failed!=0 || File.getContent(camera)!=generatedCamera
   || File.getContent(script)!="custom script"
   || CodenameSongMetadata.selectedResolved(CodenameSongMetadata.parseResolved(
    File.getContent(resolvedMeta),"Source Song"),"Hard Mode").customValues.chapter!=7)
   throw "missing-only resolved meta repair failed";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture)
            donor = folder / "donor"
            donor.mkdir()
            (donor / "script.hx").write_text("authored script")
            result = subprocess.run([str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                                     "-cp", str(folder), "--run", "Main", str(donor)], cwd=folder,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strumline_indices_offsets_and_exact_difficulties(self):
        source = r'''import haxe.Json;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function rejects(raw:String):Bool {
  try { CodenameScriptPlan.parseCamera(raw); return false; }
  catch (_:Dynamic) return true;
 }
 static function main():Void {
  var chart:Dynamic={strumLines:[
   {type:0,position:"dad",visible:false,characters:["Same", "Same"],notes:[]},
   {type:1,position:"dad",characters:["Other"],notes:[]},
   {type:2,position:"girlfriend",characters:[],notes:[]}
  ]};
  var lines=CodenameImporter.cameraStrumlines(chart);
  check(lines.length==3 && lines[0].role=="opponent" && lines[0].visible==false
   && lines[0].characters.length==2 && lines[1].role=="player"
   && lines[1].position=="dad" && lines[2].role=="gf", "authored indices");
  var character=CodenameImporter.cameraCharacterOffsets('<character x="-22" y="10" camx="4" camy="-3" centercam="false" isPlayer="true"/>');
  check(character.globalX==-22 && character.globalY==10 && character.cameraX==4
   && character.cameraY==-3 && character.centeredCamera==false && character.playerOffsets==true,
   "character camera XML");
  var unspecified=CodenameImporter.cameraCharacterOffsets('<character/>');
  check(unspecified.centeredCamera==null && unspecified.playerOffsets==null,
   "absent camera booleans must remain unresolved");
  var stageInfo=CodenameImporter.cameraStageInfo('<stage startCamPosX="0" startCamPosY="275"><dad camxoffset="7" camyoffset="8"/>'
   + '<boyfriend camxoffset="-2"/></stage>');
  var stage=stageInfo.offsets;
  check(stage.dad.cameraX==7 && stage.dad.cameraY==8 && stage.bf.cameraX==-2,
   "stage camera XML");
  var namedStage=CodenameImporter.cameraStageOffsets('<stage><dad camxoffset="1"/>'
   + '<opponent camxoffset="2"/><char name="extra" camxoffset="99"/>'
   + '<player camyoffset="3"/></stage>');
  check(namedStage.dad.cameraX==2 && namedStage.bf.cameraY==3,
   "role aliases/last placeholder wins; named actors must not overwrite dad");
  check(stageInfo.startCamera.x==0 && stageInfo.startCamera.y==275,
   "authored stage starting camera");
  check(CodenameImporter.cameraStageInfo('<stage/>').startCamera.x==null,
   "absent stage starting camera must remain unresolved");
  var invalidXml=false;
  try CodenameImporter.cameraCharacterOffsets('<character centercam="yes"/>')
  catch (_:Dynamic) invalidXml=true;
  check(invalidXml, "invalid centercam accepted");
  var defs:Dynamic={};
  var chars:Dynamic={}; Reflect.setField(chars,"Same",character);
  var entry:Dynamic={stage:"authoredStage",lines:lines,characters:chars,
   missingCharacters:["Other"],stageOffsets:stage,stageOffsetsKnown:true,
   stageStartCamera:stageInfo.startCamera,stagePlacement:stageInfo.placement};
  Reflect.setField(defs,"Hard Mode",entry);
  var plan=CodenameScriptPlan.createCamera("Source Song",defs);
  var parsed=CodenameScriptPlan.parseCamera(CodenameScriptPlan.stringifyCamera(plan));
  var selected=CodenameScriptPlan.selectedCamera(parsed,"Hard Mode");
  check(selected!=null && selected.lines[0].characters[1]=="Same"
   && selected.stage=="authoredStage" && selected.stageOffsets.dad.cameraX==7
   && selected.stageStartCamera.y==275 && selected.characters.Same.centeredCamera==false
   && selected.characters.Same.playerOffsets==true,
   "serialized camera plan");
  check(selected.stagePlacement!=null
   && CodenameStagePlacement.fromData(selected.stagePlacement).slots.exists("boyfriend"),
   "full stage placement metadata was discarded");
  var manyLines:Array<Dynamic>=[];
  for (i in 0...70) manyLines.push({role:"extra",type:i,position:"p",visible:true,characters:[]});
  Reflect.setField(defs,"Large",{stage:"authoredStage",lines:manyLines,characters:{},
   missingCharacters:[],stageOffsets:{},stageOffsetsKnown:false});
  check(CodenameScriptPlan.selectedCamera(CodenameScriptPlan.createCamera("Source Song",defs),"Large").lines.length==70,
   "valid authored strumline count was capped");
  check(CodenameScriptPlan.selectedCamera(parsed,"hard mode")==null,
   "difficulty alias fell through");
  var nullableLines=CodenameImporter.cameraStrumlines({strumLines:[
   {type:0,characters:[]},{type:1,position:"",characters:[]}]});
  Reflect.setField(defs,"Nullable",{stage:"authoredStage",lines:nullableLines,characters:{},
   missingCharacters:[],stageOffsets:{},stageOffsetsKnown:false});
  var nullablePlan=CodenameScriptPlan.parseCamera(CodenameScriptPlan.stringifyCamera(
   CodenameScriptPlan.createCamera("Source Song",defs)));
  var nullableSelected=CodenameScriptPlan.selectedCamera(nullablePlan,"Nullable");
  check(nullableSelected.lines[0].position==null && nullableSelected.lines[1].position=="",
   "absent and explicit empty stage positions were conflated");
  var skipped=CodenameImporter.cameraStrumlines({strumLines:[null,
   {type:1,characters:["hero"]}]});
  check(skipped.length==2 && skipped[0]==null && skipped[1].characters[0]=="hero",
   "null donor strumline lost its source index");
  Reflect.setField(defs,"Skipped",{stage:"authoredStage",lines:skipped,characters:{},
   missingCharacters:["hero"],stageOffsets:{},stageOffsetsKnown:false});
  var skippedPlan=CodenameScriptPlan.selectedCamera(CodenameScriptPlan.parseCamera(
   CodenameScriptPlan.stringifyCamera(CodenameScriptPlan.createCamera("Source Song",defs))),"Skipped");
  check(skippedPlan.lines[0]==null && skippedPlan.lines[1].characters[0]=="hero",
   "nullable line changed during metadata roundtrip");
  check(nullableSelected.stagePlacement==null,"old metadata invented stage placement");
  var malformed:Dynamic=Json.parse(CodenameScriptPlan.stringifyCamera(plan));
  Reflect.field(malformed.difficulties,"Hard Mode").stagePlacement={};
  check(rejects(Json.stringify(malformed)),"malformed full placement accepted");
  check(CodenameScriptPlan.cameraMetadataPath("owned","Source Song")
   =="owned/songs/Source Song/__cammie_compat_camera.json", "camera path");
  check(CodenameScriptPlan.parse('{"version":1,"song":"Source Song","stages":{}}').song
   =="Source Song", "old stage plan changed");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[{"role":"player","type":1,"position":"","visible":true,"characters":["Other"]}],"characters":{},"missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":false}}}'),
   "unresolved character was silently accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":{"Other":{"globalX":0,"globalY":0,"cameraX":1e999,"cameraY":0}},"missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":false}}}'),
   "nonfinite offset accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":{"Other":{"globalX":0,"globalY":0,"cameraX":0,"cameraY":0,"playerOffsets":"true"}},"missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":false}}}'),
   "nonnative playerOffsets hint accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":{},"missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":true,"stageStartCamera":{"x":"12","y":null}}}}'),
   "string stage starting camera accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":"hard"}'),
   "scalar difficulty map accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":"bad","missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":true}}}'),
   "scalar character map accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":{},"missingCharacters":[],"stageOffsets":"bad","stageOffsetsKnown":true}}}'),
   "scalar stage offset map accepted");
  check(rejects('{"version":1,"song":"Source Song","difficulties":{"hard":{"stage":"s","lines":[],"characters":{},"missingCharacters":[],"stageOffsets":{},"stageOffsetsKnown":true,"stageStartCamera":"bad"}}}'),
   "scalar stage start camera accepted");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(source)
            result = subprocess.run([str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                                     "-cp", str(folder), "--run", "Main"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
