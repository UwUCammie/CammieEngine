"""Execute the real complete-song branch without rewriting chart/audio."""

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


class CodenameCompleteSongRepairTest(unittest.TestCase):
    def test_complete_song_repairs_owner_only_and_preserves_chart(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        function = module.index("static public function importSongsFromPath(sourcePath:String")
        start = module.index("\t\tvar seenNames:Map<String, Bool>", function)
        end = module.index("\t\tvar assetFailures = 0;", start)
        song_loop = module[start:end]
        runtime_start = module.index("\t\tfor (songData in importedSongs)\n\t\t\tif (songData != null && songData.engine == ImportEngine.CODENAME)", end)
        runtime_end = module.index("\t\t// Psych charts refer", runtime_start)
        runtime_loop = module[runtime_start:runtime_end]
        owner_label = extract_method(module, "static function importOwnerDisplayLabel(")
        fixture = r'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongImport = {var name:String; var sourceRoot:String; var engine:String;
 @:optional var display:String; @:optional var diagnostics:Array<String>;
 @:optional var destinationFolder:String; @:optional var sourceDuplicate:Bool;
 @:optional var sourceModName:String; @:optional var importSourceInfo:SongImportSource;}
typedef SongImportSource = {var song:String; var data:String; var destination:String;
 @:optional var sourceRoot:String; @:optional var engine:String;}
typedef ImportAssetMergeResult = {var copied:Int; var skipped:Int; var failed:Int;
 @:optional var errors:Array<String>;}
class Main {
 static var importCalls:Int=0;
 static function check(ok:Bool, reason:String):Void if (!ok) throw reason;
 static function validModuleName(name:String):Bool return name != null && StringTools.trim(name) != '';
 static function importWorkCancelled():Bool return false;
 static function markImportCancelled(_:Dynamic):Void {}
 static function reportImportProgress(phase:String, current:String, completed:Int=0,
  total:Int=0, copied:Int=0, skipped:Int=0, failed:Int=0, work:Int=0):Void {}
 static function existingImportChild(parent:String, name:String):String return Path.join([parent,name]);
 static function importSongFolderName(song:SongImport):String {
  return song.destinationFolder == null || song.destinationFolder == '' ? song.name : song.destinationFolder;
 }
 static function songTargetExists(name:String, folder:String):Bool return FileSystem.exists('assets/data/'+folder+'/'+folder+'.json');
 static function songNeedsRepair(song:SongImport):Bool return false;
 static function importSong(song:SongImport):Bool { importCalls++; throw 'chart import called'; }
 static function mergeFile(path:String, content:String, result:ImportAssetMergeResult):Void {
  if (FileSystem.exists(path)) {result.skipped++; return;}
  var folder=Path.directory(path);
  if (!FileSystem.exists(folder)) FileSystem.createDirectory(folder);
  File.saveContent(path,content); result.copied++;
 }
 static function importVSliceVisuals(song:SongImport):ImportAssetMergeResult {
  var result:ImportAssetMergeResult={copied:0,skipped:0,failed:0,errors:[]};
  var owner=CompatScriptManifest.destinationRoot(song.sourceRoot,song.engine);
  mergeFile(owner+'/images/custom_stages/dorm.hscript','generated stage',result);
  mergeFile(owner+'/images/custom_chars/hero.hscript','generated character',result);
  return result;
 }
 static function mergeCodenameRuntimeAssets(song:SongImport):ImportAssetMergeResult {
  var result:ImportAssetMergeResult={copied:0,skipped:0,failed:0,errors:[]};
  var owner=CompatScriptManifest.destinationRoot(song.sourceRoot,song.engine);
  mergeFile(owner+'/songs/'+song.name+'/__cammie_compat_camera.json','generated camera',result);
  return result;
 }
''' + owner_label + r'''
 static function run(songs:Array<SongImport>):Dynamic {
  var result:Dynamic={found:songs.length,imported:0,importedSongs:[],skipped:0,
   failed:0,copiedAssets:0,skippedAssets:0,errors:[]};
  var importedSources:Map<String, Dynamic> = new Map<String, Dynamic>();
''' + song_loop + r'''
  var assetFailures=0;
''' + runtime_loop + r'''
  result.failed += assetFailures;
  return result;
 }
 static function manifest(song:SongImport):Void {
  var folder='assets/data/'+song.name;
  FileSystem.createDirectory(folder);
  File.saveContent(folder+'/'+song.name+'.json','{"song":{"notes":[],"userEdit":"keep exactly"}}');
  File.saveContent(folder+'/compatScripts.json',CompatScriptManifest.stringify(
   CompatScriptManifest.create(song.sourceRoot,song.engine)));
 }
 static function main():Void {
  var codename:SongImport={name:'song',sourceRoot:Sys.getCwd()+'/donor-a',engine:ImportEngine.CODENAME};
  var vslice:SongImport={name:'vs',sourceRoot:Sys.getCwd()+'/donor-v',engine:ImportEngine.V_SLICE};
  FileSystem.createDirectory('assets'); FileSystem.createDirectory('assets/data');
  File.saveContent('assets/data/baseSongKeys.json','[]');
  FileSystem.createDirectory('donor-a'); FileSystem.createDirectory('donor-v');
  manifest(codename); manifest(vslice);
  var chart='assets/data/song/song.json'; var original=File.getContent(chart);
  var owner=CompatScriptManifest.destinationRoot(codename.sourceRoot,codename.engine);
  FileSystem.createDirectory('assets/imported_mods'); FileSystem.createDirectory(owner);
  FileSystem.createDirectory(owner+'/songs'); FileSystem.createDirectory(owner+'/songs/song');
  File.saveContent(owner+'/songs/song/scripts.hx','custom retained script');
  var first=run([codename,vslice]);
  check(first.imported==0 && first.skipped==2 && first.failed==0 && importCalls==0,
   'complete song entered chart importer or changed accounting');
  check(first.copiedAssets==5, 'missing-only visual/runtime merges did not run');
  check(File.getContent(chart)==original && File.getContent(owner+'/songs/song/scripts.hx')=='custom retained script',
   'edited chart or custom script changed');
  File.saveContent(owner+'/images/custom_stages/dorm.hscript','custom stage');
  var second=run([codename,vslice]);
  check(second.imported==0 && second.skipped==2 && second.failed==0 && second.copiedAssets==0,
   'duplicate import was not idempotent');
  check(File.getContent(chart)==original && File.getContent(owner+'/images/custom_stages/dorm.hscript')=='custom stage',
   'duplicate import overwrote edited bytes');
  var foreign:SongImport={name:'song',sourceRoot:Sys.getCwd()+'/donor-other',engine:ImportEngine.CODENAME};
  FileSystem.createDirectory('donor-other');
  var foreignOwner=CompatScriptManifest.destinationRoot(foreign.sourceRoot,foreign.engine);
  var rejected=run([foreign]);
  check(rejected.failed==1 && rejected.imported==0 && rejected.skipped==0
   && !FileSystem.exists(foreignOwner) && File.getContent(chart)==original,
   'foreign owner repaired or mutated existing song');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
