"""Generated V-Slice stage/character framing matches the donor engine's math.

The donor engine (verified against the 0.7.3/0.8.1 sources) frames imported
stages like this:

* ``BaseCharacter.resetCharacter`` dances first (danceLeft when a pair exists,
  otherwise idle - ``CharacterData.startingAnimation`` is parsed but never
  consumed for characters) and then ``updateHitbox`` so the hitbox is the
  opening pose's frame cell.  ``Stage.addCharacter`` anchors
  ``position - characterOrigin`` (feet) from that hitbox and
  ``BaseCharacter.setScale`` re-adds the authored ``offsets``.
* The camera focus is ``midpoint + CharacterData.cameraOffsets + stage
  cameraOffsets`` (``cameraFocusPoint``), so a stage's authored offsets are
  absolute and stack on top of the character's own.

Reported as "every character sits to the bottom right of where they should
be" on Vs Tricky Expurgation: the converted stage anchored characters with
whatever hitbox the actor happened to have (the atlas's first frame), dropped
the character-level camera offsets, and the classic per-branch camera
constants stacked on top of the authored ones.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


class VSliceStageFramingTest(unittest.TestCase):
    def convert_character(self, character: dict) -> str:
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/framehero.png").write_bytes(b"png")
            (fixture / "images/characters/framehero.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-framehero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            output_path = fixture / "out.txt"
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    sys.io.File.saveContent({haxe_string(str(output_path))}, converted.hscript);
  }}
}}
'''
            with tempfile.TemporaryDirectory() as build:
                Path(build, "Main.hx").write_text(main)
                result = subprocess.run(
                    [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                     "-cp", build, "-main", "Main", "--interp"],
                    cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return output_path.read_text()

    def convert_stage(self, stage: dict, assets: dict[str, bytes] | None = None) -> str:
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            for relative, content in (assets or {}).items():
                asset = fixture / relative
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.write_bytes(content)
            stage_path = fixture / "stage.json"
            stage_path.write_text(json.dumps(stage))
            output_path = fixture / "out.txt"
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(str(stage_path))})), {haxe_string(str(fixture))});
    sys.io.File.saveContent({haxe_string(str(output_path))}, converted.hscript);
  }}
}}
'''
            with tempfile.TemporaryDirectory() as build:
                Path(build, "Main.hx").write_text(main)
                result = subprocess.run(
                    [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                     "-cp", build, "-main", "Main", "--interp"],
                    cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return output_path.read_text()

    def test_scaled_prop_graphic_bounds_use_authored_top_left(self):
        """Run generated transforms through Flixel's actual bounds equations.

        FlxSprite.updateHitbox sets offset to half the scale delta; without it,
        circo's 1920x1080 sheet renders 864px left and 486px above its authored
        position. The same rule applies to a two-value scale like Auditor Hell.
        """
        generated = self.convert_stage({
            "version": "1.0.2", "name": "Framing Probe", "characters": {},
            "props": [
                {"name": "circo", "assetPath": "stages/circo", "position": [-1367, -1019],
                 "scale": 1.9, "animType": "none"},
                {"name": "bg", "assetPath": "stages/bg", "position": [-1400, -2100],
                 "scale": [4, 4], "animType": "none"},
            ],
        }, {"images/stages/circo.png": b"png", "images/stages/bg.png": b"png"})
        names = [re.search(rf"vSliceProp_{label}_\d+", generated).group(0)
                 for label in ("circo", "bg")]
        snippets = []
        for name in names:
            start = generated.index(f"    {name} = new FlxSprite")
            end = generated.index(f"    {name}.scrollFactor", start)
            snippets.append(generated[start:end])
        source = r'''import hscript.Interp;
import hscript.Parser;
class Pair {
 public var x:Float=0; public var y:Float=0;
 public function new() {}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class FakeSprite {
 public static var nextWidth:Float=0; public static var nextHeight:Float=0;
 public var x:Float=0; public var y:Float=0;
 public var width:Float=0; public var height:Float=0;
 public var frameWidth:Float=0; public var frameHeight:Float=0;
 public var scale:Pair=new Pair(); public var offset:Pair=new Pair();
 public var origin:Pair=new Pair();
 public function new() {scale.set(1,1);}
 public function loadGraphic(_path:String):Void {
  frameWidth=nextWidth;frameHeight=nextHeight;
  width=frameWidth;height=frameHeight;
  origin.set(frameWidth/2,frameHeight/2);
 }
 public function updateHitbox():Void {
  width=Math.abs(scale.x)*frameWidth;height=Math.abs(scale.y)*frameHeight;
  offset.set(-0.5*(width-frameWidth),-0.5*(height-frameHeight));
  origin.set(frameWidth/2,frameHeight/2);
 }
 public function graphicLeft():Float return x+origin.x-offset.x-origin.x*scale.x;
 public function graphicTop():Float return y+origin.y-offset.y-origin.y*scale.y;
}
class Main {
 static function check(script:String,width:Float,height:Float,name:String,x:Float,y:Float):Void {
  FakeSprite.nextWidth=width;FakeSprite.nextHeight=height;
  var interp=new Interp();
  interp.variables.set("FlxSprite",FakeSprite);
  interp.variables.set("hscriptPath","");
  interp.variables.set(name,null);
  interp.execute(new Parser().parseString(script));
  var sprite:FakeSprite=cast interp.variables.get(name);
  if(sprite==null || Math.abs(sprite.graphicLeft()-x)>0.0001
    || Math.abs(sprite.graphicTop()-y)>0.0001)
   throw 'rendered bounds differ from stage position: '+name+' '+(sprite==null?'null':sprite.graphicLeft()+','+sprite.graphicTop()+' vs '+x+','+y);
  if(Math.abs(sprite.width-width*sprite.scale.x)>0.0001
    || Math.abs(sprite.height-height*sprite.scale.y)>0.0001)
   throw 'scaled hitbox differs from rendered size: '+name;
 }
 static function main():Void {
  check(SCRIPT0,1920,1080,"NAME0",-1367,-1019);
  check(SCRIPT1,640,360,"NAME1",-1400,-2100);
 }
}
'''.replace("SCRIPT0", haxe_string(snippets[0])).replace("SCRIPT1", haxe_string(snippets[1]))
        source = source.replace("NAME0", names[0]).replace("NAME1", names[1])
        with tempfile.TemporaryDirectory() as build:
            Path(build, "Main.hx").write_text(source)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", build, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_opening_pose_is_the_donor_first_dance_tick_with_its_hitbox(self):
        """No authored startingAnimation: the donor opens on idle and measures
        the anchor hitbox from it (resetCharacter -> dance -> updateHitbox).
        The generated init must play idle and then updateHitbox, so the stage
        script's position - origin anchoring lands on the donor feet point."""
        generated = self.convert_character({
            "version": "1.0.0",
            "name": "Frame Hero",
            "assetPath": "characters/framehero",
            "healthIcon": {"id": "framehero"},
            "animations": [
                {"name": "idle", "prefix": "Idle"},
                {"name": "singLEFT", "prefix": "Sing Left", "offsets": [127, 20]},
                {"name": "Hank", "prefix": "Hank", "looped": True},
            ],
        })
        init_play = '    char.playAnim("idle");\n    char.updateHitbox();\n}'
        self.assertIn(init_play, generated)
        self.assertLess(generated.index(init_play), generated.index("function update(elapsed, char)"))
        self.assertNotIn('char.playAnim("singLEFT");', generated)
        # the dance fallback stays on idle
        self.assertIn('function dance(char) {\n    char.playAnim("idle");\n}', generated)

    def test_character_starting_animation_is_not_consumed_like_the_donor(self):
        """The donor parses CharacterData.startingAnimation but never plays it:
        a danceLeft/danceRight character opens on danceLeft (first dance tick)
        even when startingAnimation says danceRight.  The stage tick still
        alternates the pair like the donor beat bop."""
        generated = self.convert_character({
            "version": "1.0.0",
            "name": "Tied Hero",
            "assetPath": "characters/framehero",
            "startingAnimation": "danceRight",
            "healthIcon": {"id": "framehero"},
            "animations": [
                {"name": "danceLeft", "prefix": "GF Ex", "frameIndices": [30, 0, 1]},
                {"name": "danceRight", "prefix": "GF Ex", "frameIndices": [2, 3, 4]},
            ],
        })
        self.assertIn('    char.playAnim("danceLeft");\n    char.updateHitbox();\n}', generated)
        self.assertNotIn('    char.playAnim("danceRight");\n', generated)
        self.assertIn("vSliceHasDanced = false;", generated)

    def test_character_camera_offsets_survive_stage_recomposition(self):
        """CharacterData.cameraOffsets are absolute in the donor and stack with
        the stage's authored offsets.  The generated character keeps them in
        dedicated fields so an imported stage can zero the classic follow
        defaults and recompose stage + character offsets."""
        generated = self.convert_character({
            "version": "1.0.0",
            "name": "Cam Hero",
            "assetPath": "characters/framehero",
            "cameraOffsets": [-18, 36],
            "offsets": [17, 14],
            "healthIcon": {"id": "framehero"},
            "animations": [
                {"name": "idle", "prefix": "Idle"},
            ],
        })
        self.assertIn("char.vSliceCamOffsetX = -18;", generated)
        self.assertIn("char.vSliceCamOffsetY = 36;", generated)
        # the standalone accumulation remains for classic-stage usage
        self.assertIn("char.followCamX += -18;", generated)
        self.assertIn("char.followCamY += 36;", generated)

    def test_stage_anchor_is_feet_plus_authored_global_offsets(self):
        """auditorHell-shaped stage: the bf slot anchor must be
        position - origin (feet) + the character's authored offsets, exactly
        the donor's Stage.addCharacter + BaseCharacter.setScale composition,
        with the stage camera offsets applied absolutely."""
        generated = self.convert_stage({
            "version": "1.0.0",
            "name": "Auditor Hell",
            "cameraZoom": 0.55,
            "characters": {
                "bf": {"zIndex": 300, "position": [2160, 1300], "cameraOffsets": [-100, -300]},
                "dad": {"zIndex": 200, "position": [1150, 1200], "cameraOffsets": [300, -50]},
                "gf": {"zIndex": 100, "position": [1750, 1140], "cameraOffsets": [0, 0]},
            },
            "props": [],
        })
        self.assertIn('setDefaultZoom(0.55);', generated)
        self.assertIn('boyfriend.x = 2160 - boyfriend.width / 2 + boyfriend.playerOffsetX;', generated)
        self.assertIn('boyfriend.y = 1300 - boyfriend.height + boyfriend.playerOffsetY;', generated)
        self.assertIn('stage.setOffsets("bf", 2160 - boyfriend.width / 2 + boyfriend.playerOffsetX, '
                      '1300 - boyfriend.height + boyfriend.playerOffsetY, false);', generated)
        self.assertIn('dad.x = 1150 - dad.width / 2 + dad.enemyOffsetX;', generated)
        self.assertIn('gf.x = 1750 - gf.width / 2 + gf.gfOffsetX;', generated)
        # camera offsets are absolute and the classic defaults are cancelled
        self.assertIn('boyfriend.followCamX = 0;', generated)
        self.assertIn('stage.setCamOffsets("bf", -100, -300, false);', generated)
        self.assertIn('stage.setCamOffsets("dad", 300, -50, false);', generated)

    def test_runtime_camera_composition_prefers_authored_offsets(self):
        """The runtime must compose the focus as midpoint + authored offsets
        when an imported stage owns the framing: StageHelper.setCamOffsets
        reapplies the character's vSlice offsets, and PlayState's FocusCamera /
        per-frame follow skip the classic bfCamOffset/dadCamOffset constants
        and per-animation nudges for authored actors."""
        stage_helper = (ROOT / "source/StageHelper.hx").read_text()
        self.assertIn("actor.followCamX = offx + actor.vSliceCamOffsetX;", stage_helper)
        self.assertIn("actor.followCamY = offy + actor.vSliceCamOffsetY;", stage_helper)
        self.assertIn("actor.authoredCamOffsets = true;", stage_helper)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        # FocusCamera and per-frame follow share one role composer. Psych uses
        # its own role baseline only when a selected namespace is non-empty;
        # native and V-Slice keep their prior follow values and FocusCamera
        # still excludes directional turn nudges.
        self.assertIn("targetPos = cameraTargetForActor(boyfriend, 'boyfriend', x, y, false);", play_state)
        self.assertIn("targetPos = cameraTargetForActor(dad, 'dad', x, y, false);", play_state)
        self.assertIn("if (psychCameraCompatibilityActive && !actor.authoredCamOffsets)", play_state)
        self.assertIn("actor.followCamX + (includeTurnNudge ? bfcam[0] : 0);", play_state)
        self.assertIn("actor.followCamX + (includeTurnNudge ? dadcam[0] : 0);", play_state)
        self.assertIn("if (psychCameraCompatibilityActive || dad.authoredCamOffsets)", play_state)
        self.assertIn("if (psychCameraCompatibilityActive || boyfriend.authoredCamOffsets)", play_state)
        self.assertIn("cameraTargetForActor(boyfriend, 'boyfriend',", play_state)
        self.assertIn("setCameraFollowActor(dad, 'dad');", play_state)

        character = (ROOT / "source/Character.hx").read_text()
        self.assertIn("public var vSliceCamOffsetX:Int = 0;", character)
        self.assertIn("public var vSliceCamOffsetY:Int = 0;", character)
        self.assertIn("public var authoredCamOffsets:Bool = false;", character)
        self.assertIn("public var psychInitialFollowCamX:Int = 150;", character)
        # mid-song swaps recompose the same way
        self.assertIn("newChar.followCamX = charInfo.camOffsetX + newChar.vSliceCamOffsetX;", play_state)


if __name__ == "__main__":
    unittest.main()
