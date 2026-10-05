"""Retained NV rejection recovery and Freeplay use actual supported charts."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method

ROOT = Path(__file__).resolve().parents[2]


class FreeplayChartAvailabilityTest(unittest.TestCase):
    def test_retained_structure_cache_and_selection(self):
        manager = (ROOT / 'source/DifficultyManager.hx').read_text()
        freeplay = (ROOT / 'source/FreeplayState.hx').read_text()
        methods = '\n'.join(extract_method(manager, marker) for marker in [
            'public static function addSongSupport(', 'public static function changeDifficultySans('])
        methods += '\n' + extract_method(freeplay, 'static function selectionHasChart(')
        methods += '\n' + extract_method(freeplay, 'function buildIconFor(')
        methods += '\n' + extract_method(freeplay, 'function refreshRankStarsFor(')
        methods += '\n' + extract_method(freeplay, 'function hxcChangeDifficulty(')
        methods += '\n' + extract_method(manager, 'public static function getDiffName(')
        methods += '\n' + extract_method(manager, 'public static function getDiffNum(')
        host = '''typedef DiffInfo = {difficulty:Int,text:String};
typedef SourceDifficultyRules = {selectable:Array<String>,unsupported:Array<String>};
class Harness {
public var songs:Array<Dynamic>=[{songName:"fixture",songCharacter:"bf"}];
public var iconArray:Array<HealthIcon>=[null]; public var songRows:Array<Dynamic>=[{}];
public var members:Array<Dynamic>=[]; public var grpSongSources:Dynamic={};
public var starArray:Array<Array<RankStar>>=[null]; public var hxcCapsuleViews:Array<Dynamic>=[];
public var curSelected:Int=0;
public var curDifficulty:Int=0; public var hxcDifficultyOrder:Array<String>=[];
public function new() {}
function songMatches(i:Int):Bool return true;
function insert(i:Int,v:Dynamic):Void members.push(v);
function remove(v:Dynamic,b:Bool):Void members.remove(v);
public static var diffJson:Dynamic = {defaultDiff:1,difficulties:[{name:"easy"},{name:"normal"},{name:"hard"}]};
public static var supportedDiff:Map<String,Array<Int>> = new Map();
static var rules:Dynamic = {selectable:["easy","normal","hard"],unsupported:["easy","normal","hard"]};
static function readAndDiscoverSongDifficulties(s:String):Dynamic return rules;
static function readSourceDifficultyRules(s:String):Dynamic return rules;
public static function getSupportedDiffs(s:String):Array<Int> return supportedDiff.exists(s) ? supportedDiff.get(s) : [];
public static function getDiffEnding(d:Int):String return d==1 ? "" : "-"+diffJson.difficulties[d].name;
static function changeDifficulty(d:Int,c:Int=0):Dynamic {var count=diffJson.difficulties.length;d=(d+c)%count;if(d<0)d+=count;return {difficulty:d,text:diffJson.difficulties[d].name};}
''' + methods.replace('DifficultyManager.', 'Harness.').replace('static function selectionHasChart', 'public static function selectionHasChart').replace('function buildIconFor', 'public function buildIconFor').replace('function refreshRankStarsFor', 'public function refreshRankStarsFor').replace('function hxcChangeDifficulty', 'public function hxcChangeDifficulty') + '\n}\n'
        main = r'''class Main {static function main() {
Sys.setCwd(Sys.args()[0]);
for (path in ["assets/data/fixture", "assets/imported_mods/owner/songs/original/data"])
  sys.FileSystem.createDirectory(path);
var receipt = "assets/data/fixture/importProvenance.json";
sys.io.File.saveContent(receipt,haxe.Json.stringify({sourceEngine:"Nightmare Vision",sourceOwner:"assets/imported_mods/owner",sourceFolder:"original"}));
var source = "assets/imported_mods/owner/songs/original/data/";
for (name in ["easy","normal","hard"]) {
  var retainedName = name=="normal" ? "original.jsonc" : "original-"+name+".jsonc";
  sys.io.File.saveContent(source+retainedName,haxe.Json.stringify({song:{keys:4,lanes:3,notes:[]}}));
  sys.io.File.saveContent("assets/data/fixture/fixture"+(name=="normal"?"":"-"+name)+".json",'{"song":{"notes":[]}}');
}
Harness.addSongSupport("fixture");
if (Harness.getSupportedDiffs("fixture").join(",")!="0,1,2") throw "stale 3-bank receipt retained";
if (!Harness.selectionHasChart("fixture",1)) throw "normal base-chart alias lost";
var icons=new Harness();icons.buildIconFor(0);
if(icons.starArray[0].length!=3) throw "three playable charts did not create three rank stars";
var reads=FNFAssets.chartReads;
Harness.addSongSupport("fixture");
if(FNFAssets.chartReads!=reads) throw "unchanged source was parsed twice";
sys.FileSystem.deleteFile(source+"original-easy.jsonc");
Harness.addSongSupport("fixture");
if(Harness.getSupportedDiffs("fixture").indexOf(0)>=0) throw "lossy destination certified missing source";
sys.io.File.saveContent(source+"original-hard.jsonc",'{"song":{"lanes":0,"notes":[]}}');
sys.FileSystem.deleteFile("assets/data/fixture/fixture-easy.json");
Harness.addSongSupport("fixture");
if(Harness.getSupportedDiffs("fixture").join(",")!="1") throw "missing or unsupported chart selectable";
icons.refreshRankStarsFor(0);
if(icons.starArray[0].length!=1 || icons.starArray[0][0].diff!=1) throw "rank star difficulty stale";
if(Harness.selectionHasChart("fixture",0)||Harness.selectionHasChart("fixture",2)) throw "invalid launch allowed";
sys.FileSystem.deleteFile("assets/data/fixture/fixture.json");
Harness.addSongSupport("fixture");
var selection=Harness.changeDifficultySans(1,1,"fixture");
icons.refreshRankStarsFor(0);
if(icons.starArray[0].length!=0) throw "unknown chart fabricated a rank star";
if(selection.difficulty!=1||selection.text!="UNAVAILABLE"||Harness.selectionHasChart("fixture",1)) throw "empty-support navigation/launch";
sys.FileSystem.createDirectory("assets/data/directfixture");
sys.FileSystem.createDirectory("assets/imported_mods/direct/data/original");
sys.io.File.saveContent("assets/data/directfixture/importProvenance.json",haxe.Json.stringify({sourceEngine:"Nightmare Vision",sourceOwner:"assets/imported_mods/direct",sourceFolder:"original"}));
sys.io.File.saveContent("assets/data/directfixture/directfixture-hard.json",'{"song":{"notes":[]}}');
sys.io.File.saveContent("assets/imported_mods/direct/data/original/original-hard.jsonc",'{"song":{"keys":4,"lanes":3,"notes":[]}}');
if(!FreeplayChartMetadata.retainedChartSupported("directfixture","hard","assets/data/directfixture/directfixture-hard.json"))
  throw "direct game-root data/<song> retained layout was not found";
for (fixture in [
  {song:"nestedfixture", owner:"nested", directory:"assets/imported_mods/nested/data/songs/original"},
  {song:"songdatafixture", owner:"songdata", directory:"assets/imported_mods/songdata/data/songData/original"}
]) {
  sys.FileSystem.createDirectory("assets/data/"+fixture.song);
  sys.FileSystem.createDirectory(fixture.directory);
  sys.io.File.saveContent("assets/data/"+fixture.song+"/importProvenance.json",
    haxe.Json.stringify({sourceEngine:"Nightmare Vision",sourceOwner:"assets/imported_mods/"+fixture.owner,sourceFolder:"original"}));
  sys.io.File.saveContent("assets/data/"+fixture.song+"/"+fixture.song+"-hard.json",'{"song":{"notes":[]}}');
  sys.io.File.saveContent(fixture.directory+"/original-hard.jsonc",'{"song":{"keys":4,"lanes":3,"notes":[]}}');
  if(!FreeplayChartMetadata.retainedChartSupported(fixture.song,"hard","assets/data/"+fixture.song+"/"+fixture.song+"-hard.json"))
    throw "discovered nested chart root was not retained: "+fixture.song;
}
sys.FileSystem.createDirectory("assets/data/ambiguous");
sys.io.File.saveContent("assets/data/ambiguous/importProvenance.json",haxe.Json.stringify({sourceEngine:"Nightmare Vision",sourceOwner:"assets/imported_mods/owner",sourceFolder:"original"}));
sys.io.File.saveContent("assets/data/ambiguous/ambiguous-hard.json",'{"song":{"notes":[]}}');
sys.io.File.saveContent(source+"hard.json",'{"song":{"lanes":0,"notes":[]}}');
if(FreeplayChartMetadata.retainedChartSupported("ambiguous","hard","assets/data/ambiguous/ambiguous-hard.json"))
  throw "prefixed variant overrode authoritative bare-difficulty source";
Harness.diffJson.difficulties.push({name:"expert"});
Harness.supportedDiff.set("stride",[1]);
for (step in [2,-2,4,-4]) {
  if(Harness.changeDifficultySans(0,step,"stride").difficulty!=1) throw "stride exhaustion selected unsupported difficulty";
}
if(Harness.changeDifficultySans(0,1,"stride").difficulty!=1) throw "ordinary navigation changed";
if(Harness.changeDifficultySans(1,0,"stride").difficulty!=1) throw "valid current selection changed";
Harness.supportedDiff.set("fixture",[0,2]);
icons.curDifficulty=2;icons.hxcDifficultyOrder=["HARD","NONEXISTENT"];
var authored=icons.hxcChangeDifficulty(1);
if(authored.difficulty!=2) throw "unknown authored name silently selected easy";
icons.hxcDifficultyOrder=["NONEXISTENT"];
authored=icons.hxcChangeDifficulty(0);
if(authored.difficulty!=2) throw "all-unknown authored list silently selected easy";
Sys.println("freeplay-chart-availability-ok");
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            folder = Path(temp)
            files = {'Harness.hx': host, 'Main.hx': main,
                'HealthIcon.hx': '''class HealthIcon {public var sprTracker:Dynamic;public var visible:Bool;public var alpha:Float;
public function new(a:Dynamic,b:Dynamic,c:Dynamic,d:Dynamic,e:Dynamic){}}''',
                'RankStar.hx': '''class RankStar {public var sprTracker:Dynamic;public var starNum:Int;public var visible:Bool;public var diff:Int;
public function new(s:String,d:Int){diff=d;} public function checkStar():Void{} public function destroy():Void{}}''',
                'FlxTween.hx': 'class FlxTween {public static function cancelTweensOf(v:Dynamic):Void{}}',
                'OptionsHandler.hx': 'class OptionsHandler {public static var options={style:false};}',
                'FNFAssets.hx': '''class FNFAssets {public static var chartReads=0;
public static function exists(p:String):Bool return sys.FileSystem.exists(p);
public static function getText(p:String):String {if(p.indexOf("/songs/")>=0) chartReads++;return sys.io.File.getContent(p);}
public static function resolveCaseInsensitivePath(p:String):String return p;}''',
                'CoolUtil.hx': 'class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}',
                'ImportEngine.hx': 'class ImportEngine {public static inline var NIGHTMARE_VISION="Nightmare Vision";}',
                'NightmareVisionDifficultyCompat.hx': '''class NightmareVisionDifficultyCompat {
public static function allows(names:Array<String>,name:String):Bool return names==null||names.indexOf(name)>=0;}'''}
            for name, value in files.items():
                (folder / name).write_text(value)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT/'source'), '-cp', temp,
                '--run', 'Main', temp], cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_both_launch_routes_and_rank_stars_share_support(self):
        source = (ROOT/'source/FreeplayState.hx').read_text()
        hxc = extract_method(source, 'function hxcLaunchCurrentSelection(')
        self.assertIn('selectionHasChart(songs[curSelected].songName, curDifficulty)', hxc)
        self.assertLess(hxc.index('selectionHasChart('), hxc.index('Song.loadFromJson('))
        self.assertIn('if (!selectionHasChart(songs[daSelection].songName, curDifficulty)) {', source)
        self.assertIn('ordinaryRejectedSelection(songs[daSelection].songName, curDifficulty)', source)
        icon = extract_method(source, 'function buildIconFor(')
        self.assertIn('refreshRankStarsFor(i)', icon)
        stars = extract_method(source, 'function refreshRankStarsFor(')
        self.assertIn('DifficultyManager.getSupportedDiffs(songs[i].songName)', stars)
        self.assertIn('new RankStar(songs[i].songName, diff)', stars)
        diff = extract_method(source, 'function changeDiff(')
        self.assertIn('star.diff == curDifficulty ? 25 : 0', diff)


if __name__ == '__main__':
    unittest.main()
