"""Exercise Psych dialogue progression without constructing the native scene."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
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
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError("unterminated function " + name)


FIXTURE = r'''class TypeText {
 public var skips:Int=0;
 public var completeCallback:Void->Void;
 public function new() {}
 public function skip():Void skips++;
 public function complete():Void if(completeCallback!=null) completeCallback();
}
class Main {
 public var psychInputMode:Bool=false;
 public var dialogueStarted:Bool=true;
 public var isEnding:Bool=false;
 public var psychTextFinished:Bool=false;
 public var dialogueFile:Dynamic;
 public var swagDialogue:TypeText=new TypeText();
 public var nextDialogueThing:Void->Void;
 public var skipDialogueThing:Void->Void;
 public var finishThing:Void->Void;
 public var nextCalls:Int=0;
 public var skipCalls:Int=0;
 public var finishCalls:Int=0;
 public var startCalls:Int=0;
 public var endCalls:Int=0;
 public var clickCalls:Int=0;
 public var killCalls:Int=0;
 function new(lines:Array<String>) {
  dialogueFile={info:lines};
  nextDialogueThing=function() nextCalls++;
  skipDialogueThing=function() skipCalls++;
 }
 LINE_CALLBACK
 INPUT
 CLEANUP
 function startDialogue():Void {
  startCalls++;
  onPsychDialogueLineStarted();
 }
 function endDialog():Void {endCalls++;isEnding=true;}
 function playDialogueClick():Void clickCalls++;
 function kill():Void killCalls++;
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var state=new Main(["first","second"]);
  state.psychInputMode=true;
  state.startDialogue();
  check(state.nextCalls==1 && !state.psychTextFinished,
   "the first line start should notify and reset typewriter completion");
  state.updatePsychDialogueInput(true,false);
  check(state.swagDialogue.skips==1 && state.skipCalls==1 && state.endCalls==0
   && (cast state.dialogueFile.info:Array<String>).length==2,
   "accept on unfinished text should fast-forward the current line only");
  state.swagDialogue.complete();
  check(state.psychTextFinished,"the typewriter completion callback should mark the current line finished");
  state.updatePsychDialogueInput(true,false);
  check(state.startCalls==2 && state.nextCalls==2 && state.endCalls==0
   && (cast state.dialogueFile.info:Array<String>).length==1 && !state.psychTextFinished,
   "accept after completion should advance and notify the next line start");
  state.swagDialogue.complete();
  state.updatePsychDialogueInput(true,false);
  check(state.endCalls==1 && state.startCalls==2,
   "accept on a completed final line should end instead of advancing");

  var back=new Main(["unfinished","later"]);
  back.psychInputMode=true;
  back.startDialogue();
  back.updatePsychDialogueInput(false,true);
  check(back.endCalls==1 && back.swagDialogue.skips==0 && back.skipCalls==0,
   "BACK should end immediately without reporting a typewriter skip");

  var native=new Main(["native line","next"]);
  native.psychInputMode=false;
  native.updatePsychDialogueInput(true,false);
  check(native.startCalls==0 && native.endCalls==0 && native.clickCalls==0,
   "the Psych input handler should remain inert for native dialogue");

  var finished=new Main(["finished"]);
  finished.psychInputMode=true;
  finished.nextDialogueThing=function() finished.nextCalls++;
  finished.skipDialogueThing=function() finished.skipCalls++;
  finished.finishThing=function() finished.finishCalls++;
  finished.swagDialogue.completeCallback=function() finished.psychTextFinished=true;
  finished.finishDialogueLifetime();
  check(finished.finishCalls==1 && finished.killCalls==1,
   "dialogue lifetime cleanup should preserve the finish callback and kill the group");
  check(finished.finishThing==null && finished.nextDialogueThing==null
   && finished.skipDialogueThing==null && finished.swagDialogue.completeCallback==null
   && !finished.psychInputMode,
   "dialogue completion should release source callback references");
 }
}'''


class PsychDialogueCallbacksTest(unittest.TestCase):
    def test_psych_input_progression_callbacks_and_native_boundary(self):
        source = (ROOT / "source/DialogueBox.hx").read_text(encoding="utf-8")
        update = function_body(source, "update")
        start = function_body(source, "startDialogue")
        end = function_body(source, "endDialog")
        self.assertIn("if (psychInputMode)", update)
        self.assertIn("PlayerSettings.player1.controls.SECONDARY", update)
        self.assertIn("FlxG.keys.justPressed.ANY", update,
                      "native dialogues must retain SECONDARY-to-end and any-key progression")
        self.assertIn("onPsychDialogueLineStarted()", start)
        self.assertIn("startDialogue();", start,
                      "the skipAfter timer path should route through the same per-line callback")
        self.assertIn("finishDialogueLifetime();", end)

        fixture = FIXTURE.replace("LINE_CALLBACK", function_body(source, "onPsychDialogueLineStarted"))
        fixture = fixture.replace("INPUT", function_body(source, "updatePsychDialogueInput"))
        fixture = fixture.replace("CLEANUP", function_body(source, "finishDialogueLifetime"))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_wires_counted_callbacks_before_showing_source_dialogue(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        prepare = function_body(play, "preparePsychDialogue")
        start = function_body(play, "compatStartDialogue")
        create = function_body(play, "create")
        end_song = function_body(play, "endSong")
        self.assertIn("box.psychInputMode = true", prepare)
        self.assertIn("dialogueCount++", prepare)
        self.assertIn("'onNextDialogue', [dialogueCount]", prepare)
        self.assertIn("'onSkipDialogue', [dialogueCount]", prepare)
        self.assertLess(start.index("preparePsychDialogue(doof)"), start.index("add(doof)"),
                        "dialogue callbacks must be installed before the box starts updating")
        creation = create.index("doof = new DialogueBox(false, goodDialog)")
        root_gate = create.index("if (selectedPsychSkinRoot() != null) preparePsychDialogue(doof)", creation)
        self.assertLess(creation, root_gate,
                        "the selected Psych story factory should prepare its dialogue box")
        for display_call in ("schoolIntro(doof)", "customIntro(doof)"):
            self.assertLess(root_gate, create.index(display_call, root_gate),
                            "the opening dialogue must be prepared before its intro can display it")

        ending_creation = end_song.index("doof = new DialogueBox(false, goodDialog)")
        ending_gate = end_song.index(
            "if (selectedPsychSkinRoot() != null) preparePsychDialogue(doof)", ending_creation)
        ending_display = end_song.index("schoolIntro(doof, false)", ending_gate)
        self.assertLess(ending_creation, ending_gate,
                        "the source ending factory should prepare its dialogue box")
        self.assertLess(ending_gate, ending_display,
                        "ending callbacks must be installed before schoolIntro displays the box")

        fixture = r'''class PsychRuntimeBindings {
 public static var calls:Array<Dynamic>=[];
 public static function dispatch(host:Dynamic,name:String,args:Array<Dynamic>,
  family:String='Scripts',ignoreStops:Bool=false,?hscriptArgs:Array<Dynamic>):Dynamic {
  calls.push({host:host,name:name,args:args.copy(),family:family});
  return 'STOP';
 }
}
class DialogueBox {
 public var psychInputMode:Bool=false;
 public var nextDialogueThing:Void->Void;
 public var skipDialogueThing:Void->Void;
 public var exists:Bool=false;
 public var cameras:Dynamic;
 public function new() {}
}
class Main {
 public var doof:DialogueBox;
 public var members:Array<Dynamic>=[];
 public var camHUD:Dynamic={name:'hud'};
 public var inCutscene:Bool=false;
 public var dialogueCount:Int=0;
 public var addSawPrepared:Bool=false;
 public var countdownCalls:Int=0;
 public function new() doof=new DialogueBox();
 public function add(box:DialogueBox):Void {
  addSawPrepared=box.psychInputMode && box.nextDialogueThing!=null && box.skipDialogueThing!=null;
  box.exists=true;
  members.push(box);
 }
 public function startCountdown():Void countdownCalls++;
 PREPARE
 START
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  PsychRuntimeBindings.calls=[];
  var host=new Main();
  host.compatStartDialogue('dialogue.json','music');
  var first=host.doof;
  check(host.inCutscene && host.members.length==1 && host.addSawPrepared,
   'compatStartDialogue should prepare source callbacks before adding the box');
  first.nextDialogueThing();
  first.skipDialogueThing();
  check(host.dialogueCount==1,'skip should report the current count without incrementing it');
  var second=new DialogueBox();
  host.preparePsychDialogue(second);
  second.nextDialogueThing();
  check(host.dialogueCount==2 && second.psychInputMode,
   'a later dialogue box should preserve and increment the host count');
  check(PsychRuntimeBindings.calls.length==3
   && PsychRuntimeBindings.calls[0].name=='onNextDialogue'
   && PsychRuntimeBindings.calls[0].args[0]==1
   && PsychRuntimeBindings.calls[1].name=='onSkipDialogue'
   && PsychRuntimeBindings.calls[1].args[0]==1
   && PsychRuntimeBindings.calls[2].name=='onNextDialogue'
   && PsychRuntimeBindings.calls[2].args[0]==2,
   'callbacks should receive 1, current-line skip 1, then next-line 2');
  check(host.countdownCalls==0,
   'a STOP return from callback dispatch should not cancel dialogue count updates');
 }
}'''.replace("PREPARE", prepare).replace("START", start)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
