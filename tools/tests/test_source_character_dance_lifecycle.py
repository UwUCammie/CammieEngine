"""Execute source cadence writes, GF beat gating, and alt-idle lifecycle."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class SourceCharacterDanceLifecycleTest(unittest.TestCase):
    def test_dialect_speed_gate_and_exact_alt_idle_dispatch(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(source, marker) for marker in (
            'function set_gfSpeed(', 'function sourceAnimationEventActor(', 'function applySourceAltIdleAnimation(',
            'function girlfriendDanceDue(', 'function characterDanceDue(',
        ))
        self.assertIn('public var gfSpeed(default, set):Int = 1;', source)
        self.assertIn('if (!applySourceAltIdleAnimation(e.v1, e.v2))', source)
        self.assertIn('&& girlfriendDanceDue(curBeat)', source)
        fixture = '''using StringTools;
class Character {
 public var danceEvery:Int = 2;
 public var danceEveryNumBeats(get,set):Int;
 function get_danceEveryNumBeats():Int return danceEvery;
 function set_danceEveryNumBeats(value:Int):Int return danceEvery = value;
 public var animation:Dynamic = {curAnim:{name:"idle"}};
 public var stunned=false;
 public var codenameLiveDefinition:Dynamic = null;
 public var idleSuffix:String = '';
 public var recalculations:Int = 0;
 public function new() {}
 public function recalculateDanceIdle():Void recalculations++;
}
class NightmareVisionCharacterGroup { public function new() {} }
class Main {
 public var gfSpeed(default,set):Int = 1;
 var nightmareVisionScripts:Dynamic = null;
 var nightmareVisionLegacyFieldCameras=false;
 var gfGroup:NightmareVisionCharacterGroup;
 var sourceScoreOwner:Bool = false;
 var sourceScoreNightmare:Bool = false;
 var gf:Character = new Character();
 var boyfriend:Character = new Character();
 var dad:Character = new Character();
 public function new() {}
 @@METHODS@@
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var native = new Main();
  Reflect.setProperty(native, 'gfSpeed', 2);
  check(native.gf.danceEveryNumBeats == 2 && native.girlfriendDanceDue(2), 'native cadence changed');
  check(!native.applySourceAltIdleAnimation('1', '') && native.boyfriend.recalculations == 0,
   'native event entered source target/suffix handling');
  var psych = new Main();
  psych.sourceScoreOwner = true;
  Reflect.setProperty(psych, 'gfSpeed', 2);
  check(psych.gf.danceEveryNumBeats == 2 && !psych.girlfriendDanceDue(2)
   && psych.girlfriendDanceDue(4), 'Psych GF cadence must use the product');
  psych.gfSpeed = 0;
  check(!psych.girlfriendDanceDue(0), 'zero Psych cadence must not modulo zero');
  psych.gfSpeed = 2;
  psych.gf = null;
  check(!psych.girlfriendDanceDue(4) && psych.applySourceAltIdleAnimation('gf', '-alt'), 'null GF handling');
  psych.gf = new Character();
  check(psych.applySourceAltIdleAnimation(' GF ', '  -alt  ') && psych.gf.idleSuffix == '  -alt  '
   && psych.gf.recalculations == 1, 'Psych must trim target but preserve exact suffix');
  psych.applySourceAltIdleAnimation('0', '');
  check(psych.dad.idleSuffix == '' && psych.dad.recalculations == 1
   && psych.gf.recalculations == 1, 'Psych zero selects Dad; empty suffix resets only him');
  psych.applySourceAltIdleAnimation('1', '-pair');
  check(psych.boyfriend.idleSuffix == '-pair' && psych.boyfriend.recalculations == 1,
   'Psych numeric one must select BF');
  psych.applySourceAltIdleAnimation('2', '-support');
  check(psych.gf.idleSuffix == '-support', 'Psych numeric two must select GF');
  var nv = new Main();
  nv.sourceScoreOwner = true;
  nv.sourceScoreNightmare = true;
  nv.nightmareVisionScripts = {};
  nv.gfGroup = new NightmareVisionCharacterGroup();
  Reflect.setProperty(nv, 'gfSpeed', 2);
  check(nv.gf.danceEveryNumBeats == 4 && !nv.girlfriendDanceDue(2)
   && nv.girlfriendDanceDue(4), 'NV live write must multiply actor cadence');
  Reflect.setProperty(nv, 'gfSpeed', 2);
  check(nv.gf.danceEveryNumBeats == 8, 'NV repeated writes must multiply again');
  nv.gf.danceEveryNumBeats = 3;
  check(nv.girlfriendDanceDue(3), 'NV live interval must not also retain the independent gfSpeed gate');
  nv.gf.danceEveryNumBeats = 8;
  nv.gfGroup = null;
  nv.gfSpeed = 3;
  check(nv.gf.danceEveryNumBeats == 8 && nv.gfSpeed == 3, 'NV absent group must store without multiplying');
  check(nv.gfGroup == null, 'NV setter created an unavailable GF group');
  nv.gfGroup = new NightmareVisionCharacterGroup();
  nv.gf = null;
  nv.gfSpeed = 4;
  check(nv.gfSpeed == 4, 'NV absent actor must still store');
  nv.gf = new Character();
  nv.applySourceAltIdleAnimation(' GF ', '-raw');
  check(nv.dad.idleSuffix == '-raw' && nv.gf.recalculations == 0, 'NV must not trim target names');
  nv.applySourceAltIdleAnimation('BF', '');
  check(nv.boyfriend.idleSuffix == '' && nv.boyfriend.recalculations == 1,
   'NV exact suffix and case folding');
  check(psych.gf.danceEveryNumBeats == 2 && native.gf.danceEveryNumBeats == 2,
   'NV writes leaked to other dialect actors');
  nv.nightmareVisionScripts = null;
  nv.gfSpeed = 5;
  check(nv.gf.danceEveryNumBeats == 2, 'inactive NV runtime retained setter effects');
 }
}'''.replace('@@METHODS@@', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
