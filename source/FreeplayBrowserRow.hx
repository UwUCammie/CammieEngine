package;

import flixel.FlxSprite;
import flixel.text.FlxText;

/** A bounded host row, retaining Alphabet identity for shared capsule consumers. */
class FreeplayBrowserRow extends Alphabet {
	var panel:FlxSprite;
	var divider:FlxSprite;
	var stripe:FlxSprite;
	var title:FlxText;
	var placeholder:FlxText;
	public function new(label:String, rowWidth:Int) {
		super(24, 0, '');
		text = label;
		panel = new FlxSprite().makeGraphic(rowWidth, 60, 0xFFFFFFFF);
		stripe = new FlxSprite().makeGraphic(4, 60, 0xFF80E3D0);
		placeholder = new FlxText(20, 14, 40, '?', 28);
		placeholder.setFormat('assets/fonts/vcr.ttf', 28, 0xFF8997AD, CENTER);
		title = new FlxText(82, 5, rowWidth - 100,
			FreeplayBrowserLayout.label(label.toUpperCase(), Std.int((rowWidth - 100) / 17)), 26);
		title.setFormat('assets/fonts/vcr.ttf', 26, 0xFFFFFFFF, LEFT);
		title.wordWrap = false;
		divider = new FlxSprite().makeGraphic(rowWidth, 2, 0xFF80E3D0); divider.visible = false;
		add(panel); add(divider); add(stripe); add(placeholder); add(title);
	}
	public function groupBoundary(visible:Bool):Void divider.visible = visible;
	public function present(selected:Bool, disabled:Bool, hasIcon:Bool):Void {
		alpha = 1;
		panel.color = selected ? 0xFF304760 : 0xFF192231;
		panel.alpha = selected ? 1 : 0.85;
		stripe.visible = selected;
		title.color = disabled ? 0xFF8B97A8 : (selected ? 0xFFFFFFFF : 0xFFCFD8E5);
		placeholder.visible = !hasIcon;
	}
}
