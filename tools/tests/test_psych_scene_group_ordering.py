"""Execute shared nested-group ordering across cached swaps and scene covers."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PsychSceneGroupOrderingTest(unittest.TestCase):
    def test_cached_children_stay_inside_stage_and_covers_keep_outer_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder)
            (path / 'Main.hx').write_text(r'''
class Main {
 static function eq(actual:Array<String>, expected:String):Void {
  if (actual.join(',') != expected) throw actual + ' != ' + expected;
 }
 static function main():Void {
  var scene = ['back', 'front', 'gf', 'dad', 'bf', 'hud', 'cover', 'text'];
  var dad = ['dad']; var gf = ['gf']; var bf = ['bf'];
  // Preloading happens after the song has added its full-screen cover.
  PsychSceneGroupOrdering.append(scene, dad, 'dad-pov'); dad.push('dad-pov');
  PsychSceneGroupOrdering.append(scene, dad, 'dad-rhyme'); dad.push('dad-rhyme');
  PsychSceneGroupOrdering.append(scene, gf, 'gf-cold'); gf.push('gf-cold');
  PsychSceneGroupOrdering.append(scene, bf, 'bf-pov'); bf.push('bf-pov');
  eq(scene, 'back,front,gf,gf-cold,dad,dad-pov,dad-rhyme,bf,bf-pov,hud,cover,text');
  var groups:Array<PsychSceneGroupOrdering.PsychSceneGroup<String>> = [
   {members:['back'],z:-15}, {members:['front'],z:50},
   {members:gf,z:0}, {members:dad,z:0}, {members:bf,z:2}
  ];
  PsychSceneGroupOrdering.sort(scene, groups);
  eq(scene, 'back,gf,gf-cold,dad,dad-pov,dad-rhyme,bf,bf-pov,front,hud,cover,text');
  // Cache parent changes do not move any children. Map enumeration order is
  // irrelevant; refresh preserves existing child draw order within a bank.
  groups[3].members.reverse();
  PsychSceneGroupOrdering.sort(scene, groups);
  eq(scene, 'back,gf,gf-cold,dad,dad-pov,dad-rhyme,bf,bf-pov,front,hud,cover,text');
  // A late stage prop also enters the stage root before top-level overlays.
  var stage = scene.slice(0,9);
  PsychSceneGroupOrdering.append(scene, stage, 'blackout');
  groups.push({members:['blackout'],z:999});
  PsychSceneGroupOrdering.sort(scene, groups);
  eq(scene, 'back,gf,gf-cold,dad,dad-pov,dad-rhyme,bf,bf-pov,front,blackout,hud,cover,text');
  // Authored group depth moves the whole bank, never its members separately.
  groups[3].z = -10;
  PsychSceneGroupOrdering.sort(scene, groups);
  eq(scene, 'back,dad,dad-pov,dad-rhyme,gf,gf-cold,bf,bf-pov,front,blackout,hud,cover,text');
  var empty:Array<String> = ['outside'];
  PsychSceneGroupOrdering.sort(empty, [{members:['absent'],z:4}]); eq(empty,'outside');
  PsychSceneGroupOrdering.append(empty, ['absent'], 'new'); eq(empty,'outside,new');
  PsychSceneGroupOrdering.append(empty, ['new'], 'new'); eq(empty,'outside,new');
  var inserts = 0; var nativeLength = empty.length;
  PsychSceneGroupOrdering.append(empty, ['new'], 'late', function(index, member) {
   inserts++; empty.insert(index,member); nativeLength++;
  });
  eq(empty,'outside,new,late');
  if (inserts != 1 || nativeLength != empty.length) throw 'host insertion callback was bypassed';
  // Recover an earlier flattened list without dropping holes or unrelated data.
  var scattered = ['outside-before', 'dad', 'hud', null, 'cover', 'dad-pov'];
  PsychSceneGroupOrdering.sort(scattered, [{members:dad,z:0}]);
  eq(scattered, 'outside-before,dad,dad-pov,hud,null,cover');
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(path), '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
