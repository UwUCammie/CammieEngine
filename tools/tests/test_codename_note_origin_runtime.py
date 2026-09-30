"""Executable contract for Codename note-origin propagation at note creation."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_balanced(source: str, start: int, opening: str, closing: str) -> str:
    if source[start] != opening:
        raise AssertionError(f"expected {opening!r} at {start}")
    depth = 0
    quote = None
    escaped = False
    index = start
    while index < len(source):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return source[start + 1:index]
        index += 1
    raise AssertionError(f"unclosed {opening}{closing} expression")


def split_top_level(value: str) -> list[str]:
    parts = []
    start = 0
    stack = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    quote = None
    escaped = False
    for index, char in enumerate(value):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif char in ")]}" and stack and char == stack[-1]:
            stack.pop()
        elif char == "," and not stack:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return parts


def constructor_arguments(source: str, section_start: str, section_end: str) -> list[list[str]]:
    """Extract both traced and direct `new Note(...)` paths in one site."""
    start = source.index(section_start)
    end = source.index(section_end, start)
    calls = []
    cursor = start
    marker = "new Note("
    while True:
        call = source.find(marker, cursor, end)
        if call < 0:
            return calls
        opening = call + len("new Note")
        calls.append(split_top_level(extract_balanced(source, opening, "(", ")")))
        cursor = opening + 1


class CodenameNoteOriginRuntimeTest(unittest.TestCase):
    def test_heads_sustains_and_generated_lifts_keep_distinct_authored_origins(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        note_source = (ROOT / "source/Note.hx").read_text()
        play_source = (ROOT / "source/PlayState.hx").read_text()

        constructor_start = note_source.index("public function new(")
        constructor_open = note_source.index("(", constructor_start)
        constructor_params = split_top_level(
            extract_balanced(note_source, constructor_open, "(", ")")
        )
        self.assertGreaterEqual(len(constructor_params), 6)
        origin_parameter_index = next(
            index for index, parameter in enumerate(constructor_params)
            if "authoredCodenameOrigin:CodenameNoteOrigin" in parameter
        )
        self.assertEqual(origin_parameter_index, 5,
                         "Codename origin must remain Note's optional sixth parameter")
        self.assertIn("authoredMustHit:Null<Bool>", constructor_params[origin_parameter_index + 1],
                      "transient hit-side metadata follows the authored origin")
        origin_parameter = constructor_params[origin_parameter_index]
        self.assertIn("authoredCodenameOrigin:CodenameNoteOrigin", origin_parameter)

        field_declaration = next(
            line.strip() for line in note_source.splitlines()
            if "public var codenameOrigin:CodenameNoteOrigin" in line
        )
        assignment = next(
            line.strip() for line in note_source.splitlines()
            if line.strip() == "codenameOrigin = authoredCodenameOrigin;"
        )

        sites = {
            "head": ("var swagNote:Note;", "if (traceNoteConstruction) markNoteConstructed();"),
            "sustain": ("var sustainNote:Note;", "if (traceNoteConstruction) markNoteConstructed();"),
            "lift": ("var liftNote:Note;", "if (traceNoteConstruction) markNoteConstructed();"),
        }
        origins = {}
        for label, (section_start, section_end) in sites.items():
            calls = constructor_arguments(play_source, section_start, section_end)
            self.assertEqual(len(calls), 2,
                             f"{label} must keep both traced and direct constructor paths")
            expressions = []
            for args in calls:
                self.assertEqual(len(args), 7,
                                 f"{label} must pass origin and transient hit-side arguments")
                expression = args[origin_parameter_index].replace("Note.NOTE_AMOUNT", "4")
                self.assertEqual(args[origin_parameter_index + 1], "gottaHitNote",
                                 f"{label} must pass the transient hit side separately")
                self.assertIn("CodenameNoteMetadata.read(songNotes, section.mustHitSection, 4)",
                              expression)
                expressions.append(expression)
            self.assertEqual(expressions[0], expressions[1],
                             f"{label} traced and direct paths must preserve the same origin")
            origins[label] = expressions[0]

        # Use the exact optional parameter and assignment from Note, and exact
        # sixth-argument expressions from PlayState. The real metadata reader
        # is compiled from source/CodenameNoteMetadata.hx below.
        fixture = f'''import CodenameNoteMetadata.CodenameNoteOrigin;
class Main {{
 static function fail(message:String):Void throw message;
 static function main() {{
  var section:Dynamic = {{mustHitSection:false}};
  var songNotes:Array<Dynamic> = [1200, 0, 375];
  while (songNotes.length < 13) songNotes.push(null);
  songNotes.push({{engine:"codename", version:1, lineIndex:2, noteIndex:7,
   lineType:1, nativeSide:1}});
  var authored:CodenameNoteOrigin = CodenameNoteMetadata.read(songNotes,
   section.mustHitSection, 4);
  if (authored == null || songNotes[1] != 0)
   fail("valid source identity was not readable without changing the row");

  // This models the no-opponent modifier changing the transient input side.
  // The source section and chart row remain authored data.
  var gottaHitNote:Bool = section.mustHitSection;
  var noOpponentModifier:Bool = true;
  if (noOpponentModifier && !gottaHitNote) gottaHitNote = true;

  var head = new NoteOriginProbe({origins["head"]});
  var sustainA = new NoteOriginProbe({origins["sustain"]});
  var sustainB = new NoteOriginProbe({origins["sustain"]});
  var generatedLift = new NoteOriginProbe({origins["lift"]});
  head.mustPress = gottaHitNote;
  sustainA.mustPress = gottaHitNote;
  sustainB.mustPress = gottaHitNote;
  generatedLift.mustPress = gottaHitNote;

  if (!head.mustPress || !sustainA.mustPress || !sustainB.mustPress || !generatedLift.mustPress)
   fail("modifier was not applied to transient input routing");
  if (songNotes[1] != 0 || section.mustHitSection != false)
   fail("input modifier rewrote the authored chart side");
  for (note in [head, sustainA, sustainB, generatedLift]) {{
   var origin:CodenameNoteOrigin = note.codenameOrigin;
   if (origin == null || origin.engine != "codename" || origin.lineIndex != 2
    || origin.noteIndex != 7 || origin.lineType != 1 || origin.nativeSide != 1)
    fail("authored origin was lost or changed");
  }}

  if (head.codenameOrigin == sustainA.codenameOrigin
   || head.codenameOrigin == sustainB.codenameOrigin
   || head.codenameOrigin == generatedLift.codenameOrigin
   || sustainA.codenameOrigin == sustainB.codenameOrigin
   || sustainA.codenameOrigin == generatedLift.codenameOrigin
   || sustainB.codenameOrigin == generatedLift.codenameOrigin)
   fail("generated notes share mutable origin objects");
  head.codenameOrigin.lineIndex = 99;
  if (sustainA.codenameOrigin.lineIndex != 2 || sustainB.codenameOrigin.lineIndex != 2
   || generatedLift.codenameOrigin.lineIndex != 2 || authored.lineIndex != 2)
   fail("mutating one runtime origin changed another note or source identity");

  // Existing non-Codename Note call sites omit the optional sixth argument.
  var legacy = new NoteOriginProbe();
  if (legacy.codenameOrigin != null)
   fail("legacy constructor behavior gained a Codename origin");
  Sys.println("OK");
 }}
}}

class NoteOriginProbe {{
 {field_declaration}
 public var mustPress:Bool = false;
 public function new({origin_parameter}) {{
  {assignment}
 }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "--run", "Main"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
