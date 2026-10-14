"""startDialogue(file, music) shows the dialogue file a script names, with its music."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"^\t(?:@:keep |override |public |static |private )*function " + re.escape(name) + r"\(",
                      source, re.M)
    if match is None:
        raise AssertionError(name)
    brace = source.index("{", match.start())
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[match.start():pos + 1]
    raise AssertionError(name)


RUNTIME_FIXTURE = r'''class PsychRuntimeBindings {
 public static var calls:Array<String>=[];
 public static function dispatch(host:Dynamic,name:String,args:Array<Dynamic>):Dynamic {
  calls.push(name+':'+args.join(','));
  return null;
 }
}
class PsychOwnerPaths {
 public static function formatToSongPath(song:String):String
  return StringTools.replace(song.toLowerCase(),' ','-');
}
class FNFAssets {
 public static var files:Map<String,String>=new Map();
 public static function exists(path:String):Bool return files.exists(path);
 public static function getText(path:String):String return files.get(path);
}
class CoolUtil {
 public static function parseJson(text:String):Dynamic return haxe.Json.parse(text);
}
class EngineCompat {
 // stands in for the real converter: the lines and who is talking to whom
 public static function legacyDialogueText(data:Dynamic,player1:String,player2:String):String {
  var entries:Dynamic=Reflect.field(data,'dialogue');
  if(!Std.isOfType(entries,Array)) return null;
  var lines=[for(entry in (cast entries:Array<Dynamic>)) Std.string(entry.text)];
  return lines.length==0 ? null : player1+'/'+player2+'>'+lines.join('+');
 }
}
class ScrollFactor { public var calls=0; public function new() {} public function set():Void calls++; }
class DialogueBox {
 public var text:String;
 public var exists:Bool=false;
 public var alive:Bool=true;
 public var cameras:Dynamic;
 public var psychInputMode:Bool=false;
 public var scrollFactor:ScrollFactor=new ScrollFactor();
 public var finishThing:Void->Void;
 public var nextDialogueThing:Void->Void;
 public var skipDialogueThing:Void->Void;
 public function new(talkingRight:Bool,text:String) this.text=text;
}
class Music {
 public var playing:Bool=true;
 public var fades:Array<String>=[];
 public function new() {}
 public function fadeIn(duration:Float,from:Float,to:Float):Music {
  fades.push(duration+':'+from+':'+to);return this;
 }
}
class SoundFrontEnd { public var music:Music; public function new() {} }
class FlxG { public static var sound:SoundFrontEnd=new SoundFrontEnd(); }
class Main {
 public var doof:DialogueBox;
 public var SONG:Dynamic={song:'Test Song',player1:'bf',player2:'dad'};
 public var members:Array<Dynamic>=[];
 public var camHUD:Dynamic={name:'hud'};
 public var inCutscene:Bool=false;
 public var endingSong:Bool=false;
 // before the first note, which is when opening dialogue runs
 public var startingSong:Bool=true;
 public var generatedMusic:Bool=true;
 public var dialogueCount:Int=0;
 public var countdownCalls:Int=0;
 public var endSongCalls:Int=0;
 public var musicCalls:Array<String>=[];
 public var mountedRoot:String=null;
 public var preparedBeforeAdd:Bool=false;
 public function new() {}
 public function add(box:DialogueBox):Void {
  preparedBeforeAdd=box.psychInputMode && box.nextDialogueThing!=null && box.cameras!=null;
  box.exists=true;
  members.push(box);
 }
 public function startCountdown():Void countdownCalls++;
 public function endSong():Void endSongCalls++;
 function currentSongDataPath(file:String):String return 'assets/data/test-song/'+file;
 function selectedPsychSkinRoot():Null<String> return mountedRoot;
 function compatPsychPathCall(owner:String,call:String,args:Array<Dynamic>):Dynamic
  return owner+'/'+call+'/'+args[0]+'.json';
 function compatPlayMusic(path:Dynamic,volume:Float=1,looped:Bool=false):Void {
  musicCalls.push(path+':'+volume+':'+looped);
  FlxG.sound.music=new Music();
 }
 METHODS
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  FNFAssets.files.set('assets/data/test-song/dialogue.json','{"dialogue":[{"text":"opening"}]}');
  FNFAssets.files.set('assets/data/test-song/ending.json','{"dialogue":[{"text":"so long"},{"text":"bye"}]}');
  FNFAssets.files.set('assets/data/test-song/broken.json','{"dialogue":');
  FNFAssets.files.set('assets/data/test-song/chart.json','{"song":{"notes":[]}}');
  FNFAssets.files.set('mods/pack/json/test-song/mounted.json','{"dialogue":[{"text":"from the mod"}]}');

  // a named file is converted and shown, not the default
  var host=new Main();
  host.compatStartDialogue('ending','breakfast');
  var box:DialogueBox=host.scriptDialogueBox;
  check(box!=null && host.members.length==1 && host.members[0]==box,'the named dialogue was not shown');
  check(box.text=='bf/dad>so long+bye','wrong dialogue file: '+box.text);
  check(host.inCutscene && host.preparedBeforeAdd && box.scrollFactor.calls==1,
   'the box should be set up before it starts updating');
  check(host.musicCalls.join('|')=='breakfast:0:true','dialogue music request: '+host.musicCalls.join('|'));
  check(FlxG.sound.music.fades.join('|')=='2:0:1','dialogue music should fade in');

  // line callbacks run through the same hooks as the opening dialogue
  box.nextDialogueThing();
  box.skipDialogueThing();
  check(PsychRuntimeBindings.calls.join('|')=='onNextDialogue:1|onSkipDialogue:1',
   'callbacks: '+PsychRuntimeBindings.calls.join('|'));

  // one box at a time
  host.compatStartDialogue('dialogue');
  host.compatStartDialogue('ending');
  check(host.members.length==1,'a second box was stacked on the first');
  check(host.showDialogueFromData('x')==null,'the base function ignored the box on screen');

  // finishing before the song hands back to the countdown
  box.finishThing();
  check(host.countdownCalls==1 && host.endSongCalls==0,'pre-song dialogue should resume the countdown');
  box.exists=false;

  // the extension is optional, and without music nothing is played
  host.compatStartDialogue('ending.json');
  check(host.members.length==2 && host.scriptDialogueBox!=box && host.musicCalls.length==1,
   'a finished box should not block the next one, and no music means no music');
  host.scriptDialogueBox.exists=false;

  // after the last note the dialogue hands back to the ending instead
  host.endingSong=true;
  host.compatStartDialogue('ending','');
  host.scriptDialogueBox.finishThing();
  check(host.endSongCalls==1 && host.countdownCalls==1,'end-of-song dialogue should finish the song');
  host.scriptDialogueBox.exists=false;

  // a file that is not there, is not dialogue or does not parse resumes right away
  for(name in ['nowhere','chart','broken','../ending','C:/ending']) {
   var before=host.members.length;
   var ends=host.endSongCalls;
   host.compatStartDialogue(name,'breakfast');
   check(host.members.length==before && host.endSongCalls==ends+1,name+' should log and resume');
  }
  check(host.musicCalls.length==1,'missing dialogue must not start its music');
  host.endingSong=false;

  // a mounted mod is searched after the imported song folder
  check(host.compatDialogueText('mounted')==null,'a mod file was found without a selected mod');
  host.mountedRoot='mods/pack';
  check(host.compatDialogueText('mounted')=='bf/dad>from the mod','mounted dialogue was not found');
  check(host.compatDialogueText('ending')=='bf/dad>so long+bye','the imported copy should win');

  // the dialogue built at create keeps serving its own names
  var opening=new Main();
  opening.doof=new DialogueBox(false,'prepared');
  for(name in [null,'','dialogue','Dialog','dialogue.json']) {
   opening.members=[];
   opening.doof.exists=false;
   opening.compatStartDialogue(name,'tea');
   check(opening.members.length==1 && opening.members[0]==opening.doof && opening.scriptDialogueBox==null,
    'the prepared opening dialogue should be reused for '+name);
  }
  check(opening.musicCalls.length==5 && opening.musicCalls[0]=='tea:0:true',
   'the prepared dialogue should get its music too');
  opening.members=[];
  opening.doof.exists=false;
  opening.compatStartDialogue('ending');
  check(opening.members.length==1 && opening.members[0]==opening.scriptDialogueBox
   && opening.scriptDialogueBox.text=='bf/dad>so long+bye',
   'a named file should not fall back to the prepared dialogue');
  // a prepared box that already ran its course is gone: the file is read again
  opening.members=[];
  opening.scriptDialogueBox=null;
  opening.doof.exists=false;
  opening.doof.alive=false;
  opening.endingSong=true;
  opening.compatStartDialogue('dialogue');
  check(opening.members.length==1 && opening.members[0]==opening.scriptDialogueBox
   && opening.scriptDialogueBox.text=='bf/dad>opening',
   'a finished opening box was put back on screen instead of a fresh one');
  opening.scriptDialogueBox.finishThing();
  check(opening.endSongCalls==1 && opening.countdownCalls==0,
   'the default file at the end of a song should hand back to the ending');
  var spent=opening.endSongCalls;
  opening.scriptDialogueBox.exists=false;
  opening.compatStartDialogue(null);
  check(opening.members.length==1 && opening.endSongCalls==spent+1,
   'no file and no usable prepared box should resume instead of waiting forever');

  // while the instrumental is running a box would take over its channel
  var midSong=new Main();
  midSong.startingSong=false;
  FlxG.sound.music=new Music();
  check(midSong.showDialogueFromData('x','breakfast')==null && midSong.members.length==0
   && midSong.musicCalls.length==0 && !midSong.inCutscene,
   'a dialogue box opened over the playing song');
  midSong.compatStartDialogue('ending','breakfast');
  check(midSong.members.length==0 && midSong.countdownCalls==0 && midSong.endSongCalls==0,
   'mid-song dialogue should be left out without restarting the countdown');
  // once the music has run out the same request goes through
  FlxG.sound.music.playing=false;
  midSong.compatStartDialogue('ending');
  check(midSong.members.length==1,'dialogue after the music stopped was refused');

  // without a prepared box the default name is just another file
  var late=new Main();
  late.compatStartDialogue('dialogue');
  check(late.scriptDialogueBox!=null && late.scriptDialogueBox.text=='bf/dad>opening',
   'the default file should load on demand when nothing was prepared');
 }
}'''

IMPORT_FIXTURE = r'''import sys.FileSystem;
import sys.io.File;
import haxe.io.Path;
using StringTools;

class CoolUtil {
  public static var parses:Int = 0;
  public static function parseJson(text:String):Dynamic { parses++; return haxe.Json.parse(text); }
}
class Main {
  METHODS
  static function names(found:Array<String>):String
    return [for (path in found) Path.withoutDirectory(path)].join(',');
  static function main():Void {
    var root = Sys.args()[0];
    var all = names(findImportDialogueFiles(root));
    if (all != 'dialogue.json,Ending.json,midway.json') throw 'dialogue files: ' + all;
    // the chart and the event list were ruled out without paying for a parse
    if (CoolUtil.parses != 7) throw 'unexpected parse count: ' + CoolUtil.parses;
    var extra = names(findImportDialogueFiles(root, Path.join([root, 'dialogue.json'])));
    if (extra != 'Ending.json,midway.json') throw 'already imported file was listed again: ' + extra;
    if (findImportDialogueFiles(Path.join([root, 'nowhere'])).length != 0 || findImportDialogueFiles(null).length != 0)
      throw 'a missing folder produced dialogue files';
  }
}
'''


class PsychStartDialogueFileTest(unittest.TestCase):
    def test_named_dialogue_file_and_music_are_used(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("interp.variables.set('startDialogue', compatStartDialogue);", play_state)
        methods = "\n".join(method(play_state, name).replace("static function", "function") for name in (
            "showDialogueFromData", "dialogueBoxShowing", "dialogueWouldReplaceSong", "playDialogueMusic",
            "compatDialogueName",
            "compatDialogueIsPrepared", "compatDialogueText", "compatStartDialogue", "preparePsychDialogue"))
        fixture = RUNTIME_FIXTURE.replace("METHODS", "public var scriptDialogueBox:DialogueBox;\n" + methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_importer_brings_every_dialogue_json_by_content(self):
        importer = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        gather = method(importer, "songImportFromRoots")
        self.assertIn("findImportDialogueFiles(chartRoot, result.dialogueJson)", gather)
        # the extra files are copied beside the chart under their own names and
        # an import that lacks one counts as incomplete
        self.assertEqual(importer.count("Reflect.field(songData, 'dialogueFiles')"), 2)
        self.assertIn("Path.join([dataFolder, Path.withoutDirectory(Path.normalize(Std.string(source)))])",
                      importer)
        self.assertIn("Reflect.field(songData, 'dialogueFiles')", method(importer, "songNeedsRepair"))
        methods = "\n".join(method(importer, name) for name in (
            "isImportFile", "findImportDialogueFiles", "isImportDialogueJson"))
        files = {
            "dialogue.json": '{"dialogue":[{"portrait":"bf","text":"hi"}]}',
            "Ending.json": '{"dialogue":[{"text":"bye"}]}',
            "midway.json": '{\n  "dialogue": []\n}',
            "song-hard.json": '{"song":{"song":"x","notes":[]}}',
            "events.json": '{"events":[]}',
            # mentions the key without being a dialogue file
            "notes.json": '{"comment":"see \\"dialogue\\"","song":{"notes":[]},"dialogue":[]}',
            "list.json": '[{"dialogue":[]}]',
            "text.json": '{"dialogue":"not a list"}',
            "broken.json": '{"dialogue":[',
            "dialogue.txt": '"dialogue"',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            data = work / "data"
            data.mkdir()
            (data / "folder.json").mkdir()
            for name, text in files.items():
                (data / name).write_text(text, encoding="utf-8", newline="\n")
            code = work / "code"
            code.mkdir()
            (code / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text(), newline="\n")
            (code / "Main.hx").write_text(IMPORT_FIXTURE.replace("METHODS", methods), encoding="utf-8",
                                          newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(code), "--run", "Main", str(data)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
