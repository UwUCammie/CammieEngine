"""Imported stage z-order keeps gameplay notes above receptor graphics."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class StageHudNoteOrderTest(unittest.TestCase):
    def test_imported_hud_props_leave_notes_above_receptors(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction layerNativeStageHudOverProps():Void {")
        end = source.index("\n\tfunction addHscriptSprite(", start)
        methods = source[start:end].replace("FlxSprite", "FakeBasic").replace(
            "FlxBasic", "FakeBasic"
        )
        fixture = r'''
class FakeBasic {
 public var exists:Bool = true;
 public var cameras:Array<FakeBasic> = [];
 public var z:Int = 0;
 public function new() {}
}
class FakeStrumline extends FakeBasic {
 public var noteHoldCovers:FakeBasic = new FakeBasic();
 public function new() { super(); }
}
class HxcCompatRuntime {
 public static function getZIndex(target:FakeBasic):Int return target == null ? 0 : target.z;
 public static function setZIndex(target:FakeBasic, value:Int):Void if (target != null) target.z = value;
}
class StageHudOrderFixture {
 var camHUD:FakeBasic = new FakeBasic();
 var importedStageHudProps:Array<FakeBasic> = [];
 var members:Array<FakeBasic> = [];
 var songPosBG:FakeBasic;
 var songName:FakeBasic;
 var playerStrums:FakeStrumline = new FakeStrumline();
 var enemyStrums:FakeStrumline = new FakeStrumline();
 var codenameStrumlines:Array<Null<FakeStrumline>> = [];
 var notes:FakeBasic = new FakeBasic();
 var grpNoteSplashes:FakeBasic = new FakeBasic();
 var healthBarBG:FakeBasic;
 var healthBar:FakeBasic;
 var iconP1:FakeBasic;
 var iconP2:FakeBasic;
 var scoreTxt:FakeBasic;
 var missesTxt:FakeBasic;
 var healthTxt:FakeBasic;
 var accuracyTxt:FakeBasic;
 var difficTxt:FakeBasic;
 public function new() {}
 function refresh():Void members.sort((left, right) -> left.z - right.z);
''' + methods + r'''
 static function main() {
  var state = new StageHudOrderFixture();
  var stageProp = new FakeBasic();
  stageProp.z = 50;
  stageProp.cameras = [state.camHUD];
  state.importedStageHudProps.push(stageProp);
  state.members = [stageProp, state.playerStrums, state.enemyStrums, state.notes,
   state.enemyStrums.noteHoldCovers, state.playerStrums.noteHoldCovers,
   state.grpNoteSplashes];
  state.layerNativeStageHudOverProps();
  if (state.members.indexOf(stageProp) >= state.members.indexOf(state.playerStrums)
   || state.members.indexOf(state.playerStrums) >= state.members.indexOf(state.notes)
   || state.members.indexOf(state.enemyStrums) >= state.members.indexOf(state.notes)
   || state.members.indexOf(state.notes) >= state.members.indexOf(state.grpNoteSplashes))
    throw 'imported HUD sorting buried gameplay notes or their effects';
  var withRaisedReceptor = new StageHudOrderFixture();
  var secondProp = new FakeBasic();
  secondProp.z = 50;
  secondProp.cameras = [withRaisedReceptor.camHUD];
  withRaisedReceptor.playerStrums.z = 5000;
  withRaisedReceptor.importedStageHudProps.push(secondProp);
  withRaisedReceptor.members = [secondProp, withRaisedReceptor.playerStrums,
   withRaisedReceptor.enemyStrums, withRaisedReceptor.notes,
   withRaisedReceptor.grpNoteSplashes];
  withRaisedReceptor.layerNativeStageHudOverProps();
  if (withRaisedReceptor.members.indexOf(withRaisedReceptor.notes)
      <= withRaisedReceptor.members.indexOf(withRaisedReceptor.playerStrums))
    throw 'an existing receptor z index still buried gameplay notes';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "StageHudOrderFixture.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "StageHudOrderFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
