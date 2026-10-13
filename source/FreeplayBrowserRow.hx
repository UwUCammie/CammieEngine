package;

import flixel.FlxSprite;
import flixel.text.FlxText;

/** Compact host rows with one expanded selection; live row count remains bounded. */
class FreeplayBrowserRow extends Alphabet {
	var panel:FlxSprite;
	var trails:Array<FlxSprite> = [];
	var trailClock:Float = 0;
	var trailColor:Int = 0xFFFFDDDD;
	public function setTrailColor(color:Int):Void {
		trailColor = flixel.util.FlxColor.interpolate(color, 0xFFFFFFFF, 0.58);
	}
	var trailShown:Bool = false;
	/** Built on first use: only a selected or hovered card pays for its stars. */
	function buildTrail():Void {
		var key = 'freeplay-trail-star'; var graphic = flixel.FlxG.bitmap.get(key);
		if (graphic == null) {
			var bitmap = new openfl.display.BitmapData(18, 18, true, 0); var shape = new openfl.display.Shape();
			shape.graphics.beginFill(0xFFFFFF);
			for (i in 0...11) {
				var angle = -Math.PI / 2 + i * Math.PI / 5; var radius = i % 2 == 0 ? 8.0 : 3.5;
				var px = 9 + Math.cos(angle) * radius; var py = 9 + Math.sin(angle) * radius;
				if (i == 0) shape.graphics.moveTo(px, py); else shape.graphics.lineTo(px, py);
			}
			shape.graphics.endFill(); bitmap.draw(shape); graphic = flixel.FlxG.bitmap.add(bitmap, false, key);
		}
		// Above the panel, below the text. Inserting at one index stacks later
		// sprites lower, which leaves each star above its own tail copies.
		var layer = members.indexOf(panel) + 1;
		for (i in 0...FreeplayStarTrail.STARS * (FreeplayStarTrail.GHOSTS + 1)) {
			var star = new FlxSprite(); star.loadGraphic(graphic); star.antialiasing = true; star.visible = false;
			insert(layer, star); trails.push(star);
		}
	}
	function animateTrail(elapsed:Float):Void {
		var activeTrail = !disabled && (selected || flixel.FlxG.mouse.overlaps(panel));
		if (!activeTrail) {
			if (trailShown) { for (star in trails) star.visible = false; trailShown = false; }
			return;
		}
		if (trails.length == 0) buildTrail();
		trailShown = true; trailClock += elapsed;
		var copies = FreeplayStarTrail.GHOSTS + 1;
		// Stars stay wholly inside the card, so a rotating sprite needs no clip.
		var travel = rowWidth - 36; var lanes = Math.max(0, motion.height - 4 - 26);
		for (i in 0...FreeplayStarTrail.STARS) {
			var head = FreeplayStarTrail.progress(trailClock, i);
			var size = FreeplayStarTrail.size(i); var turn = FreeplayStarTrail.spin(i);
			var laneY = y + 4 + FreeplayStarTrail.lane(i) * lanes;
			for (copy in 0...copies) {
				var star = trails[i * copies + copy];
				var progress = copy == 0 ? head : head - FreeplayStarTrail.ghostLag(copy - 1);
				var opacity = copy == 0 ? FreeplayStarTrail.opacity(head) : FreeplayStarTrail.ghostOpacity(head, copy - 1);
				star.visible = opacity > 0.01;
				if (!star.visible) continue;
				star.alpha = opacity; star.color = trailColor;
				star.scale.set(size * (1 - copy * 0.15), size * (1 - copy * 0.15));
				star.angle = turn * (trailClock - copy * 0.05);
				star.setPosition(x + rowWidth - 27 - progress * travel, laneY);
			}
		}
	}
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
	public var chartStars(default, null):Array<RankStar> = [];
	public var presentationSong:Int = -1;
	public var presentationKey:String = '';
	var artworkDifficulties:String = '';
	public function setChartArtwork(song:String, character:String, difficulty:Int, density:Null<ChartDifficultyAnalysis.ChartDensity>, ready:Bool):Void {
		if (ready && chartIcon == null) {
			chartIcon = new HealthIcon(character, false, false, false, song);
			chartIcon.setGraphicSize(Std.int(34 * chartIcon.width / Math.max(chartIcon.width, chartIcon.height))); chartIcon.updateHitbox(); add(chartIcon);
		}
		var difficulties = !ready ? [] : (difficulty < 0 ? DifficultyManager.getSupportedDiffs(song) : [difficulty]);
		var signature = difficulties.join(',');
		if (signature != artworkDifficulties) {
			for (star in chartStars) { remove(star, true); star.destroy(); }
			chartStars = []; artworkDifficulties = signature;
			for (diff in difficulties) {
				var star = new RankStar(song, diff);
				star.configureCard(diff == difficulty ? density : ChartDensityCache.read(song, DifficultyManager.getDiffName(diff)));
				chartStars.push(star); add(star);
			}
			chartStar = chartStars.length == 0 ? null : chartStars[0];
		} else for (star in chartStars)
			star.updateDensity(star.diff == difficulty ? density : ChartDensityCache.read(song, DifficultyManager.getDiffName(star.diff)));
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
		var moved = motion.advance(elapsed);
		if (moved) { setPosition(motion.x, motion.y); drawPresentation(); }
		animateTrail(elapsed); return moved;
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
		add(panel);
		add(divider); add(stripe); add(placeholder); add(title); add(chartTag); add(favoriteTag);
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
			title.text = FreeplayBrowserLayout.label(FreeplaySongTitle.display(label), Std.int((rowWidth - 370) / (selected ? 17 : 14)));
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
		var spacing = Math.min(36, 196 / Math.max(1, chartStars.length));
		for (i in 0...chartStars.length) {
			var star = chartStars[i];
			star.setGraphicSize(Std.int(Math.max(2, Math.min(26, spacing - 4)))); star.updateHitbox();
			star.cardX = x + rowWidth - (chartCaption == '' ? 244 : 94) + i * spacing;
			star.cardY = y - 2; star.setPosition(star.cardX, y + 3); star.visible = !selected; star.alpha = disabled ? 0.45 : 1;
		}
		chartTag.text = FreeplayBrowserLayout.label(chartCaption.toUpperCase(), 16);
		chartTag.setPosition(x + rowWidth - 244, y + 8); chartTag.visible = !selected && chartCaption != '';
		placeholder.visible = chartIcon == null && !hasIcon && chartCaption == '';
	}
}
