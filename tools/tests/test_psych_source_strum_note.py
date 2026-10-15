"""Psych's `new StrumNote(x, y, leData, player)` builds a host receptor with Psych's meaning instead of crashing."""
from pathlib import Path
import re, shutil, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]


class PsychSourceStrumNoteTest(unittest.TestCase):
	def test_psych_constructor_is_bound_for_psych_sources(self):
		play_state = (ROOT / 'source/PlayState.hx').read_text()
		body = play_state[play_state.index('function bindSourceBarClass('):]
		body = body[:body.index('\n\t}\n')]
		self.assertRegex(body, r'if \(!nightmare\) interp\.bindConstructorFactory\(Strumline\.StrumNote,\s*function\(args:Array<Dynamic>\):Dynamic return PsychSourceStrumNote\.create\(this, args\)')

	def test_factory_maps_psych_arguments(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = Path(folder)
			shutil.copyfile(ROOT / 'source/PsychSourceStrumNote.hx', work / 'PsychSourceStrumNote.hx')
			files = {
				'Strumline.hx': 'class Strumline {} class StrumNote {public var x:Float;public var y:Float;public var ID:Int;public var type:String;public var skin:Array<Dynamic>;'
					'public function new(x:Float=0, y:Float=0, noteId:Int=0, type:String="normal", ?currentKey:Dynamic, ?parentLine:Dynamic) '
					'{if (noteId >= Note.NOTE_AMOUNT) throw "lane outside the UI pack";this.x=x;this.y=y;ID=noteId;this.type=type;}'
					'public function configurePsychSkin(owner:String, arrowSkin:String, disableRGB:Bool, pixel:Bool, ?postfix:String=""):Bool {skin=[owner,arrowSkin,disableRGB,pixel];return true;}}',
				'Note.hx': 'class Note {public static var NOTE_AMOUNT:Int = 4;}',
				'Judgement.hx': 'class Judgement {public static var uiJson:Dynamic;}',
				'PlayState.hx': 'class Song {public var uiType:String;public var arrowSkin:String;public var disableNoteRGB:Null<Bool>;public function new(){}}'
					'class PlayState {public static var SONG:Song;var pixelUI:Bool=false;var root:String;public function new(r:String,p:Bool){root=r;pixelUI=p;}'
					'function selectedPsychSkinRoot():Null<String> return root;}',
				'Main.hx': '''import Strumline.StrumNote;
import PlayState.Song;
class Main {
	static function ok(v:Bool, m:String):Void if (!v) throw m;
	static function main() {
		Judgement.uiJson = {normal:{}, pixel:{}};
		PlayState.SONG = new Song();PlayState.SONG.uiType = 'pixel';PlayState.SONG.arrowSkin = 'noteSkins/Custom';
		var host = new PlayState('assets/imported_mods/owner', true);
		var extra = PsychSourceStrumNote.create(host, [0, 80, 4, 1]);
		ok(extra.ID == 4 && extra.type == 'pixel' && extra.y == 80, 'a fifth Psych receptor keeps its lane and the song UI');
		ok(extra.skin[0] == 'assets/imported_mods/owner' && extra.skin[1] == 'noteSkins/Custom' && extra.skin[2] == false && extra.skin[3] == true,
			'it is skinned like the song receptors');
		var plain = PsychSourceStrumNote.create(new PlayState(null, false), [10.5, '20', 2, 0]);
		ok(plain.x == 10.5 && plain.y == 20 && plain.ID == 2 && plain.skin == null, 'no Psych owner, no Psych skin');
		PlayState.SONG.uiType = 'unknown-ui';
		ok(PsychSourceStrumNote.create(host, [0, 0, 1, 1]).type == 'normal', 'an unknown song UI falls back to normal');
		ok(PsychSourceStrumNote.create(host, [0, 0, 1, 'pixel']).type == 'pixel', 'a host-style UI name is still honoured');
		ok(PsychSourceStrumNote.create(host, []).ID == 0, 'no arguments is lane 0');
		Sys.println('ok');
	}
}'''
			}
			for name, content in files.items():
				(work / name).write_text(content, encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], cwd=work,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
