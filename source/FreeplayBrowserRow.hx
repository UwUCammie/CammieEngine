package;

import flixel.FlxSprite;
import flixel.text.FlxText;

/** Compact host rows with one expanded selection; live row count remains bounded. */
class FreeplayBrowserRow extends Alphabet {
	var panel:FlxSprite;
	var divider:FlxSprite;
	var stripe:FlxSprite;
	var title:FlxText;
	var placeholder:FlxText;
	var favoriteTag:FlxText;
	var label:String;
	var rowWidth:Int;
	var wasSelected:Null<Bool>;
	public function new(label:String, rowWidth:Int) {
		super(24, 0, ''); text = label; this.label = label; this.rowWidth = rowWidth;
		panel = new FlxSprite().makeGraphic(rowWidth, 1, 0xFFFFFFFF);
		stripe = new FlxSprite().makeGraphic(5, 1, 0xFFFF66B7);
		placeholder = new FlxText(14, 8, 48, '?', 22);
		placeholder.setFormat('assets/fonts/vcr.ttf', 22, 0xFF8997AD, CENTER);
		title = new FlxText(82, 5, rowWidth - 370, '', 22);
		title.setFormat('assets/fonts/vcr.ttf', 22, 0xFFFFFFFF, LEFT); title.wordWrap = false;
		favoriteTag = new FlxText(rowWidth - 50, 10, 50, 'FAV', 16);
		favoriteTag.setFormat('assets/fonts/vcr.ttf', 16, 0xFFFFD166, CENTER);
		divider = new FlxSprite().makeGraphic(rowWidth, 1, 0xFF80E3D0); divider.visible = false;
		add(panel); add(divider); add(stripe); add(placeholder); add(title); add(favoriteTag);
	}
	public function groupBoundary(visible:Bool):Void divider.visible = visible;
	public function present(selected:Bool, disabled:Bool, hasIcon:Bool, favorite:Bool = false):Void {
		alpha = 1;
		if (wasSelected == null || wasSelected != selected) {
			var height = (selected ? FreeplayBrowserLayout.SELECTED_HEIGHT : FreeplayBrowserLayout.ROW_HEIGHT) - 4;
			panel.scale.y = height; panel.updateHitbox(); panel.setPosition(x, y);
			stripe.scale.y = height; stripe.updateHitbox(); stripe.setPosition(x, y);
			title.size = selected ? 28 : 22;
			title.text = FreeplayBrowserLayout.label(label.toUpperCase(), Std.int((rowWidth - 370) / (selected ? 17 : 14)));
			title.setPosition(x + 82, y + (selected ? 12 : 7));
			placeholder.y = y + (selected ? 25 : 6);
			wasSelected = selected;
		}
		panel.color = selected ? 0xFF354963 : 0xFF182235;
		panel.alpha = selected ? 1 : 0.78; stripe.visible = selected;
		title.color = disabled ? 0xFF8B97A8 : (selected ? 0xFFFFF4DC : 0xFFCFD8E5);
		favoriteTag.visible = favorite; favoriteTag.alpha = disabled ? 0.5 : 1;
		placeholder.visible = !hasIcon;
	}
}
