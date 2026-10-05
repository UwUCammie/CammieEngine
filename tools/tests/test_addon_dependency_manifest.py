"""Execute addon dependency preparation and manifest publication from production."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def method(text, name):
    start = text.index('static function ' + name + '(')
    brace = text.index('{', start)
    depth = 0
    for end in range(brace, len(text)):
        if text[end] == '{': depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0: return text[start:end+1]
    raise AssertionError(name)


class AddonDependencyManifestTest(unittest.TestCase):
    def test_preparation_and_staged_manifest_preserve_selected_owner(self):
        source=(ROOT/'source/ModuleFunctions.hx').read_text()
        methods=method(source,'prepareInstalledDependencyRoots')+'\n'+method(source,'writeCompatScriptManifest')
        fixture=r'''
import haxe.io.Path;
import ImportFileSystem as FileSystem;
import ImportFile as File;
import CompatScriptManifest.CompatScriptManifestData;
typedef SongImport={var sourceRoot:String;var engine:String;var diffFiles:Array<String>;@:optional var diagnostics:Array<String>;}
typedef ImportAssetMergeResult={var copied:Int;var skipped:Int;var failed:Int;}
class Main {
METHODS
static function readSongChart(path:String):Dynamic return haxe.Json.parse(File.getContent(path));
static function compatScriptManifestPath(song:Dynamic):String return "assets/data/addon/compatScripts.json";
static function ensureDirectory(path:String):Void FileSystem.createDirectory(path);
static function reportImportProgress(a:String,b:String,c:Int,d:Int,e:Int,f:Int,g:Int,h:Int):Void {}
static function main(){
 var install=Sys.args()[0]; Sys.setCwd(install);
 sys.FileSystem.createDirectory("assets/data");
 sys.io.File.saveContent("assets/data/baseSongKeys.json","[]");
 sys.FileSystem.createDirectory("donor");
 sys.io.File.saveContent("donor/chart.json",'{"song":{"stage":"room"}}');
 var donor=Sys.getCwd()+"/donor";
 var song:Dynamic={sourceRoot:donor,engine:ImportEngine.PSYCH,diffFiles:[donor+"/chart.json",donor+"/chart.json"],diagnostics:[]};
 prepareInstalledDependencyRoots(song,donor,ImportEngine.PSYCH);
 if(song.installedDependencyRoots.length!=1 || song.diagnostics.length!=1) throw "provider/diagnostic not deduplicated";
 var selected=CompatScriptManifest.destinationRoot(donor,ImportEngine.PSYCH);
 var stage=Sys.getCwd()+"/import-cache/staging/test";
 var io=ImportIO.begin(Sys.getCwd(),stage);
 var first=writeCompatScriptManifest(song);
 if(first.failed!=0 || first.copied!=2) throw "thin owner and manifest were not counted";
 var paths=io.writtenPaths();
 if(paths.length!=2 || paths.indexOf(selected+"/.cammie-owner.json")<0) throw "unexpected owner output/media duplication";
 var encoded=File.getContent("assets/data/addon/compatScripts.json");
 var manifest=CompatScriptManifest.parse(encoded);
 var roots=CompatScriptManifest.rootsInPrecedence(manifest);
 if(manifest.selectedRoot!=selected || roots.length!=2 || roots[0].path!=selected || roots[1].path!="assets/imported_mods/base" || roots[1].dependency!=true) throw "selected addon/provider precedence lost";
 if(encoded.indexOf(donor)>=0 || encoded.indexOf("import-cache/sources")>=0) throw "donor/retained path persisted";
 if(FileSystem.stat("assets/data/addon/compatScripts.json").size!=haxe.io.Bytes.ofString(encoded).length) throw "manifest byte count differs";
 var marker=File.getContent(selected+"/.cammie-owner.json");
 if(FileSystem.stat(selected+"/.cammie-owner.json").size!=haxe.io.Bytes.ofString(marker).length) throw "owner marker byte count differs";
 var repeat=writeCompatScriptManifest(song);
 if(repeat.copied!=0 || repeat.skipped!=1) throw "repeat import rewrote stable manifest";
 io.setNamespace(donor+"/base",ImportEngine.PSYCH,"base");
 if(ImportSongOwnership.conflict("assets/data/addon",donor+"/base",ImportEngine.PSYCH)==null) throw "declared base adopted addon";
 ImportIO.end();
 if(sys.FileSystem.exists(selected) || sys.FileSystem.exists("assets/data/addon/compatScripts.json")) throw "staging leaked into install";
 // Existing owner bytes are preserved; the missing small provenance marker is materialized.
 sys.FileSystem.createDirectory(selected);
 sys.io.File.saveContent(selected+"/existing.txt","preserve");
 var direct=writeCompatScriptManifest(song);
 if(direct.copied!=2 || !sys.FileSystem.exists(selected+"/.cammie-owner.json") || sys.io.File.getContent(selected+"/existing.txt")!="preserve") throw "existing owner overwritten/missing marker";
 var markerBefore=sys.io.File.getContent(selected+"/.cammie-owner.json");
 if(writeCompatScriptManifest(song).copied!=0 || sys.io.File.getContent(selected+"/.cammie-owner.json")!=markerBefore) throw "existing marker rewritten";
 if(ImportSongOwnership.conflict("assets/data/addon",donor,ImportEngine.PSYCH)!=null) throw "declared base relationship blocked addon";
 if(ImportSongOwnership.conflict("assets/data/addon",donor+"/other",ImportEngine.PSYCH)==null) throw "foreign base adopted addon";
 var spoof=CompatScriptManifest.parse(haxe.Json.stringify({version:1,selectedRoot:"assets/imported_mods/base",roots:[{engine:ImportEngine.PSYCH,path:selected},{engine:ImportEngine.PSYCH,path:"assets/imported_mods/base",dependency:true}]}));
 if(CompatScriptManifest.selectedRoot(spoof)=="assets/imported_mods/base") throw "dependency selected-owner spoof accepted";
 var ownerless=CompatScriptManifest.parse('{"version":1,"roots":[{"engine":"Psych Engine","path":"assets/imported_mods/base","dependency":true}]}');
 if(ownerless.roots.length!=0) throw "ownerless dependency survived";
 manifest.roots[1].dependency=null;
 sys.io.File.saveContent("assets/data/addon/compatScripts.json",CompatScriptManifest.stringify(manifest));
 if(ImportSongOwnership.conflict("assets/data/addon",donor,ImportEngine.PSYCH)==null) throw "legacy mixed chart owner adopted";
 var native:Dynamic={sourceRoot:donor,engine:"Native",diffFiles:[]};
 prepareInstalledDependencyRoots(native,donor,"Native");
 if(Reflect.hasField(native,"installedDependencyRoots")) throw "native adopted source dependencies";
}
}
'''.replace('METHODS',methods)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            folder=Path(temp)
            (folder/'Main.hx').write_text(fixture)
            (folder/'CoolUtil.hx').write_text('class CoolUtil {public static function stringifyJson(v:Dynamic):String return haxe.Json.stringify(v);}')
            (folder/'ImportInstalledDependencyRoots.hx').write_text(r'''class ImportInstalledDependencyRoots {
public static function resolve(s:String,e:String,c:Dynamic):{providers:Array<{root:String,owner:String,engine:String}>,diagnostics:Array<String>} return {providers:[{root:"import-cache/sources/retained/content/base",owner:"assets/imported_mods/base",engine:e}],diagnostics:["fixture diagnostic"]};
}''')
            install=folder/'install';install.mkdir()
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(folder),'--run','Main',str(install)],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_inspect_chart_provider_stage_wiring_executes(self):
        source=(ROOT/'source/ImportWorkflow.hx').read_text()
        start=source.index('var stageCandidatesForChart = stageCandidates(roots, stage);')
        end=source.index('var psychStageCandidates = stageCandidatesForChart.copy();',start)
        block=source[start:end]
        main=r'''class Main {
static function uniquePush(a:Array<String>,s:String):Void if(a.indexOf(s)<0) a.push(s);
static function stageCandidates(a:Array<String>,s:String):Array<String> return [for(r in a) r+"/stages/"+s+".lua"];
static function main(){
 var roots=["addon"];var stage="room";var dependencyRoots=["addon"];
 var plannedSong:Dynamic={installedDependencyRoots:[{owner:"assets/imported_mods/base"},{owner:"assets/imported_mods/base"}]};
BLOCK
 if(implementationRoots.length!=2 || implementationRoots[0]!="addon" || implementationRoots[1]!="assets/imported_mods/base") throw "stage implementation scope missing or duplicated";
 if(dependencyRoots.length!=2 || stageCandidatesForChart.length!=2 || stageCandidatesForChart[1]!="assets/imported_mods/base/stages/room.lua") throw "base stage dependency omitted";
 if(roots.length!=1) throw "selected chart roots mutated";
}
}'''.replace('BLOCK',block)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            folder=Path(temp);(folder/'Main.hx').write_text(main)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(folder),'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
