from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f'unclosed method: {signature}')


class PsychAddLuaScriptTest(unittest.TestCase):
    def test_scoped_resolution_duplicate_rules_and_child_lifecycle(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        extracted = '\n'.join(method(play, signature) for signature in (
            'function compatibleScriptIdentity(path:String):String',
            'function compatibleScriptKey(scope:String):String',
            'function resolvePsychLuaScriptPath(requested:String, ?callerPath:String):Null<String>',
            'function compatAddLuaScript(luaFile:String',
            'function compatScriptRunning(identity:String):Bool',
            'function compatRemoveLuaScript(luaFile:String',
        ))
        extracted = extracted.replace('function resolvePsychLuaScriptPath(',
                                      'public function resolvePsychLuaScriptPath(', 1)
        extracted = extracted.replace('function compatAddLuaScript(',
                                      'public function compatAddLuaScript(', 1)
        extracted = extracted.replace('function compatRemoveLuaScript(',
                                      'public function compatRemoveLuaScript(', 1)
        self.assertIn('interp.variables.set("flashingLights", OptionsHandler.options.flashingLights);', play)
        self.assertIn('return compatAddLuaScript(luaFile, ignoreAlreadyRunning, path + filename)', play)
        self.assertIn('return compatRemoveLuaScript(luaFile, path + filename)', play)
        self.assertIn("interp != null && interp.variables.get('__compatClosed') == true", play)
        self.assertIn('callHscript("createPost", [], usehaxe, true);', play)
        files = {
            'CompatScriptManifest.hx': '''class CompatScriptManifest {
                public static function selectedRoot(manifest:Dynamic):String return "scoped";
            }''',
            'FNFAssets.hx': '''class FNFAssets {
                public static var existing:Map<String,Bool>=new Map();
                public static function isInScope(path:String):Bool return true;
                public static function exists(path:String):Bool return existing.exists(path);
            }''',
            'PsychHost.hx': '''import haxe.io.Path;
            using StringTools;
            class CompatInterp {
                public var variables:Map<String,Dynamic>=new Map();
                public function new(){}
            }
            typedef Interp = CompatInterp;
            class PsychHost {
                public var loadedCompatScriptPaths:Map<String,Bool>=new Map();
                public var loadingPsychLuaScriptPaths:Map<String,Bool>=new Map();
                public var compatScriptScopes:Map<String,Array<{scope:String,interp:CompatInterp,path:String}>>=new Map();
                public var hscriptStates:Map<String,CompatInterp>=new Map();
                public var psychCompatScriptIndex=0;
                public var loaded:Array<String>=[];
                public var recursiveRejected=0;
                public function new(){}
                function compatForeignScriptRoots():Array<String> return ["scoped","other"];
                function currentSongDataFolder():String return "assets/data/song";
                function getCompatScriptManifest():Dynamic return {};
                function makeHaxeState(scope:String, folder:String, file:String):Void {
                    var path=folder+file;
                    if (path=="scoped/epicScripts/cam.lua"
                        && !compatAddLuaScript("epicScripts/cam",true)) recursiveRejected++;
                    loaded.push(scope+":"+path+":start:createPost");
                    var identity=compatibleScriptIdentity(path);
                    loadedCompatScriptPaths.set(identity,true);
                    var scopes=compatScriptScopes.get(identity);
                    if(scopes==null) { scopes=[]; compatScriptScopes.set(identity,scopes); }
                    var interp=new CompatInterp();
                    scopes.push({scope:scope,interp:interp,path:Path.normalize(path).toLowerCase()});
                    hscriptStates.set(scope,interp);
                }
                __METHODS__
            }'''.replace('__METHODS__', extracted),
            'PsychLoadTest.hx': '''import PsychHost.CompatInterp;
            class PsychLoadTest {
                static function check(ok:Bool,label:String):Void if(!ok) throw label;
                static function main():Void {
                    FNFAssets.existing.set("scoped/epicScripts/cam.lua",true);
                    FNFAssets.existing.set("assets/epicScripts/cam.lua",true);
                    FNFAssets.existing.set("assets/epicScripts/infishake.lua",true);
                    FNFAssets.existing.set("other/epicScripts/stale.lua",true);
                    var host=new PsychHost();
                    check(host.resolvePsychLuaScriptPath("epicScripts/cam") ==
                        "scoped/epicScripts/cam.lua", "selected root did not win");
                    check(host.resolvePsychLuaScriptPath("epicScripts/infishake") ==
                        "assets/epicScripts/infishake.lua", "native fallback missing");
                    check(host.resolvePsychLuaScriptPath("epicScripts/infishake",
                        "scoped/scripts/child.lua")==null,
                        "foreign child borrowed native script outside its namespace");
                    check(host.resolvePsychLuaScriptPath("epicScripts/infishake",
                        "assets/data/song/script.lua")=="assets/epicScripts/infishake.lua",
                        "native caller lost native fallback");
                    check(host.resolvePsychLuaScriptPath("epicScripts/stale")==null,
                        "unselected manifest root was searched");
                    for (bad in ["../other/cam", "/other/cam", "assets/imported_mods/other/cam",
                        "epicScripts/../cam", "epicScripts/cam.hscript", "C:/cam"])
                        check(host.resolvePsychLuaScriptPath(bad)==null,"unsafe path accepted: "+bad);
                    check(host.compatAddLuaScript("epicScripts/cam"),"first load failed");
                    check(!host.compatAddLuaScript("epicScripts/cam.lua"),"duplicate should stop");
                    check(host.compatAddLuaScript("epicScripts/cam",true),"explicit duplicate ignored");
                    check(host.compatAddLuaScript("epicScripts/infishake"),"second script failed");
                    check(!host.compatAddLuaScript("epicScripts/missing"),"missing script loaded");
                    check(host.loaded.length==3,"wrong lifecycle load count");
                    check(host.recursiveRejected==2,"recursive self-load bypassed the in-flight guard");
                    check(host.loaded[0].indexOf("scoped/epicScripts/cam.lua:start:createPost")>=0
                        && host.loaded[1].indexOf("scoped/epicScripts/cam.lua:start:createPost")>=0
                        && host.loaded[2].indexOf("assets/epicScripts/infishake.lua:start:createPost")>=0,
                        "child lifecycle or ordering wrong");
                    check(host.loaded[0].split(":")[0]!=host.loaded[1].split(":")[0],
                        "forced duplicate reused child scope");
                    check(!host.compatRemoveLuaScript("epicScripts/cam",
                        "other/data/song/script.lua"),"foreign caller removed selected-root script");
                    check(host.compatRemoveLuaScript("epicScripts/cam",
                        "assets/data/song/script.lua"),"owned chart script removal failed");
                    check(!host.loadedCompatScriptPaths.exists("scoped/epicscripts/cam"),
                        "removed identity still counted as running");
                    for(scope in [host.loaded[0].split(":")[0],host.loaded[1].split(":")[0]])
                        check(host.hscriptStates.get(scope).variables.get("__compatClosed")==true,
                            "duplicate scope still dispatches callbacks");
                    check(!host.compatRemoveLuaScript("epicScripts/cam",
                        "assets/data/song/script.lua"),"closed script removed twice");
                    check(host.compatAddLuaScript("epicScripts/cam"),"removed script could not reload");
                    check(host.loaded.length==4,"reload did not create a new scope");
                    host.hscriptStates.get(host.loaded[3].split(":")[0]).variables.set("__compatClosed",true);
                    check(host.compatAddLuaScript("epicScripts/cam"),
                        "self-closed script remained blocked from reload");
                    check(host.loaded.length==5,"self-close reload did not create a scope");
                    FNFAssets.existing.set("scoped/stages/old.lua",true);
                    var oldStage=new CompatInterp();
                    var newStage=new CompatInterp();
                    host.compatScriptScopes.set("scoped/stages/old",
                        [{scope:"stage",interp:oldStage,path:"scoped/stages/old.lua"}]);
                    host.loadedCompatScriptPaths.set("scoped/stages/old",true);
                    host.hscriptStates.set("stage",newStage);
                    check(!host.compatRemoveLuaScript("stages/old",
                        "assets/data/song/script.lua"),"stale path closed a replacement stage");
                    check(newStage.variables.get("__compatClosed")!=true,
                        "replacement stage callback was disabled");
                    check(!host.loadedCompatScriptPaths.exists("scoped/stages/old"),
                        "stale stage identity remained counted as running");
                    check(host.compatAddLuaScript("stages/old"),
                        "replaced stage source could not reload safely");
                    var sibling=new CompatInterp();
                    host.hscriptStates.set("native-sibling",sibling);
                    host.compatScriptScopes.get("scoped/epicscripts/cam").push({
                        scope:"native-sibling",interp:sibling,
                        path:"scoped/epicscripts/cam.hscript"});
                    check(host.compatRemoveLuaScript("epicScripts/cam",
                        "assets/data/song/script.lua"),"Lua sibling was not removed");
                    check(sibling.variables.get("__compatClosed")!=true,
                        "Lua removal closed same-stem HScript sibling");
                    check(host.compatAddLuaScript("epicScripts/cam"),
                        "same-stem HScript incorrectly blocked Lua reload");
                }
            }''',
        }
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, source in files.items():
                (Path(folder) / name).write_text(source, newline='\n')
            run = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                  '-main', 'PsychLoadTest', '--interp'], cwd=ROOT,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
