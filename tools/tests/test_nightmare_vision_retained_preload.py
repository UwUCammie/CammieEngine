"""Keep Nightmare Vision event preloads in their source character groups."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def function_body(source, name):
    marker = "function " + name + "("
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError("unterminated function " + name)


class NightmareVisionRetainedPreloadTest(unittest.TestCase):
    def run_haxe(self, fixture, *extra_sources, desktop=False):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            if "__PRELOAD_PATH__" in fixture:
                preload_path = work / "preload.txt"
                preload_path.write_text("explicit-preload\n", newline='\n')
                fixture = fixture.replace("__PRELOAD_PATH__", str(preload_path))
            (work / "Main.hx").write_text(fixture, newline='\n')
            for name, source in extra_sources:
                (work / name).write_text(source, newline='\n')
            command = list(HAXE_COMMAND)
            if desktop:
                command.extend(["-D", "desktop"])
            result = subprocess.run(
                [*command, "-cp", str(ROOT / "source"),
                 "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_preload_aliases_remain_distinct_from_psych_trigger_roles(self):
        fixture = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  // Nightmare Vision's source event-push aliases: 1 is GF and 0 is opponent.
  check(NightmareVisionCharacterEvent.preloadRole('gf') == 2, 'gf event alias');
  check(NightmareVisionCharacterEvent.preloadRole('girlfriend') == 2, 'girlfriend event alias');
  check(NightmareVisionCharacterEvent.preloadRole('1') == 2, 'legacy 1 event alias');
  check(NightmareVisionCharacterEvent.preloadRole('dad') == 1, 'dad event alias');
  check(NightmareVisionCharacterEvent.preloadRole('opponent') == 1, 'opponent event alias');
  check(NightmareVisionCharacterEvent.preloadRole('0') == 1, 'legacy 0 event alias');
  check(NightmareVisionCharacterEvent.preloadRole('2') == 2, 'numeric GF event role');
  check(NightmareVisionCharacterEvent.preloadRole('boyfriend') == 0, 'BF event fallback');

  // Psych's shared character-trigger interpretation stays 0=BF, 1=opponent.
  check(PsychCharacterChangeEvent.role('1') == 1, 'Psych trigger role was remapped');
  check(PsychCharacterChangeEvent.role('0') == 0, 'Psych player role was remapped');
 }
}'''
        self.run_haxe(fixture)

    def test_playstate_preload_paths_retain_group_actors(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        preload = function_body(source, "preloadSwapCharacters")
        psych_preload = function_body(source, "compatAddCharacterToList")
        self.assertIn("NightmareVisionCharacterEvent.preloadRole(e.v1)", preload)
        self.assertIn("addNightmareVisionCharacterToList(characterName, PsychCharacterChangeEvent.role", psych_preload)
        group_preload = function_body(source, "addNightmareVisionCharacterToList")

        fixture = r'''import sys.FileSystem;
using StringTools;
class Actor {
 public var requestedCharacter:String;public var curCharacter:String;
 public var alpha:Float=1;
 public var destroyed:Bool=false;
 public function new(name:String) {requestedCharacter=name;curCharacter=name;}
 public function destroy():Void destroyed=true;
}
class Character {
 public static function characterExists(name:String):Bool return name != '';
}
class CodenameEventDispatch {
 public static function fromNative(event:Dynamic):Dynamic return null;
}
class RetainedGroup {
 public var map:Map<String,Actor>=[];var construct:String->Actor;
 public function new(initial:Actor,construct:String->Actor){map.set(initial.curCharacter,initial);this.construct=construct;}
 public function addToList(name:String):Actor {var old=map.get(name);if(old!=null)return old;var actor=construct(name);actor.alpha=.00001;map.set(actor.curCharacter,actor);return actor;}
}
class Main {
 var nightmareVisionScripts:Dynamic={owner:'nightmare-vision'};
 var characterGroups:Map<Int,RetainedGroup>=new Map();
 var nightmareVisionHiddenGFPlaceholder:Actor;var loaded:Array<String>=[];
 var boyfriend:Actor;
 var dad:Actor;
 var gf:Actor;
 var songEvents:Array<Dynamic>=[];
 var SONG:Dynamic={player1:'bf',player2:'dad',gf:'gf'};
 var warmed:Array<Actor>=[];
 var warmCalls:Array<String>=[];
 var nightmareVisionSourceEventsPrepared:Bool=false;
 var useExplicitPreloadFile:Bool=false;
 var preloadFilePath:String='__PRELOAD_PATH__';
 function new() {
  boyfriend=new Actor('bf'); dad=new Actor('dad'); gf=new Actor('gf');
 }
 function nightmareVisionCharacterGroup(type:Int):RetainedGroup {
  var existing=characterGroups.get(type);if(existing!=null)return existing;
  var initial=type==0?boyfriend:type==1?dad:gf;
  var group=new RetainedGroup(initial,function(name){var actor=new Actor(name);warmed.push(actor);return actor;});
  characterGroups.set(type,group);return group;
 }
 function loadNightmareVisionCharacter(actor:Actor):Void loaded.push(actor.curCharacter);
 __GROUP_PRELOAD_BODY__
 function warmCharacterAtlas(name:String,isPlayer:Bool=false):Void {
  warmCalls.push(name+':'+isPlayer);
  var actor=new Actor(name); warmed.push(actor); actor.destroy();
 }
 function codenameSelectedRoot():String return '';
 function currentSongDataPath(name:String):String
  return useExplicitPreloadFile ? preloadFilePath : preloadFilePath+'.missing';
 function codenameSwapPreloadParams(event:Dynamic):Null<Array<Dynamic>> return null;
 __PRELOAD_BODY__
 __PSYCH_PRELOAD_BODY__
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var state=new Main();
  state.songEvents=[
   {name:'Change Character',v1:'gf',v2:'gf-by-name'},
   {name:'Change Character',v1:'1',v2:'gf-by-one'},
   {name:'Change Character',v1:'opponent',v2:'dad-by-name'},
   {name:'Change Character',v1:'0',v2:'dad-by-zero'}
  ];
  state.preloadSwapCharacters();

  var gfBank=state.nightmareVisionCharacterGroup(2);
  var dadBank=state.nightmareVisionCharacterGroup(1);
  check(gfBank.map.exists('gf-by-name') && gfBank.map.exists('gf-by-one'),
   'event-push GF aliases did not preload into GF bank');
  check(dadBank.map.exists('dad-by-name') && dadBank.map.exists('dad-by-zero'),
   'event-push opponent aliases did not preload into opponent bank');
  for(name in ['gf-by-name','gf-by-one']) {
   var actor:Actor=cast gfBank.map.get(name);
   check(actor.alpha==0.00001 && !actor.destroyed, 'GF preload actor was not retained hidden');
  }
  for(name in ['dad-by-name','dad-by-zero']) {
   var actor:Actor=cast dadBank.map.get(name);
   check(actor.alpha==0.00001 && !actor.destroyed, 'opponent preload actor was not retained hidden');
  }
  check(state.warmCalls.length==0, 'event preload used the temporary atlas warmer');
  check(state.loaded.join(',')=='gf-by-name,gf-by-one,dad-by-name,dad-by-zero','source caller loads current identities after group preloads');

  // The Psych script API continues to use Psych's 0=BF, 1=opponent, 2=GF roles.
  state.compatAddCharacterToList('script-gf','gf');
  state.compatAddCharacterToList('script-one','1');
  check(gfBank.map.exists('script-gf'), 'Psych GF script preload missed GF bank');
  check(dadBank.map.exists('script-one') && !gfBank.map.exists('script-one'),
   'Psych numeric trigger role 1 was treated as the older NV event alias');
  var scriptGF:Actor=cast gfBank.map.get('script-gf');
  var scriptOne:Actor=cast dadBank.map.get('script-one');
  check(!scriptGF.destroyed && !scriptOne.destroyed && scriptGF.alpha==0.00001
   && scriptOne.alpha==0.00001, 'Psych script preload actors were not retained hidden');
  check(state.warmCalls.length==0, 'Psych script preload used the temporary atlas warmer');

  // The ordinary Psych host still uses the temporary atlas warm-up path.
  var psychOnly=new Main();
  psychOnly.nightmareVisionScripts=null;
  psychOnly.compatAddCharacterToList('ordinary','boyfriend');
  check(psychOnly.warmCalls.join(',')=='ordinary:true', 'ordinary preload behavior changed');
  check(psychOnly.warmed[0].destroyed, 'ordinary warm-up actor was not destroyed');

  // Once NV source events have been prepared, their character bank already
  // owns preload responsibility. Keep explicit preload.txt warming active.
  var sourcePrepared=new Main();
  sourcePrepared.nightmareVisionSourceEventsPrepared=true;
  sourcePrepared.useExplicitPreloadFile=true;
  sourcePrepared.songEvents=[{name:'Change Character',v1:'gf',v2:'already-prepared'}];
  sourcePrepared.preloadSwapCharacters();
  check(sourcePrepared.characterGroups.get(2)==null,
   'prepared NV events should not construct a duplicate retained character-bank actor');
  check(sourcePrepared.warmCalls.join(',')=='explicit-preload:false',
   'source-prepared early return should still process explicit preload.txt entries');
  check(sourcePrepared.warmed.length==1 && sourcePrepared.warmed[0].destroyed,
   'explicit preload.txt character should use and release the temporary atlas warmer');
 }
}'''
        fixture = fixture.replace("__PRELOAD_BODY__", preload).replace(
            "__PSYCH_PRELOAD_BODY__", psych_preload).replace("__GROUP_PRELOAD_BODY__", group_preload)
        cool_util_stub = '''class CoolUtil {
 public static function coolTextFile(path:String):Array<String>
  return sys.io.File.getContent(path).split("\\n");
}'''
        self.run_haxe(fixture, ("CoolUtil.hx", cool_util_stub), desktop=True)


if __name__ == "__main__":
    unittest.main()
