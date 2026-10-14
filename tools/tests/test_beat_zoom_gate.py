"""The native beat bump honours a Psych owner's camZooms preference."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
class Options { public var zoomCamera:Bool = true; public function new() {} }
class OptionsHandler { public static var options = new Options(); }
class State {
 public var sourceScoreOwner = false; public var ownerZooms = true;
 public function new() {}
 function sourceLivePreference(name:String, fallback:Bool):Bool { if (name != 'camZooms') throw name; return ownerZooms; }
 @@METHODS@@
 public function allowed():Bool return nativeBeatZoomAllowed();
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var s = new State();
  check(s.allowed(), 'native song bumps');
  OptionsHandler.options.zoomCamera = false; s.ownerZooms = false;
  check(s.allowed(), 'native song keeps its old gate whatever the options say');
  s.sourceScoreOwner = true;
  OptionsHandler.options.zoomCamera = true; s.ownerZooms = true;
  check(s.allowed(), 'owner with zooms on bumps');
  s.ownerZooms = false; check(!s.allowed(), 'owner camZooms off stops the bump');
  s.ownerZooms = true; OptionsHandler.options.zoomCamera = false; check(!s.allowed(), 'host option still gates owners');
 }
}
'''


class BeatZoomGateTest(unittest.TestCase):
	def test_owner_preference_gates_the_native_bump(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		methods = method(play, 'function nativeBeatZoomAllowed():Bool') + '\n' + method(play, 'function sourceCameraZoomsEnabled():Bool')
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			Path(folder, 'Main.hx').write_text(FIXTURE.replace('@@METHODS@@', methods), encoding='utf-8', newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
					cwd=ROOT, capture_output=True, text=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
	unittest.main()
