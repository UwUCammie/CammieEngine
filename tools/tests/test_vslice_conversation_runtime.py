"""V-Slice conversations open in the base dialogue box, and song load/retry events carry their data."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

CONVERSATION = {
    "version": "1.0.0",
    "backdrop": {"type": "solid", "fadeTime": 1.0, "color": "#80000000"},
    "music": {"asset": "talkLoop", "fadeTime": 1.0, "looped": True},
    "outro": {"type": "fade", "fadeTime": 1.0},
    "dialogue": [
        {"speaker": "visitor", "speakerAnimation": "talk", "box": "plain", "boxAnimation": "enter",
         "text": ["First page.", "Second page."]},
        {"speaker": "bf", "box": "pixel", "text": ["Reply."]},
        {"speaker": "visitor", "box": "plain", "text": []},
    ],
}

INTRO_SONG = '''
class IntroSong extends Song {
    var seen:Bool = false;
    function new() { super("intro-song"); }
    override function onCountdownStart(event) {
        super.onCountdownStart(event);
        if (!seen) {
            seen = true;
            event.cancel();
            showTalk();
        }
    }
    function showTalk() {
        PlayState.instance.startConversation("intro-talk");
    }
    override function onDialogueEnd(event) {
        trace("talk over");
    }
}
'''


class VSliceConversationRuntimeTest(unittest.TestCase):
    def run_fixture(self, body):
        fixture = f'''import hscript.Interp;
import hscript.Parser;
class ConversationFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
{body}
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "ConversationFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "ConversationFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_conversation_becomes_base_dialogue_lines(self):
        self.run_fixture(f'''
        var data = haxe.Json.parse({json.dumps(json.dumps(CONVERSATION))});
        var lines = VSliceConversation.lines(data);
        if (lines.length != 3) fail("pages " + lines.length);
        if (lines[0].text != "First page." || lines[1].text != "Second page." || lines[2].text != "Reply.")
            fail("page order");
        if (lines[1].speaker != "visitor" || lines[2].speaker != "bf" || lines[2].box != "pixel") fail("speaker or box");
        var text = VSliceConversation.dialogueText(data, "player-one", "player-two");
        var rows = text.split("\\n");
        // One settings row, then one row per page.
        if (rows.length != 4) fail("rows " + rows.length);
        if (rows[1].indexOf("First page.") < 0 || rows[3].indexOf("Reply.") < 0) fail("text rows");
        if (rows[3].indexOf(":player-one:") != 0) fail("boyfriend line not on the player side: " + rows[3]);
        if (rows[3].indexOf("#pixel_normal#") < 0) fail("pixel box");
        if (VSliceConversation.musicAsset(data) != "talkLoop") fail("music");
        if (VSliceConversation.dialogueText(haxe.Json.parse('{{"dialogue": []}}')) != null) fail("empty conversation");
        if (VSliceConversation.musicAsset(haxe.Json.parse('{{}}')) != null) fail("no music");
        var paths = VSliceConversation.candidatePaths("mods/pack/", "intro-talk");
        if (paths[0] != "mods/pack/data/dialogue/conversations/intro-talk.json") fail("first path " + paths[0]);
        if (paths.indexOf("mods/pack/data/dialogue/conversations/intro-talk/intro-talk.json") < 0) fail("folder layout");
        for (bad in ["../secret", "/abs", "c:/x", "", "a//b"])
            if (VSliceConversation.candidatePaths("root", bad).length != 0) fail("unsafe id accepted: " + bad);
        if (VSliceConversation.safeId("talk.json") != "talk") fail("extension");
        ''')

    def test_dialogue_and_song_events_carry_their_fields(self):
        self.run_fixture('''
        var start = EngineCompat.hxcDialoguePayload("dialogueStart", "intro-talk", 0);
        if (start.conversationId != "intro-talk" || start.conversation.id != "intro-talk") fail("conversation id");
        start.cancel();
        if (!EngineCompat.hxcPayloadCanceled(start)) fail("dialogue start not cancelable");
        var line = EngineCompat.hxcDialoguePayload("dialogueLine", "intro-talk", 2);
        if (line.line != 2 || line.conversation.currentDialogueEntry != 2) fail("line index");
        var retry = EngineCompat.hxcSongRetryPayload("hard");
        if (retry.difficulty != "hard" || retry.eventData.value.difficulty != "hard") fail("retry difficulty");
        var notes:Array<Dynamic> = [{time: 0, data: 1, length: 0, kind: ""}, {time: 500, data: 2, length: 100, kind: "alt"}];
        var events:Array<Dynamic> = [{time: 0, eventKind: "FocusCamera"}];
        var loaded = EngineCompat.hxcSongLoadPayload("some-song", "erect", notes, events);
        if (loaded.id != "some-song" || loaded.difficulty != "erect") fail("song id or difficulty");
        if (loaded.notes.length != 2 || loaded.notes[1].kind != "alt" || loaded.events.length != 1) fail("notes or events");
        var empty = EngineCompat.hxcSongLoadPayload(null, null, null, null);
        if (empty.notes.length != 0 || empty.events.length != 0 || empty.id != "") fail("empty load event");
        ''')

    def test_song_script_starting_a_conversation_translates_to_the_base_call(self):
        self.run_fixture(f'''
        var result = HxcCompat.translate({json.dumps(INTRO_SONG)}, "scripts/songs/intro.hxc");
        for (name in ["countdownStart", "dialogueEnd"])
            if (result.canonicalCallbacks.indexOf(name) < 0) fail("not routed: " + name);
        if (result.generatedHscript.indexOf("startConversation(") < 0) fail("conversation call dropped");
        for (finding in (cast result.diagnostics:Array<Dynamic>))
            if (finding.code == "unsupported-hxc-callback-body") fail("diagnosed: " + finding.message);
        ''')

    def test_playstate_runs_the_conversation_through_the_base_dialogue(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        start = source[source.index("@:keep public function startConversation("):source.index("@:keep public var dialogueCount")]
        # Same box as Psych's startDialogue.
        self.assertIn("showDialogueFromData(text, VSliceConversation.musicAsset(data), finishConversation,", start)
        self.assertLess(start.index("callAllHScript('dialogueStart', [opening]);"),
                        start.index("conversationData(id)"))
        # A conversation that cannot be found or shown still lets the song start.
        missing = start[start.index("if (text == null) {"):]
        self.assertIn("finishConversation();", missing[:missing.index("}")])
        finish = start[start.index("function finishConversation("):]
        self.assertLess(finish.index("callAllHScript('dialogueEnd'"), finish.index("startCountdown();"))
        self.assertIn("if (startingSong && !startedCountdown)", finish)
        prepare = start[start.index("function prepareConversationBox("):start.index("function finishConversation(")]
        for kind in ("dialogueCompleteLine", "dialogueSkip", "dialogueLine"):
            self.assertIn("'" + kind + "'", prepare)
        self.assertIn("if (EngineCompat.hxcPayloadCanceled(event))\n\t\t\t\treturn false;", prepare)
        box = (ROOT / "source/DialogueBox.hx").read_text(encoding="utf-8", errors="ignore")
        update = box[box.index("function updatePsychDialogueInput("):box.index("function playDialogueClick(")]
        # A refused press changes nothing, not even the click sound.
        self.assertLess(update.index("if (allowInputThing != null && !allowInputThing(action))"),
                        update.index("playDialogueClick();"))
        retry = source[source.index("@:keep public function restartSong("):]
        self.assertIn("callAllHScript('songRetry', [], false, null, [EngineCompat.hxcSongRetryPayload(hxcDifficultyId())]);",
                      retry[:2000])


if __name__ == "__main__":
    unittest.main()
