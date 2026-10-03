"""Keep Codename's actor globals tied to their authored source strumlines."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DONOR_UI = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/songs/UI.hx"
)


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def extract_function(source: str, name: str) -> str:
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", source)
    if match is None:
        raise AssertionError(f"missing donor function: {name}")
    start = match.start()
    brace = source.index("{", match.start())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated donor function: {name}")


class CodenameActorStrumlineAliasTest(unittest.TestCase):
    def test_actor_aliases_follow_source_lines_and_swaps(self):
        if not DONOR_UI.is_file():
            self.skipTest("mounted D-Sides Codename UI script is unavailable")

        playstate = (ROOT / "source/PlayState.hx").read_text()
        interp_source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        actor_reader = extract_method(playstate, "\tfunction codenameScriptCharacterAtLine(")
        actor_writer = extract_method(playstate, "\tfunction setCodenameScriptCharacterAtLine(")
        actor_binder = extract_method(playstate, "\tfunction bindCodenameActorAliases(")
        line_reader = extract_method(playstate, "\t@:keep public function getCodenameInputLine(")
        live_global_lookup = extract_method(interp_source, "public function hasLiveGlobal(")
        stage_alias_filter = extract_method(interp_source, "public function isStageActorAlias(")
        seed = extract_method(playstate, "\tfunction seedCodenameScriptGlobals(")
        refresh = extract_method(playstate, "\tfunction refreshCodenameCharacterScopes(")
        callback_bindings = extract_method(playstate, "\tfunction callCodenameScript(")
        callback = extract_function(DONOR_UI.read_text(), "onPostNoteHit")

        self.assertIn("bindCodenameActorAliases(interp);", seed)
        for alias in ("dad", "bf", "boyfriend", "gf"):
            self.assertIn("bindLiveGlobal('" + alias + "'", actor_binder)
        for codename_method in (refresh, callback_bindings):
            self.assertNotIn("variables.set('boyfriend', boyfriend)", codename_method)
            self.assertNotIn("variables.set('bf', boyfriend)", codename_method)
            self.assertNotIn("variables.set('dad', dad)", codename_method)
        self.assertNotIn("variables.set('gf', gf)", playstate)
        # The standard HScript environment still receives native actors.
        for native_alias in ("boyfriend", "gf", "dad"):
            self.assertIn(f'interp.variables.set("{native_alias}", {native_alias});', playstate)
        self.assertIn("if (liveGlobals.exists(id)) return liveGlobals.get(id).read();",
                      extract_method(interp_source, "override function resolve("))
        self.assertIn("liveGlobals.get(id).write(value);",
                      extract_method(interp_source, "override function setVar("))
        self.assertIn("interp.isStageActorAlias", playstate)

        fixture = r'''import hscript.Interp;
import hscript.Parser;
class Character {
 public var name:String;
 public var played:Array<String>=[];
 public function new(name:String) this.name=name;
 public function hasAnim(name:String):Bool return name=='combo50';
 public function playAnim(name:String,force:Bool=false):Void played.push(name+':'+force);
}
class CodenameInputLine<T> {
 public var characters:Array<T>=[];
 public function new(actors:Array<Null<T>>) {
  for(actor in actors) if(actor!=null) characters.push(actor);
 }
}
class CodenameScriptInterp extends Interp {
 var liveGlobals:Map<String,{read:Void->Dynamic,write:Dynamic->Void}>=new Map();
 public function bindLiveGlobal(name:String,read:Void->Dynamic,write:Dynamic->Void):Void
  liveGlobals.set(name,{read:read,write:write});
''' + live_global_lookup + '\n' + stage_alias_filter + r'''
 override function resolve(id:String):Dynamic {
  if(!variables.exists(id) && liveGlobals.exists(id)) return liveGlobals.get(id).read();
  return super.resolve(id);
 }
 override function setVar(id:String,value:Dynamic):Void {
  if(!variables.exists(id) && liveGlobals.exists(id)) {liveGlobals.get(id).write(value);return;}
  super.setVar(id,value);
 }
}
class Main {
 var codenameInputLines:Array<CodenameInputLine<Character>>=[];
''' + line_reader + '\n' + actor_reader + '\n' + actor_writer + '\n' + actor_binder + r'''
 public function new() {}
 static function check(ok:Bool,why:String):Void if(!ok) throw why;
 static function main():Void {
  var state=new Main();
  var interp=new CodenameScriptInterp();
  var empty=state.newLineSet(false);
  state.codenameInputLines=empty;
  state.bindCodenameActorAliases(interp);
  var earlyPlayer=new Character('early-player');
  interp.variables.set('earlyPlayer',earlyPlayer);
  interp.execute(new Parser().parseString('bf=earlyPlayer;'));
  interp.execute(new Parser().parseString('earlyRead=bf;'));
  check(state.codenameScriptCharacterAtLine(1)==null && interp.variables.get('earlyRead')==null,
   'an absent authored BF line fell back to an actor or retained an early assignment');
  interp.variables.set('canPlayGFAnims',true);
  interp.variables.set('combo',50);
  interp.variables.set('strumLines',{members:empty});
  interp.execute(new Parser().parseString(''' + haxe_quote(callback) + r'''));
  var onPostNoteHit=interp.variables.get('onPostNoteHit');
  Reflect.callMethod(null,onPostNoteHit,[{note:{strumLine:{cpu:false}}}]);
  check(state.codenameScriptCharacterAtLine(2)==null,
   'an absent authored GF line exposed the legacy native girlfriend');
  check(state.codenameScriptCharacterAtLine(2)==null,
   'the donor callback did not leave the absent source line empty');

  var dadFirst=new Character('source-dad-1');
  var bfFirst=new Character('source-bf-1');
  var first=new Character('source-gf-1');
  var dadLine=new CodenameInputLine<Character>([dadFirst]);
  var bfLine=new CodenameInputLine<Character>([bfFirst]);
  var gfLine=new CodenameInputLine<Character>([first]);
  var authored:Array<CodenameInputLine<Character>>=[dadLine,bfLine,gfLine];
  state.codenameInputLines=authored;
  interp.variables.set('strumLines',{members:authored});
  check(state.codenameScriptCharacterAtLine(2)==first,
   'source line 2 did not provide Codename gf');
  interp.execute(new Parser().parseString('seenDad=dad;seenBF=bf;seenBoyfriend=boyfriend;seenGF=gf;'));
  check(interp.variables.get('seenDad')==dadFirst && interp.variables.get('seenBF')==bfFirst
   && interp.variables.get('seenBoyfriend')==bfFirst && interp.variables.get('seenGF')==first,
   'Codename actor globals did not resolve source line primaries');
  Reflect.callMethod(null,onPostNoteHit,[{note:{strumLine:{cpu:false}}}]);
  check(first.played.join(',')=='combo50:true',
   'donor callback did not use the authored GF actor');

  var dadSecond=new Character('source-dad-2');
  var bfSecond=new Character('source-bf-2');
  var second=new Character('source-gf-2');
  dadLine.characters=[dadSecond];
  bfLine.characters=[bfSecond];
  gfLine.characters=[second];
  interp.execute(new Parser().parseString('seenDad=dad;seenBF=bf;seenBoyfriend=boyfriend;seenGF=gf;'));
  check(interp.variables.get('seenDad')==dadSecond && interp.variables.get('seenBF')==bfSecond
   && interp.variables.get('seenBoyfriend')==bfSecond && interp.variables.get('seenGF')==second,
   'Codename actor globals stayed stale after source-line actor replacement');
  Reflect.callMethod(null,onPostNoteHit,[{note:{strumLine:{cpu:false}}}]);
  check(state.codenameScriptCharacterAtLine(2)==second
   && second.played.join(',')=='combo50:true',
   'Codename gf stayed stale after a source-line actor replacement');

  var replacement=new Character('assigned-gf');
  interp.variables.set('replacement',replacement);
  interp.execute(new Parser().parseString('gf = replacement;'));
  check(gfLine.characters.length==1 && gfLine.characters[0]==replacement,
   'assigning Codename gf did not update the authored third line');
  check(state.codenameScriptCharacterAtLine(2)==replacement,
   'Codename gf did not read back its assigned source-line actor');

  var replacementPlayer=new Character('assigned-boyfriend');
  interp.variables.set('replacementPlayer',replacementPlayer);
  interp.execute(new Parser().parseString('boyfriend = replacementPlayer;'));
  check(bfLine.characters.length==1 && bfLine.characters[0]==replacementPlayer,
   'assigning Codename boyfriend did not update the authored second line');
  interp.execute(new Parser().parseString('seenBF=bf;seenBoyfriend=boyfriend;'));
  check(interp.variables.get('seenBF')==replacementPlayer
   && interp.variables.get('seenBoyfriend')==replacementPlayer,
   'bf and boyfriend aliases did not read the same current actor');

  var replacementDad=new Character('assigned-dad');
  interp.variables.set('replacementDad',replacementDad);
  interp.execute(new Parser().parseString('dad = replacementDad;'));
  check(dadLine.characters.length==1 && dadLine.characters[0]==replacementDad,
   'assigning Codename dad did not update the authored first line');

  var aliasPlayer=new Character('assigned-bf');
  interp.variables.set('aliasPlayer',aliasPlayer);
  interp.execute(new Parser().parseString('bf = aliasPlayer;'));
  check(bfLine.characters.length==1 && bfLine.characters[0]==aliasPlayer,
   'assigning Codename bf did not update the authored second line');

  // Stage XML names are injected into variables for ordinary prop lookup.
  // A native character registered as `boyfriend` must not shadow the live actor in an
  // asynchronous callback, including after a character swap.
  var stageProp=new Character('stage-boyfriend-prop');
  var stageBindings=new CodenameStageBindings();
  var elements:Map<String,Dynamic>=['boyfriend'=>stageProp,'ground'=>stageProp];
  stageBindings.refresh(interp.variables,elements,interp.isStageActorAlias);
  check(!interp.variables.exists('boyfriend') && interp.variables.get('ground')==stageProp,
   'stage bindings shadowed a live actor alias or omitted a normal prop');
  interp.execute(new Parser().parseString('function delayedBoyfriend() { return boyfriend; }'));
  var delayedBoyfriend:Dynamic=interp.variables.get('delayedBoyfriend');
  var swappedPlayer=new Character('swapped-player');
  bfLine.characters=[swappedPlayer];
  stageBindings.refresh(interp.variables,elements,interp.isStageActorAlias);
  check(Reflect.callMethod(null,delayedBoyfriend,[])==swappedPlayer,
   'an asynchronous callback resolved the stage prop instead of the swapped source-line actor');
  // Upstream stageSprites does inject real XML sprites, even with a name
  // colliding with a state property. Only native character aliases are excluded.
  var authoredSprite:Dynamic={alpha:0.75};
  elements.set('boyfriend',authoredSprite);
  stageBindings.refresh(interp.variables,elements,interp.isStageActorAlias);
  check(Reflect.callMethod(null,delayedBoyfriend,[])==authoredSprite,
   'a real authored XML prop was incorrectly treated as a reserved name');
  var explicitSprite:Dynamic={alpha:0.5};
  interp.variables.set('boyfriend',explicitSprite);
  elements.set('boyfriend',stageProp);
  stageBindings.refresh(interp.variables,elements,interp.isStageActorAlias);
  check(Reflect.callMethod(null,delayedBoyfriend,[])==explicitSprite,
   'an explicit script variable was removed with a native actor registration');
 }
 function newLineSet(includeGirlfriend:Bool):Array<CodenameInputLine<Character>> {
  var lines:Array<CodenameInputLine<Character>>=[null,null];
  if(includeGirlfriend) lines.push(new CodenameInputLine<Character>([new Character('source-gf')]));
  return lines;
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", folder, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def haxe_quote(text: str) -> str:
    """Return a Haxe double-quoted string literal containing the donor body."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'


if __name__ == "__main__":
    unittest.main()
