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
	var presentedHeight:Float = -1;
	public var motion(default, null) = new FreeplayCardMotion();
	var disabled:Bool = false;
	var hasIcon:Bool = false;
	var favorite:Bool = false;
	var selected:Bool = false;
	public function rename(label:String):Void {
		if (this.label == label) return;
		text = label; this.label = label; wasSelected = null;
	}
	public function moveTo(x:Float, y:Float, selectedHeight:Int, snap:Bool = false):Void {
		motion.target(x, y, selected ? selectedHeight : FreeplayBrowserLayout.ROW_HEIGHT, selected, snap);
	}
	public function animate(elapsed:Float):Bool {
		if (!motion.advance(elapsed)) return false;
		setPosition(motion.x, motion.y); drawPresentation(); return true;
	}
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
	public function present(selected:Bool, disabled:Bool, hasIcon:Bool, favorite:Bool = false, selectedHeight:Int = FreeplayBrowserLayout.SELECTED_HEIGHT):Void {
		this.selected = selected; this.disabled = disabled; this.hasIcon = hasIcon; this.favorite = favorite;
		if (!motion.initialized) motion.target(x, y, selected ? selectedHeight : FreeplayBrowserLayout.ROW_HEIGHT, selected, true);
		drawPresentation();
	}
	function drawPresentation():Void {
		alpha = 1;
		var height = motion.height - 4;
		if (presentedHeight != height) {
			presentedHeight = height;
			panel.scale.y = height; panel.updateHitbox(); panel.setPosition(x, y);
			stripe.scale.y = height; stripe.updateHitbox(); stripe.setPosition(x, y);
		}
		if (wasSelected == null || wasSelected != selected) {
			title.text = FreeplayBrowserLayout.label(label.toUpperCase(), Std.int((rowWidth - 370) / (selected ? 17 : 14)));
			wasSelected = selected;
		}
		title.origin.set(0, 0);
		title.scale.set(1 + motion.focus * 6 / 22, 1 + motion.focus * 6 / 22);
		title.setPosition(x + 82, y + 7 + motion.focus * 5);
		placeholder.y = y + 6 + motion.focus * 19;
		panel.color = flixel.util.FlxColor.interpolate(0xFF182235, 0xFF354963, motion.focus);
		panel.alpha = 0.78 + 0.22 * motion.focus; stripe.visible = motion.focus > 0; stripe.alpha = motion.focus;
		title.color = disabled ? 0xFF8B97A8 : (selected ? 0xFFFFF4DC : 0xFFCFD8E5);
		favoriteTag.visible = favorite; favoriteTag.alpha = disabled ? 0.5 : 1;
		placeholder.visible = !hasIcon;
	}
}
