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
	var chartTag:FlxText;
	var chartCaption:String = '';
	var chartIcon:HealthIcon;
	var chartStar:RankStar;
	public function setChartArtwork(song:String, character:String, difficulty:Int, density:Null<ChartDifficultyAnalysis.ChartDensity>, ready:Bool):Void {
		if (ready && chartIcon == null) {
			chartIcon = new HealthIcon(character, false, false, false, song);
			chartIcon.setGraphicSize(Std.int(34 * chartIcon.width / Math.max(chartIcon.width, chartIcon.height))); chartIcon.updateHitbox(); add(chartIcon);
		}
		if (difficulty >= 0 && (chartStar == null || chartStar.diff != difficulty)) {
			if (chartStar != null) { remove(chartStar, true); chartStar.destroy(); }
			chartStar = new RankStar(song, difficulty); chartStar.configureCard(density); add(chartStar);
		} else if (chartStar != null) chartStar.updateDensity(density);
	}

	public function setChartCaption(value:String):Void { chartCaption = value; drawPresentation(); }
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
		if (snap) { setPosition(motion.x, motion.y); drawPresentation(); }
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
		chartTag = new FlxText(rowWidth - 244, 8, 140, '', 16);
		chartTag.setFormat('assets/fonts/vcr.ttf', 16, 0xFFCFD8E5, RIGHT); chartTag.wordWrap = false;
		divider = new FlxSprite().makeGraphic(rowWidth, 1, 0xFF80E3D0); divider.visible = false;
		add(panel); add(divider); add(stripe); add(placeholder); add(title); add(chartTag); add(favoriteTag);
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
		var titleColor = disabled ? 0xFF8B97A8 : (selected ? 0xFFFFF4DC : 0xFFCFD8E5);
		var titleChanged = wasSelected == null || wasSelected != selected;
		var titleAppearanceChanged = titleChanged || title.color != titleColor;
		title.color = titleColor;
		if (titleChanged) {
			title.text = FreeplayBrowserLayout.label(label.toUpperCase(), Std.int((rowWidth - 370) / (selected ? 17 : 14)));
			wasSelected = selected;
		}
		title.scale.set(1 + motion.focus * 6 / 22, 1 + motion.focus * 6 / 22);
		// Generate changed text before drawing at the scaled left anchor.
		if (titleAppearanceChanged) title.updateHitbox();
		title.offset.set(0, 0); title.origin.set(0, 0);
		title.setPosition(x + 82, y + 7 + motion.focus * 5);
		placeholder.y = y + 6 + motion.focus * 19;
		panel.color = flixel.util.FlxColor.interpolate(0xFF182235, 0xFF354963, motion.focus);
		panel.alpha = 0.78 + 0.22 * motion.focus; stripe.visible = motion.focus > 0; stripe.alpha = motion.focus;
		favoriteTag.visible = favorite; favoriteTag.alpha = disabled ? 0.5 : 1;
		if (chartIcon != null) { chartIcon.setPosition(x + 24, y + 3); chartIcon.visible = !selected; chartIcon.color = disabled ? 0xFF858585 : 0xFFFFFFFF; }
		if (chartStar != null) { chartStar.cardX = x + rowWidth - 94; chartStar.cardY = y - 2; chartStar.setPosition(chartStar.cardX, y + 3); chartStar.visible = !selected; chartStar.alpha = disabled ? 0.45 : 1; }
		chartTag.text = FreeplayBrowserLayout.label(chartCaption.toUpperCase(), 16);
		chartTag.setPosition(x + rowWidth - 244, y + 8); chartTag.visible = !selected && chartCaption != '';
		placeholder.visible = chartIcon == null && !hasIcon && chartCaption == '';
	}
}
