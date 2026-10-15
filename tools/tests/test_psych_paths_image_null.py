"""Psych's Paths.image returns null for an image it cannot load instead of stopping the script."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_skin_runtime import method
ROOT = Path(__file__).resolve().parents[2]


class PsychPathsImageNullTest(unittest.TestCase):
	def test_missing_empty_and_unsafe_keys_return_null(self):
		image = method((ROOT / 'source/PsychOwnerPaths.hx').read_text(), 'image').replace('static function image', 'public static function image', 1)
		files = {
			'flixel/graphics/FlxGraphic.hx': 'package flixel.graphics;class FlxGraphic {public var path:String;public function new(p:String)path=p;}',
			'FNFAssets.hx': 'class FNFAssets {public static var loads:Array<String>=[];public static var available:Map<String,Bool>=[];public static function exists(p:String)return available.exists(p);'
				'public static function getFlxGraphic(p:String):flixel.graphics.FlxGraphic {loads.push(p);return new flixel.graphics.FlxGraphic(p);}}',
			'Paths.hx': 'class Paths {public static function file(p:String,t:Dynamic,l:String)return "native/"+l+"/"+p;}',
			'SourceBarAssets.hx': 'class SourceBarAssets {public static function coreImage(e:String,k:String):String return null;}',
			'PsychOwnerAssetPath.hx': 'class PsychOwnerAssetPath {public static function cleanId(k:String):String return k==null||k==""||k.indexOf("..")>=0?null:k;}',
			'PsychOwnerPaths.hx': 'import flixel.graphics.FlxGraphic;class PsychOwnerPaths {static var IMAGE=0;public static var owned:Map<String,String>=[];'
				'static function ownerAsset(o:String,k:String,l:String,c:String):String return owned.get(k);'
				'static function graphic(p:String):FlxGraphic return p==null||p==""?null:FNFAssets.getFlxGraphic(p);' + image + '}',
			'Main.hx': '''class Main {
	static function ok(v:Bool, m:String):Void if (!v) throw m;
	static function main() {
		var traces:Array<String> = [];
		haxe.Log.trace = function(v:Dynamic, ?i:haxe.PosInfos) traces.push(Std.string(v));
		PsychOwnerPaths.owned.set("images/bg.png", "owner/images/bg.png");
		ok(PsychOwnerPaths.image("owner", "bg", null, null).path == "owner/images/bg.png", "owned image still loads");
		FNFAssets.available.set("native/shared/images/stageback.png", true);
		ok(PsychOwnerPaths.image("owner", "stageback", null, null).path == "native/shared/images/stageback.png", "shared fallback still loads");
		for (key in ["", null, "../other/images/leak", "nothing/here"])
			ok(PsychOwnerPaths.image("owner", key, null, null) == null, "Paths.image must return null for " + key);
		ok(FNFAssets.loads.length == 2, "nothing is loaded for a refused or missing key");
		ok(traces.length == 4 && traces[3].indexOf("nothing/here") >= 0, "each null result is reported: " + traces.join("|"));
		Sys.println("ok");
	}
}'''
		}
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
			for name, content in files.items():
				path = Path(tmp) / name
				path.parent.mkdir(parents=True, exist_ok=True)
				path.write_text(content, encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '-main', 'Main', '--interp'], cwd=ROOT,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
