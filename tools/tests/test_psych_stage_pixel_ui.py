"""A Psych stage marked isPixelStage (or with a pixel stageUI) switches the song to the pixel UI before it is built."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_skin_runtime import method
ROOT = Path(__file__).resolve().parents[2]


class PsychStagePixelUITest(unittest.TestCase):
	def test_stage_file_sets_pixel_ui_before_ui_pack(self):
		play_state = (ROOT / 'source/PlayState.hx').read_text()
		apply = method(play_state, 'applyPsychStagePixelUI')
		is_pixel = method(play_state, 'stageUIIsPixel')
		# The UI pack is picked right after the stage choice lands on the chart.
		self.assertRegex(play_state, r'applyPsychStagePixelUI\(\);\s*\n\s*uiSmelly = Reflect\.field\(Judgement\.uiJson, SONG\.uiType\);')
		metadata = (ROOT / 'source/SourceStageMetadata.hx').read_text()
		resolve = method(metadata, 'resolveStageUI')
		files = {
			'Judgement.hx': 'class Judgement {public static var uiJson:Dynamic;}',
			'FNFAssets.hx': 'class FNFAssets {public static var files:Map<String,String>=[];public static function exists(p:String)return files.exists(p);public static function getText(p:String)return files.get(p);}',
			'CoolUtil.hx': 'class CoolUtil {public static function parseJson(t:String):Dynamic return haxe.Json.parse(t);}',
			'SourceStageMetadata.hx': 'using StringTools;class SourceStageMetadata {public var stageUI:String;public function new(){}'
				'public static function parse(data:Dynamic):SourceStageMetadata {var r=new SourceStageMetadata();r.stageUI=resolveStageUI(Reflect.field(data,"stageUI"),Reflect.field(data,"isPixelStage"));return r;}'
				+ resolve + '}',
			'Main.hx': '''class Song {public var stage:String;public var uiType:String;public function new(s:String,u:String){stage=s;uiType=u;}}
class Host {
	public var SONG:Song;public var root:String="owner";
	public function new(s:Song) SONG=s;
	function selectedPsychSkinRoot():Null<String> return root;
	function psychStageMetadataPath(r:String, stage:String):String return r + "/stages/" + stage + ".json";
	__IS_PIXEL__
	__APPLY__
	public function run():String {applyPsychStagePixelUI();return SONG.uiType;}
}
class Main {
	static function ok(v:Bool, m:String):Void if (!v) throw m;
	static function main() {
		haxe.Log.trace = function(v:Dynamic, ?i:haxe.PosInfos) {};
		Judgement.uiJson = {normal:{}, pixel:{}};
		FNFAssets.files.set("owner/stages/blocks.json", '{"isPixelStage": true}');
		FNFAssets.files.set("owner/stages/named.json", '{"stageUI": "retro-pixel"}');
		FNFAssets.files.set("owner/stages/plain.json", '{"isPixelStage": false}');
		FNFAssets.files.set("owner/stages/override.json", '{"stageUI": "normal", "isPixelStage": true}');
		FNFAssets.files.set("owner/stages/broken.json", '{not json');
		ok(new Host(new Song("blocks", "normal")).run() == "pixel", "isPixelStage stage uses the pixel UI");
		ok(new Host(new Song("named", null)).run() == "pixel", "a pixel stageUI uses the pixel UI");
		ok(new Host(new Song("plain", "normal")).run() == "normal", "a normal stage keeps the normal UI");
		ok(new Host(new Song("override", "normal")).run() == "normal", "a non-empty stageUI wins over isPixelStage, as in Psych");
		ok(new Host(new Song("broken", "normal")).run() == "normal", "an unreadable stage file changes nothing");
		ok(new Host(new Song("absent", "normal")).run() == "normal", "a missing stage file changes nothing");
		ok(new Host(new Song("blocks", "custom")).run() == "custom", "a chart that names its own UI keeps it");
		var other = new Host(new Song("blocks", "normal"));other.root = null;
		ok(other.run() == "normal", "songs that are not Psych imports are untouched");
		Judgement.uiJson = {normal:{}};
		ok(new Host(new Song("blocks", "normal")).run() == "normal", "no pixel pack, no switch");
		Sys.println("ok");
	}
}'''.replace('__IS_PIXEL__', is_pixel).replace('__APPLY__', apply)
		}
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
			for name, content in files.items():
				(Path(tmp) / name).write_text(content, encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '-main', 'Main', '--interp'], cwd=ROOT,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
