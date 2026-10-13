package;

import flixel.FlxSprite;
import flixel.text.FlxText;

/** Compact host rows with one expanded selection; live row count remains bounded. */
class FreeplayBrowserRow extends Alphabet {
	var panel:FlxSprite;
	var trails:Array<FlxSprite> = [];
	var trailStars:Array<Int> = [];
	var trailClips:Array<flixel.math.FlxRect> = [];
	var trailClock:Float = 0;
	var trailColor:Int = 0xFFFFDDDD;
	public function setTrailColor(color:Int):Void {
		trailColor = flixel.util.FlxColor.interpolate(color, 0xFFFFFFFF, 0.58);
	}
	var trailShown:Bool = false;
	/** Built on first use: only a selected or hovered card pays for its stars. */
	function buildTrail():Void {
		var frame = FreeplayStarTrail.FRAME; var turns = FreeplayStarTrail.TURNS;
		var key = 'freeplay-trail-star-turns'; var graphic = flixel.FlxG.bitmap.get(key);
		if (graphic == null) {
			// One frame per step of the star's turn; see FreeplayStarTrail.TURNS.
			var bitmap = new openfl.display.BitmapData(frame * turns, frame, true, 0); var shape = new openfl.display.Shape();
			for (turn in 0...turns) {
				var middle = turn * frame + frame / 2; var tilt = turn * (Math.PI * 2 / 5) / turns;
				shape.graphics.beginFill(0xFFFFFF);
				for (i in 0...11) {
					var angle = -Math.PI / 2 + tilt + i * Math.PI / 5; var radius = i % 2 == 0 ? 8.0 : 3.5;
					var px = middle + Math.cos(angle) * radius; var py = frame / 2 + Math.sin(angle) * radius;
					if (i == 0) shape.graphics.moveTo(px, py); else shape.graphics.lineTo(px, py);
				}
				shape.graphics.endFill();
			}
			bitmap.draw(shape); graphic = flixel.FlxG.bitmap.add(bitmap, false, key);
		}
		// Above the panel, below the text. Inserting at one index stacks later
		// sprites lower, which leaves each star above its own tail copies.
		var layer = members.indexOf(panel) + 1;
		// Only stars whose path can cross the card get sprites.
		for (i in 0...FreeplayStarTrail.STARS) if (FreeplayStarTrail.reachesCard(i)) {
			trailStars.push(i);
			for (copy in 0...FreeplayStarTrail.GHOSTS + 1) {
				var star = new FlxSprite(); star.loadGraphic(graphic, true, frame, frame); star.antialiasing = true; star.visible = false;
				insert(layer, star); trails.push(star); trailClips.push(new flixel.math.FlxRect());
			}
		}
	}
	function animateTrail(elapsed:Float):Void {
		// The cursor is hidden in this menu, so pointing must not light a card.
		var activeTrail = !disabled && (selected || (flixel.FlxG.mouse.visible && flixel.FlxG.mouse.overlaps(panel)));
		if (!activeTrail) {
			if (trailShown) { for (star in trails) star.visible = false; trailShown = false; }
			return;
		}
		if (trails.length == 0) buildTrail();
		trailShown = true; trailClock += elapsed;
		var copies = FreeplayStarTrail.GHOSTS + 1;
		// The card is a window onto a taller field that starts just beyond its
		// right edge. A star crossing the top, bottom or right edge is cut off
		// there, and nothing is ever drawn past the card.
		var frame = FreeplayStarTrail.FRAME; var half = frame / 2;
		var cardLeft = x; var cardRight = x + rowWidth; var cardTop = y; var cardBottom = y + motion.height - 4;
		var travel = rowWidth - 36; var reach = (cardBottom - cardTop) / 2;
		var turn = FreeplayStarTrail.SPIN;
		for (slot in 0...trailStars.length) {
			var i = trailStars[slot];
			var head = FreeplayStarTrail.life(trailClock, i);
			for (copy in 0...copies) {
				var star = trails[slot * copies + copy];
				var life = copy == 0 ? head : head - FreeplayStarTrail.ghostLag(copy - 1);
				var opacity = copy == 0 ? FreeplayStarTrail.opacity(head) : FreeplayStarTrail.ghostOpacity(head, copy - 1);
				if (opacity <= 0.01) { star.visible = false; continue; }
				var size = FreeplayStarTrail.scale(life) * (1 - copy * 0.15);
				var px = cardRight - FreeplayStarTrail.entered(life) * travel;
				var py = cardTop + reach + FreeplayStarTrail.offset(i, life) * reach - half;
				// The drawn star is `size` times the frame, about the frame's middle.
				var left = px + half - half * size; var top = py + half - half * size;
				var fromX = FreeplayStarTrail.clipFrom(left, size, cardLeft); var toX = FreeplayStarTrail.clipTo(left, size, cardRight);
				var fromY = FreeplayStarTrail.clipFrom(top, size, cardTop); var toY = FreeplayStarTrail.clipTo(top, size, cardBottom);
				if (toX - fromX < 0.5 || toY - fromY < 0.5) { star.visible = false; continue; }
				star.visible = true; star.alpha = opacity; star.color = trailColor;
				star.scale.set(size, size); star.setPosition(px, py);
				star.animation.frameIndex = FreeplayStarTrail.turnFrame(turn * (trailClock - copy * FreeplayStarTrail.GHOST_STEP * FreeplayStarTrail.PERIOD) + i * 47);
				if (fromX <= 0 && fromY <= 0 && toX >= frame && toY >= frame) { if (star.clipRect != null) star.clipRect = null; }
				else star.clipRect = trailClips[slot * copies + copy].set(fromX, fromY, toX - fromX, toY - fromY);
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
			// Centered in the compact card. The rating is spelled out on the selected card only.
			star.cardY = y + (height - star.height) / 2; star.setPosition(star.cardX, star.cardY); star.visible = !selected; star.alpha = disabled ? 0.45 : 1;
		}
		chartTag.text = FreeplayBrowserLayout.label(chartCaption.toUpperCase(), 16);
		chartTag.setPosition(x + rowWidth - 244, y + 8); chartTag.visible = !selected && chartCaption != '';
		placeholder.visible = chartIcon == null && !hasIcon && chartCaption == '';
	}
}
