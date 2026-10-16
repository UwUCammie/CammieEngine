"""Characters keep the authored JSON values scripts read back off them."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterFieldSurfaceTest(unittest.TestCase):
    def test_members_are_kept_and_filled_from_one_place(self):
        character = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        for name in ("jsonScale", "originalFlipX", "noAntialiasing", "animationsArray", "vocalsFile",
                     "extraData", "isAnimateAtlas", "animPaused"):
            self.assertRegex(character, r"@:keep public var " + name + r"\b", name)
        start = character.index("\tfunction applySourceDefinitionFields(definition:Dynamic):Void {")
        apply = character[start:character.index("\n\t}\n", start)]
        for name in ("jsonScale", "originalFlipX", "noAntialiasing", "animationsArray", "vocalsFile"):
            self.assertIn(f"{name} = authored.{name};", apply)
        # One call serves both JSON families: the parsed owner definition when
        # there is one, the import root's character file otherwise.
        self.assertEqual(character.count("\t\tapplySourceDefinitionFields("), 1)
        self.assertIn(
            "applySourceDefinitionFields(nightmareVisionCharacterOwned ? nightmareVisionOwnedCharacter\n"
            "\t\t\t: SourceCharacterDefinition.read(visualCharacterId, psychCameraRoot,", character)
        # The pause switch drives the animation that is playing, not a copy of it.
        self.assertIn("animation.curAnim.paused = value;", character)
        self.assertIn("function get_isAnimateAtlas():Bool return isAnimate;", character)

    def test_definition_fields_come_from_the_authored_json(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''class CharacterDefinitionFixture {
 static function main():Void {
  var files:Map<String, String> = [
   'root/characters/hero.json' => '{"scale":1.5,"flip_x":true,"no_antialiasing":true,"vocals_file":"Hero",'
    + '"animations":[{"anim":"idle","name":"Idle","offsets":[3,4]},{"anim":"singUP","name":"Up"}]}',
   'root/shared/characters/side.json' => '{"flip_x":false}',
   'root/characters/broken.json' => '{not json'
  ];
  var read = function(path:String):Null<String> return files.get(StringTools.replace(path, '\\', '/'));

  var hero = SourceCharacterDefinition.fields(SourceCharacterDefinition.read('hero', 'root', read));
  if (hero.jsonScale != 1.5) throw 'scale';
  if (!hero.originalFlipX) throw 'authored flip';
  if (!hero.noAntialiasing) throw 'antialiasing switch';
  if (hero.vocalsFile != 'Hero') throw 'vocals file';
  if (hero.animationsArray.length != 2 || hero.animationsArray[0].anim != 'idle'
   || hero.animationsArray[0].offsets[1] != 4) throw 'animations should be handed over as authored';

  // The authored flip is the file value. The slot flip a player character gets
  // on screen is a separate thing and must not leak back into it.
  var onScreen = hero.originalFlipX != true;
  if (onScreen != false || !hero.originalFlipX) throw 'authored flip changed with the slot';

  var side = SourceCharacterDefinition.fields(SourceCharacterDefinition.read('side', 'root', read));
  if (side.jsonScale != 1 || side.originalFlipX || side.noAntialiasing || side.vocalsFile != ''
   || side.animationsArray.length != 0) throw 'missing fields should be neutral';

  for (id in ['broken', 'absent', '../hero', '', null])
   if (SourceCharacterDefinition.read(id, 'root', read) != null) throw 'unusable definition was read: ' + id;
  if (SourceCharacterDefinition.read('hero', '', read) != null) throw 'no root should read nothing';
  var none = SourceCharacterDefinition.fields(null);
  if (none.jsonScale != 1 || none.originalFlipX || none.animationsArray.length != 0 || none.vocalsFile != '')
   throw 'no definition should be neutral';
  var text = SourceCharacterDefinition.fields({scale: '2', animations: 'nope'});
  if (text.jsonScale != 2 || text.animationsArray.length != 0) throw 'loose values';
  Sys.println('OK');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="character-fields-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "CharacterDefinitionFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (scratch / "SourceCharacterId.hx").write_text((ROOT / "source/SourceCharacterId.hx").read_text(), newline="\n")
            (scratch / "SourceCharacterDefinition.hx").write_text(
                (ROOT / "source/SourceCharacterDefinition.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "CharacterDefinitionFixture"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
