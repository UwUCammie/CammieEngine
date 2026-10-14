"""Freeplay card stars share one drawn graphic instead of rasterising one each.

Every card star is the same 32x32 vector star, tinted only at draw time. The
production whitenCard is run against stand-ins for the bitmap cache and the
vector drawing classes: many stars must draw once and all load that graphic,
and the drawing is made again only after the cache lost it.
"""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(text, start):
    pos = text.index(start)
    brace = text.index('{', pos)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[pos:i + 1]
    raise AssertionError('unterminated ' + start)


class RankStarSharedCardGraphicTest(unittest.TestCase):
    def test_card_stars_draw_once_and_share(self):
        source = (ROOT / 'source/RankStar.hx').read_text(encoding='utf-8')
        whiten = method(source, '\tfunction whitenCard():Void {')
        key_line = [l for l in source.splitlines() if 'CARD_GRAPHIC_KEY:String' in l][0]
        body = (whiten.replace('flixel.FlxG.bitmap', 'Cache')
                .replace('openfl.display.Shape', 'Shape').replace('openfl.geom.Matrix', 'Matrix')
                .replace('openfl.display.GradientType.LINEAR', '0'))
        fixture = '''
class Graphic { public var bitmap:BitmapData; public function new(b) bitmap = b; }
class BitmapData {
	public static var created = 0;
	public var drawn = 0;
	public function new(w:Int, h:Int, t:Bool, c:Int) created++;
	public function draw(s:Shape) drawn++;
}
class Graphics {
	public function new() {}
	public function beginGradientFill(a:Dynamic, b:Dynamic, c:Dynamic, d:Dynamic, e:Dynamic) {}
	public function lineStyle(a:Dynamic, b:Dynamic, c:Dynamic, d:Dynamic, e:Dynamic, f:Dynamic, g:Dynamic) {}
	public function moveTo(x:Float, y:Float) {}
	public function lineTo(x:Float, y:Float) {}
	public function endFill() {}
}
class Shape { public var graphics = new Graphics(); public function new() {} }
class Matrix { public function new() {} public function createGradientBox(a:Dynamic, b:Dynamic, c:Dynamic) {} }
class Cache {
	public static var map:Map<String, Graphic> = [];
	public static function get(key:String):Graphic return map.get(key);
	public static function add(b:BitmapData, unique:Bool, key:String):Graphic {
		if (!map.exists(key)) map.set(key, new Graphic(b));
		return map.get(key);
	}
}
class Star {
	static var NORMAL = 0; static var ROUND = 0;
	''' + key_line.strip() + '''
	public var graphic:Graphic;
	public function new() {}
	function loadGraphic(g:Dynamic) graphic = g;
	function setGraphicSize(w:Int, h:Int) {}
	function updateHitbox() {}
	public ''' + body.strip() + '''
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var stars = [for (i in 0...40) new Star()];
		for (star in stars) star.whitenCard();
		check(BitmapData.created == 1, 'forty card stars must rasterise the star once, made ' + BitmapData.created);
		for (star in stars) check(star.graphic == stars[0].graphic && star.graphic != null, 'every card star shares the graphic');
		check(stars[0].graphic.bitmap.drawn == 1, 'the shared bitmap holds the drawing');
		// A state switch or the last star going away drops the cached graphic.
		Cache.map.clear();
		var later = new Star(); later.whitenCard();
		check(BitmapData.created == 2 && later.graphic != null && later.graphic.bitmap.drawn == 1, 'a lost graphic is drawn again');
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + fixture)
        self.assertIn('ok', result.stdout)

    def test_card_legend_text_is_built_on_first_lift(self):
        source = (ROOT / 'source/RankStar.hx').read_text(encoding='utf-8')
        configure = method(source, '\tpublic function configureCard(')
        create = method(source, '\tfunction createLegend():flixel.text.FlxText {')
        draw = method(source, '\toverride public function draw():Void {')
        legend_block = draw[draw.index('\t\tif (legendLift > 0.01) {'):]
        legend_block = method(legend_block, '\t\tif (legendLift > 0.01) {')
        fixture = '''
class Text {
	public static var made = 0;
	public var text = '';
	public var alpha = 1.0; public var color = 0; public var cameras:Dynamic;
	public var scrollFactor = new Pair();
	public function new(x:Float, y:Float, w:Float, t:String, s:Int) made++;
	public function setFormat(a:Dynamic, b:Dynamic, c:Dynamic, d:Dynamic) {}
	public function setBorderStyle(a:Dynamic, b:Dynamic, c:Dynamic) {}
	public function setPosition(x:Float, y:Float) {}
	public function draw() {}
}
class Pair { public function new() {} public function set() {} }
class DifficultyManager { public static function getDiffName(d:Int) return 'hard'; }
class Star {
	static var CENTER = 0; static var OUTLINE = 0;
	public var inCard = false; public var diff = 2; public var focused = false;
	public var width = 26.0; public var height = 26.0; public var cameras:Dynamic;
	public var legendLift = 0.0;
	var legend:Text; var difficultyLabel = ''; var ratingLabel = '?';
	public function new() {}
	function whitenCard() {}
	function updateDensity(v:Dynamic) {}
	static function legendOffset(a:Float, b:Float) return 0.0;
	static function legendOpacity(a:Float) return 1.0;
	public function hasLegend() return legend != null;
	''' + configure.strip().replace('ChartDifficultyAnalysis.ChartDensity', 'Dynamic') + '''
	''' + create.strip().replace('flixel.text.FlxText', 'Text') + '''
	public function drawLegend(savedX:Float, savedY:Float, savedAlpha:Float) {
	''' + legend_block.replace('flixel.text.FlxText', 'Text') + '''
	}
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var stars = [for (i in 0...12) new Star()];
		for (star in stars) { star.configureCard(null); star.drawLegend(0, 0, 1); }
		check(Text.made == 0, 'configuring and drawing unlifted card stars builds no legend text');
		stars[0].legendLift = 1;
		stars[0].drawLegend(0, 0, 1); stars[0].drawLegend(0, 0, 1);
		check(Text.made == 1 && stars[0].hasLegend(), 'a lifted star builds its legend once');
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + fixture)
        self.assertIn('ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
