"""Psych stage points include character JSON position, even for base actors."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)
PSYCH_SOURCE = Path('/run/media/cammie/External Storage/psych_source_code/assets')


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class PsychCharacterPositionTest(unittest.TestCase):
    def test_base_data_matches_psych_definitions(self):
        imported = json.loads((ROOT / 'assets/data/psych_base_character_positions.json').read_text())
        source_files = list(PSYCH_SOURCE.glob('**/characters/*.json'))
        if not source_files:
            self.skipTest('local Psych source checkout is unavailable')
        expected = {}
        for path in source_files:
            position = json.loads(path.read_text()).get('position')
            if position and position[:2] != [0, 0]:
                expected[path.stem] = position[:2]
        self.assertEqual(imported, expected)

    def test_scoped_character_precedes_native_and_base_position(self):
        stage = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn("var bfPosition = stageCharacterOffset(boyfriend, 'boyfriend');", stage)
        self.assertIn('applyPsychStageJson(Path.join([Path.directory(entry.path), stem + \'.json\']), compatRoot);', stage)
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'PsychCharacterPosition.hx').write_text(
                (ROOT / 'source/PsychCharacterPosition.hx').read_text(), newline='\n')
            (work / 'assets/data').mkdir(parents=True)
            (work / 'assets/data/psych_base_character_positions.json').write_text(
                (ROOT / 'assets/data/psych_base_character_positions.json').read_text(), newline='\n')
            (work / 'scope/characters').mkdir(parents=True)
            (work / 'scope/characters/bf.json').write_text('{"position":[12,-5]}', newline='\n')
            (work / 'scope/characters/dad.json').write_text('{"position":[0,0]}', newline='\n')
            (work / 'scope2/characters').mkdir(parents=True)
            (work / 'scope2/characters/bf.json').write_text('{"position":[20,40]}', newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Probe.hx').write_text('''
class Probe {
  static function eq(actual:Array<Float>, x:Float, y:Float):Void
    if (actual[0] != x || actual[1] != y) throw 'position mismatch: ' + actual;
  static function main():Void {
    eq(PsychCharacterPosition.resolve('bf', 'scope'), 12, -5);
    eq(PsychCharacterPosition.resolve('bf', 'scope2'), 20, 40);
    eq(PsychCharacterPosition.resolve('bf', 'missing'), 0, 350);
    eq(PsychCharacterPosition.resolve('dad', 'scope', 8, 9), 0, 0);
    eq(PsychCharacterPosition.resolve('bf', 'missing', 7, 11), 7, 11);
    eq(PsychCharacterPosition.resolve('nobody', 'missing'), 0, 0);
    eq(PsychCharacterPosition.resolve('../bf', 'scope'), 0, 0);
    // A stage point plus the Psych base BF metadata.
    var offset = PsychCharacterPosition.resolve('bf', 'missing');
    eq([749 + offset[0], 100 + offset[1]], 749, 450);
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_position_preserves_raw_values_and_uses_psych_role_signs(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'PsychCharacterPosition.hx').write_text(
                (ROOT / 'source/PsychCharacterPosition.hx').read_text(), newline='\n')
            (work / 'scope/characters').mkdir(parents=True)
            (work / 'scope/shared/characters').mkdir(parents=True)
            (work / 'scope/characters/bf.json').write_text('{"camera_position":[12,-5]}', newline='\n')
            (work / 'scope/characters/dad.json').write_text('{"camera_position":[-2,8]}', newline='\n')
            (work / 'scope/shared/characters/gf.json').write_text('{"camera_position":[30,4]}', newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Probe.hx').write_text('''
class Probe {
  static function eq(actual:Array<Float>, x:Float, y:Float, label:String):Void
    if (actual == null || actual.length < 2 || actual[0] != x || actual[1] != y)
      throw label + ': ' + actual;
  static function main():Void {
    var bf = PsychCharacterPosition.characterCameraPosition('bf', 'scope');
    eq(bf, 12, -5, 'Psych raw BF camera_position changed');
    eq(PsychCharacterPosition.roleCameraOffset(bf, 'boyfriend'), -12, -5,
      'BF must subtract camera_position X and add Y');
    eq(PsychCharacterPosition.roleCameraOffset(bf, 'player1'), -12, -5,
      'player1 alias must keep BF sign convention');
    eq(PsychCharacterPosition.roleCameraOffset([-2, 8], 'dad'), -2, 8,
      'opponent must add both camera_position coordinates');
    eq(PsychCharacterPosition.roleCameraOffset([30, 4], 'gf'), 30, 4,
      'GF must add both camera_position coordinates');
    bf[0] = 99;
    eq(PsychCharacterPosition.roleCameraOffset(bf, 'bf'), -99, -5,
      'role mapping must read a live script-edited cameraPosition array');
    eq(PsychCharacterPosition.characterCameraPosition('missing', 'scope'), 0, 0,
      'missing Psych metadata must stay neutral');
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_point_and_swap_offset_lifecycle(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        for call in (
            "rememberPsychStagePoint('bf', bfPoint);",
            "rememberPsychStagePoint('dad', opponentPoint);",
            "rememberPsychStagePoint('gf', gfPoint);",
            'clearPsychStageCharacterPosition();',
            "stageCharacterOffset(boyfriend, 'boyfriend')",
            "stageCharacterOffset(newChar, charState)",
        ):
            self.assertIn(call, play)
        methods = '\n'.join(extract_method(play, '\tfunction ' + name)
                            for name in ('rememberPsychStagePoint(',
                                         'clearPsychStageCharacterPosition(',
                                         'stageCharacterOffset('))
        methods += '\n' + extract_method(play, '\tpublic function syncPsychStageGroupAnchor(')
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'PsychCharacterPosition.hx').write_text(
                (ROOT / 'source/PsychCharacterPosition.hx').read_text(), newline='\n')
            (work / 'assets/data').mkdir(parents=True)
            (work / 'assets/data/psych_base_character_positions.json').write_text(
                (ROOT / 'assets/data/psych_base_character_positions.json').read_text(), newline='\n')
            (work / 'scope/characters').mkdir(parents=True)
            (work / 'scope/characters/guest.json').write_text('{"position":[25,-9]}', newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Character.hx').write_text('''
class Character {
  public var curCharacter:String;
  public var likeGf:Bool = false;
  public var playerOffsetX:Int = 0;
  public var playerOffsetY:Int = 0;
  public var enemyOffsetX:Int = 0;
  public var enemyOffsetY:Int = 0;
  public var gfOffsetX:Int = 0;
  public var gfOffsetY:Int = 0;
  public function new(id:String) curCharacter = id;
}
''', newline='\n')
            (work / 'Probe.hx').write_text('''
class StageInfo { public var x:Float = 0; public var y:Float = 0; public function new() {} }
class Stage {
  public var bf = new StageInfo(); public var dad = new StageInfo(); public var gf = new StageInfo();
  public function new() {}
  public function getInfo(role:String):StageInfo return switch (role) {
    case 'bf': bf; case 'gf': gf; default: dad;
  };
}
class Probe {
  var curStage = new Stage();
  var swapOffsets:Array<Float> = [770, 450, 400, 130, 100, 100];
  var swapOffsetsBeforePsychStage:Array<Float> = null;
  var psychStageCharacterRoot:String = null;
  var psychStageLibrary:String = null;
  var psychStageCameraBoyfriend:Array<Float> = [0, 0];
  var psychStageCameraOpponent:Array<Float> = [0, 0];
  var psychStageCameraGirlfriend:Array<Float> = [0, 0];
''' + methods + '''
  static function eq(actual:Array<Float>, x:Float, y:Float):Void
    if (actual[0] != x || actual[1] != y) throw 'position mismatch: ' + actual;
  public function new() {}
  static function main():Void {
    var state = new Probe();
    state.swapOffsetsBeforePsychStage = state.swapOffsets.copy();
    state.psychStageCharacterRoot = 'scope';
    state.rememberPsychStagePoint('bf', [749, 100]);
    state.rememberPsychStagePoint('dad', [50, 400]);
    if (state.curStage.bf.x != 749 || state.swapOffsets[1] != 100) throw 'raw stage point lost';
    state.syncPsychStageGroupAnchor('gf', 'x', 355);
    state.syncPsychStageGroupAnchor('dad', 'y', 430);
    if (state.swapOffsets[2] != 355 || state.swapOffsets[5] != 430)
      throw 'Psych group move did not survive a later character swap';
    var bf = new Character('bf');
    var guest = new Character('guest');
    var bfOffset = state.stageCharacterOffset(bf, 'boyfriend');
    var guestOffset = state.stageCharacterOffset(guest, 'boyfriend');
    eq([state.swapOffsets[0] + bfOffset[0], state.swapOffsets[1] + bfOffset[1]], 749, 450);
    eq([state.swapOffsets[0] + guestOffset[0], state.swapOffsets[1] + guestOffset[1]], 774, 91);
    state.swapOffsets[0] = 900; // A script-edited base remains authoritative.
    eq([state.swapOffsets[0] + guestOffset[0], state.swapOffsets[1] + guestOffset[1]], 925, 91);
    state.clearPsychStageCharacterPosition();
    eq([state.swapOffsets[0], state.swapOffsets[1]], 770, 450);
    eq(state.psychStageCameraBoyfriend, 0, 0);
    eq(state.psychStageCameraOpponent, 0, 0);
    eq(state.psychStageCameraGirlfriend, 0, 0);
    eq(state.stageCharacterOffset(bf, 'boyfriend'), 0, 0);
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_camera_composes_live_character_offsets_once_and_clears(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        character = (ROOT / 'source/Character.hx').read_text()
        for fragment in (
            "psychCameraContribution('boyfriend')",
            "cameraTargetForActor(dad, 'dad')",
            "cameraTargetForActor(gf, 'gf')",
            'applyPsychStageCameraOffsets(data);',
            'psychCameraRoot != null && StringTools.trim(psychCameraRoot) != \'\'',
        ):
            self.assertIn(fragment, play)
        apply = play[play.index('\tfunction applyPsychStageJson('):play.index('\n\tfunction loadPsychStageCompat(')]
        self.assertNotIn('followCamX +=', apply)
        self.assertIn('public var cameraPosition:Array<Float> = [0, 0];', character)
        self.assertIn('Song.currentPsychCharacterRoot()', character)
        self.assertIn('PsychCharacterPosition.characterCameraPosition(visualCharacterId, psychCameraRoot)', character)
        self.assertIn('positionArray = psychCharacterPositionArray(visualCharacterId, psychCameraRoot);', character)
        self.assertIn('var visualCharacterId = curCharacter;', character)
        self.assertIn('curCharacter = character;', character)
        self.assertLess(character.index('try callInterp("init", [this])'),
                        character.index('psychInitialFollowCamX = followCamX;'))

        methods = '\n'.join(
            extract_method(play, marker)
            for marker in (
                '\tfunction psychStagePoint(',
                '\tfunction clearPsychStageCharacterPosition(',
                '\tfunction psychCameraContribution(',
                '\tfunction cameraTargetForActor(',
                '\tfunction applyPsychStageCameraOffsets(',
            )
        )
        fixture = '''
using StringTools;
class Midpoint { public function put():Void {} public var x:Float; public var y:Float; public function new(x:Float,y:Float) {this.x=x;this.y=y;} }
class Character {
  public var cameraPosition:Array<Float>;
  public var followCamX:Int; public var followCamY:Int;
  public var psychInitialFollowCamX:Int; public var psychInitialFollowCamY:Int;
  public var authoredCamOffsets:Bool = false;
  public var midpoint:Midpoint;
  public var codenameLiveDefinition:Dynamic=null;
  public var sourceCameraCalls=0;
  public function getCameraPosition():Midpoint {sourceCameraCalls++;return new Midpoint(321,654);}
  public function new(value:Array<Float>, mx:Float, my:Float, fx:Int, fy:Int) {
    cameraPosition=value.copy(); midpoint=new Midpoint(mx,my);
    followCamX=fx; followCamY=fy;
    psychInitialFollowCamX=fx; psychInitialFollowCamY=fy;
  }
  public function getMidpoint():Midpoint return midpoint;
}
class Probe {
  var boyfriend:Character;
  var dad:Character;
  var gf:Character;
  var curStage:Dynamic = null;
  var psychStageCharacterRoot:String = 'psych-owner';
  var psychStageLibrary:String = null;
  var swapOffsets:Array<Float> = [1,2,3,4,5,6];
  var swapOffsetsBeforePsychStage:Array<Float> = null;
  var psychStageCameraBoyfriend:Array<Float> = [0,0];
  var psychStageCameraOpponent:Array<Float> = [0,0];
  var psychStageCameraGirlfriend:Array<Float> = [0,0];
  var psychCameraCompatibilityActive:Bool = true;
  var bfCamOffset:Array<Int> = [-100,-100];
  var dadCamOffset:Array<Int> = [0,0];
  var bfcam:Array<Float> = [0,0];
  var dadcam:Array<Float> = [0,0];
''' + methods + '''
  static function eq(actual:Array<Float>, x:Float, y:Float, label:String):Void
    if (actual == null || actual.length < 2 || actual[0] != x || actual[1] != y)
      throw label + ': ' + actual;
  public function new() {
    // The native fallback BF script initializes these legacy values. They are
    // the baseline to subtract, not part of Psych's own [-100,-100] role base.
    boyfriend = new Character([12,-5], 1000, 600, -100, -50);
    dad = new Character([-2,8], 100, 200, 150, -100);
    gf = new Character([30,4], 300, 400, 150, -100);
  }
  static function main():Void {
    var state = new Probe();
    var stageData:Dynamic = {camera_boyfriend:[5,10], camera_opponent:[3,4],
      camera_girlfriend:[5,6]};
    state.applyPsychStageCameraOffsets(stageData);
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 893, 505,
      'Psych BF base or raw camera_position sign is wrong; native fallback followCam leaked');
    eq(state.cameraTargetForActor(state.boyfriend, 'player1'), 893, 505,
      'player1 alias did not use the BF camera baseline');
    eq(state.cameraTargetForActor(state.dad, 'dad'), 251, 112,
      'Psych opponent role baseline or camera_position is wrong');
    eq(state.cameraTargetForActor(state.gf, 'gf'), 335, 410,
      'Psych GF role baseline or camera_position is wrong');

    state.applyPsychStageCameraOffsets(stageData);
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 893, 505,
      'reapplying stage JSON accumulated its camera offset');
    state.boyfriend.cameraPosition[0] = 20;
    state.boyfriend.cameraPosition[1] = 25;
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 885, 535,
      'a live character property write did not affect the camera contribution');
    state.boyfriend.followCamX += 7;
    state.boyfriend.followCamY += 2;
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 892, 537,
      'later followCam edits must act as deltas from native Character.init');

    state.boyfriend = new Character([7,-3], 1000, 600, -100, -50);
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 898, 507,
      'replacement character did not supply its own metadata without accumulating');
    state.applyPsychStageCameraOffsets({camera_opponent:[0,0]});
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 893, 497,
      'missing stage fields did not replace prior authored offsets');
    eq(state.cameraTargetForActor(state.dad, 'dad'), 248, 108,
      'missing opponent stage fields retained an old camera offset');
    eq(state.cameraTargetForActor(state.gf, 'gf'), 330, 404,
      'missing GF stage fields retained an old camera offset');

    state.clearPsychStageCharacterPosition();
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 893, 497,
      'clearing stage camera data erased the character metadata');
    // Non-Psych playback keeps native offsets, while V-Slice actors keep their
    // authored absolute follow values and do not acquire Psych role defaults.
    state.psychCameraCompatibilityActive = false;
    state.bfcam = [20,30];
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend'), 820, 480,
      'native camera target changed when no selected Psych namespace exists');
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend', 2, 3, false), 802, 453,
      'FocusCamera event unexpectedly included the per-turn camera nudge');
    state.psychCameraCompatibilityActive = true;
    state.boyfriend.authoredCamOffsets = true;
    state.boyfriend.followCamX = 4;
    state.boyfriend.followCamY = 8;
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend', 2, 3, false), 1006, 611,
      'authored V-Slice camera offsets acquired Psych defaults');
    state.boyfriend.codenameLiveDefinition={};
    eq(state.cameraTargetForActor(state.boyfriend, 'boyfriend', 2, 3, true), 323, 657,
      'source Codename camera callback ignored or fork turn nudges leaked');
    if(state.boyfriend.sourceCameraCalls!=1) throw 'source camera dispatched more than once';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'PsychCharacterPosition.hx').write_text(
                (ROOT / 'source/PsychCharacterPosition.hx').read_text(), newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Probe.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
