package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import openfl.display.Shape;
import openfl.geom.Rectangle;
import ResultsModel.ResultsData;
import ResultsModel.ResultsPlayer;

/**
	The results screen, laid out after osu!lazer's: an expanded panel for the
	local player (accuracy ring that fills to the rank, rolling score, combo and
	judgement counts, modifiers) beside a timing card in solo play, or the whole
	lobby ranked by score in a multiplayer match.

	It loads nothing but the menu background and the result music, so it opens
	immediately however large the song was. The old victory screen loaded every
	character of the song again after the song's images had been released.
**/
class ResultsState extends MusicBeatState {
	static inline var PANEL_X:Int = 48;
	static inline var PANEL_Y:Int = 36;
	static inline var PANEL_WIDTH:Int = 440;
	static inline var PANEL_HEIGHT:Int = 596;
	static inline var SIDE_X:Int = 520;
	static inline var SIDE_WIDTH:Int = 712;
	static inline var RING_RADIUS:Int = 112;
	static inline var RING_THICKNESS:Int = 18;
	static inline var FILL_DELAY:Float = 0.35;
	static inline var FILL_TIME:Float = 2.0;
	static inline var ROW_HEIGHT:Int = 58;
	static inline var VISIBLE_PLAYERS:Int = 9;

	var data:ResultsData;
	var onContinue:Void->Void;
	var elapsedTime:Float = 0;
	var ringSprite:FlxSprite;
	var ringShape:Shape = new Shape();
	var lastFill:Float = -1;
	var rankText:FlxText;
	var scoreText:FlxText;
	var rankShown:Bool = false;
	var staged:Array<FlxSprite> = [];
	var leaving:Bool = false;
	var playerRows:Array<ResultsPlayer> = [];
	var playerTop:Int = 0;
	var playerTexts:Array<FlxText> = [];
	var playerCards:Array<FlxSprite> = [];
	var playerStripes:Array<FlxSprite> = [];

	/** `onContinue` replaces the usual way out (Story menu or Freeplay), e.g. back to a lobby. */
	public function new(data:ResultsData, ?onContinue:Void->Void) {
		super();
		this.data = data;
		this.onContinue = onContinue;
	}

	override function create():Void {
		super.create();
		FlxG.camera.scroll.set();
		FlxG.camera.target = null;
		MenuWidgets.background(this);
		buildPlayerPanel();
		if (data.players != null && data.players.length > 0)
			buildLobby();
		else
			buildTiming();
		var hints:Array<MenuStyle.MenuHint> = [{key: 'ENTER', action: 'Continue'}];
		if (canRetry())
			hints.push({key: 'R', action: 'Retry'});
		if (data.players != null && data.players.length > VISIBLE_PLAYERS)
			hints.push({key: 'UP/DOWN', action: 'Scroll'});
		hints.push({key: 'ESC', action: 'Back'});
		add(new MenuFooter('RESULTS', hints));
		var music = 'assets/music/' + ResultsModel.musicFor(data.player.accuracy) + TitleState.soundExt;
		if (FNFAssets.exists(music))
			FlxG.sound.playMusic(music, 0.7);
	}

	function canRetry():Bool
		return onContinue == null && !data.storyMode && data.players == null && PlayState.SONG != null;

	// ------------------------------------------------------------------ the local player's panel

	function buildPlayerPanel():Void {
		var player = data.player;
		add(MenuWidgets.rect(PANEL_X, PANEL_Y, PANEL_WIDTH, PANEL_HEIGHT, MenuStyle.CARD, MenuStyle.DETAIL_ALPHA));
		add(MenuWidgets.rect(PANEL_X, PANEL_Y, PANEL_WIDTH, 4, MenuStyle.PINK));
		var title = MenuWidgets.text(PANEL_X + 20, PANEL_Y + 18, PANEL_WIDTH - 40, data.title, 24, MenuStyle.CREAM, CENTER);
		add(title);
		var sub = data.difficulty.toUpperCase() + '    ' + (data.unranked ? 'UNRANKED' : 'SCORE x' + Std.string(Math.round(data.multiplier * 100) / 100));
		add(MenuWidgets.text(PANEL_X + 20, PANEL_Y + 18 + title.height + 4, PANEL_WIDTH - 40, sub, MenuStyle.SMALL_SIZE,
			data.unranked ? MenuStyle.AMBER : MenuStyle.MUTED, CENTER));

		var size = (RING_RADIUS + RING_THICKNESS) * 2 + 4;
		ringSprite = new FlxSprite(PANEL_X + PANEL_WIDTH / 2 - size / 2, PANEL_Y + 236 - size / 2);
		ringSprite.makeGraphic(size, size, 0x00000000, true);
		add(ringSprite);
		drawRing(0);

		rankText = MenuWidgets.text(PANEL_X, PANEL_Y + 236 - 44, PANEL_WIDTH, player.rank, 80, ResultsModel.rankColor(player.rank), CENTER);
		rankText.visible = false;
		add(rankText);

		scoreText = MenuWidgets.text(PANEL_X, PANEL_Y + 380, PANEL_WIDTH, '0', 44, MenuStyle.CREAM, CENTER);
		add(scoreText);
		if (!data.unranked && data.previousBest >= 0 && player.score > data.previousBest && !player.failed)
			stage(MenuWidgets.text(PANEL_X, PANEL_Y + 360, PANEL_WIDTH, 'NEW BEST', MenuStyle.SECTION_SIZE + 2, MenuStyle.PINK, CENTER));

		var columnWidth = Std.int((PANEL_WIDTH - 40) / 2);
		stat(PANEL_X + 20, PANEL_Y + 446, columnWidth, 'ACCURACY', ResultsModel.formatAccuracy(player.accuracy));
		stat(PANEL_X + 20 + columnWidth, PANEL_Y + 446, columnWidth, 'MAX COMBO',
			player.maxCombo < 0 ? '-' : player.maxCombo + 'x' + (data.judgeable > 0 ? ' / ' + data.judgeable : ''));

		var judgements:Array<{label:String, value:String, color:Int}> = [
			{label: 'SICK', value: count(player.sicks), color: 0xFF80E3D0}, {label: 'GOOD', value: count(player.goods), color: 0xFF7BE07B},
			{label: 'BAD', value: count(player.bads), color: 0xFFFFD166}, {label: 'SHIT', value: count(player.shits), color: 0xFFFF9F5A},
			{label: 'MISS', value: count(player.misses), color: 0xFFFF6B6B}
		];
		var cell = Std.int((PANEL_WIDTH - 40) / judgements.length);
		for (index in 0...judgements.length) {
			var entry = judgements[index];
			stage(MenuWidgets.text(PANEL_X + 20 + index * cell, PANEL_Y + 506, cell, entry.label, MenuStyle.SECTION_SIZE, entry.color, CENTER));
			stage(MenuWidgets.text(PANEL_X + 20 + index * cell, PANEL_Y + 524, cell, entry.value, MenuStyle.BODY_SIZE, MenuStyle.WHITE, CENTER));
		}
		var names = new Map<String, String>();
		for (modifier in ModifierState.modifiers)
			names.set(modifier.internName, modifier.name);
		stage(MenuWidgets.text(PANEL_X + 20, PANEL_Y + 562, PANEL_WIDTH - 40,
			ResultsModel.modifierNames(player.modifiers, names), MenuStyle.SMALL_SIZE, MenuStyle.MUTED, CENTER));
	}

	/** A judgement count; -1 means it was not kept (a story week's total). */
	static function count(value:Int):String
		return value < 0 ? '-' : Std.string(value);

	function stat(x:Float, y:Float, width:Int, label:String, value:String):Void {
		stage(MenuWidgets.text(x, y, width, label, MenuStyle.SECTION_SIZE, MenuStyle.TEAL, CENTER));
		stage(MenuWidgets.text(x, y + 18, width, value, MenuStyle.TITLE_SIZE, MenuStyle.WHITE, CENTER));
	}

	/** Added hidden; shown one after another once the ring starts filling. */
	function stage(sprite:FlxSprite):Void {
		sprite.alpha = 0;
		staged.push(sprite);
		add(sprite);
	}

	/** Redraw the ring: the rank bands as a dim track, then the filled arc in the achieved rank's colour. */
	function drawRing(fill:Float):Void {
		if (fill == lastFill)
			return;
		lastFill = fill;
		var size = ringSprite.frameWidth;
		var center = size / 2;
		var graphics = ringShape.graphics;
		graphics.clear();
		arc(graphics, center, 0, 1, MenuStyle.CHIP_OFF, 1);
		for (segment in ResultsModel.SEGMENTS)
			arc(graphics, center, segment[0], segment[1], ResultsModel.rankColor(segment[2]), 0.22);
		arc(graphics, center, 0, fill, ResultsModel.rankColor(data.player.rank), 1);
		ringSprite.pixels.fillRect(new Rectangle(0, 0, size, size), 0x00000000);
		ringSprite.pixels.draw(ringShape);
		ringSprite.dirty = true;
	}

	/** A thick arc from accuracy `from` to `to`, clockwise from the top. */
	static function arc(graphics:openfl.display.Graphics, center:Float, from:Float, to:Float, color:Int, alpha:Float):Void {
		if (to <= from)
			return;
		graphics.lineStyle(RING_THICKNESS, color & 0xFFFFFF, alpha, false, openfl.display.LineScaleMode.NORMAL, openfl.display.CapsStyle.NONE);
		var steps = Std.int(Math.max(2, Math.ceil((to - from) * 160)));
		for (step in 0...steps + 1) {
			var angle = (from + (to - from) * step / steps) * Math.PI * 2 - Math.PI / 2;
			var x = center + Math.cos(angle) * RING_RADIUS;
			var y = center + Math.sin(angle) * RING_RADIUS;
			if (step == 0)
				graphics.moveTo(x, y);
			else
				graphics.lineTo(x, y);
		}
	}

	// ------------------------------------------------------------------ solo: timing card

	function buildTiming():Void {
		var top = PANEL_Y;
		MenuWidgets.detailCard(this, SIDE_X, top, SIDE_WIDTH, 300, 'TIMING', MenuStyle.TEAL);
		var stats = ResultsModel.hitErrors(data.hitOffsets);
		if (stats.count == 0) {
			add(MenuWidgets.text(SIDE_X + 20, top + 140, SIDE_WIDTH - 40, 'No timed hits in this play.', MenuStyle.BODY_SIZE, MenuStyle.MUTED, CENTER));
		} else {
			var range = Judge.wayoffJudge > 0 ? Judge.wayoffJudge : 166.0;
			var bins = 41;
			var counts = ResultsModel.histogram(data.hitOffsets, bins, range);
			var tallest = 1;
			for (count in counts)
				if (count > tallest)
					tallest = count;
			var graphLeft = SIDE_X + 24;
			var graphWidth = SIDE_WIDTH - 48;
			var graphBottom = top + 220;
			var barWidth = graphWidth / bins;
			for (index in 0...bins) {
				var middle = Math.abs((index + 0.5) / bins * 2 * range - range);
				var height = Math.max(2, counts[index] / tallest * 170);
				var color = middle <= Judge.sickJudge ? 0xFF80E3D0 : middle <= Judge.goodJudge ? 0xFF7BE07B
					: middle <= Judge.badJudge ? 0xFFFFD166 : 0xFFFF9F5A;
				stage(MenuWidgets.rect(graphLeft + index * barWidth + 1, graphBottom - height, Math.max(1, barWidth - 2), height, color));
			}
			add(MenuWidgets.rect(graphLeft + graphWidth / 2, top + 40, 1, 184, MenuStyle.WHITE, 0.4));
			add(MenuWidgets.text(graphLeft, graphBottom + 6, 120, 'EARLY', MenuStyle.SECTION_SIZE, MenuStyle.MUTED));
			add(MenuWidgets.text(graphLeft + graphWidth - 120, graphBottom + 6, 120, 'LATE', MenuStyle.SECTION_SIZE, MenuStyle.MUTED, RIGHT));
			stage(MenuWidgets.text(SIDE_X + 20, top + 252, SIDE_WIDTH / 2 - 20,
				'Average: ' + ResultsModel.meanLabel(stats.mean), MenuStyle.BODY_SIZE, MenuStyle.TEXT));
			stage(MenuWidgets.text(SIDE_X + SIDE_WIDTH / 2, top + 252, SIDE_WIDTH / 2 - 20,
				'Unstable rate: ' + Std.string(Math.round(stats.unstableRate * 10) / 10), MenuStyle.BODY_SIZE, MenuStyle.TEXT, RIGHT));
		}

		var bestTop = top + 324;
		MenuWidgets.detailCard(this, SIDE_X, bestTop, SIDE_WIDTH, 120, 'BEST BEFORE THIS PLAY', MenuStyle.GOLD);
		var best = data.previousBest > 0
			? ResultsModel.formatScore(data.previousBest) + (data.previousRank == '' ? '' : '    ' + data.previousRank)
			: 'No score yet';
		stage(MenuWidgets.text(SIDE_X + 20, bestTop + 44, SIDE_WIDTH - 40, best, MenuStyle.SELECTED_TITLE_SIZE, MenuStyle.CREAM));
		if (data.unranked)
			stage(MenuWidgets.text(SIDE_X + 20, bestTop + 82, SIDE_WIDTH - 40,
				'This play used practice, autoplay or a play style modifier, so it was not saved.', MenuStyle.SMALL_SIZE, MenuStyle.AMBER));
	}

	// ------------------------------------------------------------------ multiplayer: the lobby ranked

	function buildLobby():Void {
		playerRows = ResultsModel.ordered(data.players);
		MenuWidgets.detailCard(this, SIDE_X, PANEL_Y, SIDE_WIDTH, PANEL_HEIGHT, 'MATCH RESULTS', MenuStyle.PINK);
		if (data.note != null && data.note != '')
			add(MenuWidgets.text(SIDE_X + 20, PANEL_Y + 22, SIDE_WIDTH - 40, data.note, MenuStyle.SMALL_SIZE, MenuStyle.AMBER));
		for (slot in 0...VISIBLE_PLAYERS) {
			var y = PANEL_Y + 48 + slot * ROW_HEIGHT;
			var card = MenuWidgets.rect(SIDE_X + 12, y, SIDE_WIDTH - 24, ROW_HEIGHT - 6, MenuStyle.WHITE);
			playerCards.push(card);
			add(card);
			var stripe = MenuWidgets.rect(SIDE_X + 12, y, MenuStyle.STRIPE_WIDTH, ROW_HEIGHT - 6, MenuStyle.PINK);
			playerStripes.push(stripe);
			add(stripe);
			var text = MenuWidgets.text(SIDE_X + 28, y + 16, SIDE_WIDTH - 56, '', MenuStyle.BODY_SIZE, MenuStyle.TEXT);
			text.wordWrap = false;
			playerTexts.push(text);
			add(text);
		}
		var own = 0;
		for (index in 0...playerRows.length)
			if (playerRows[index].id == data.player.id)
				own = index;
		playerTop = Std.int(Math.max(0, Math.min(own - Std.int(VISIBLE_PLAYERS / 2), playerRows.length - VISIBLE_PLAYERS)));
		renderLobby();
	}

	function renderLobby():Void {
		for (slot in 0...VISIBLE_PLAYERS) {
			var index = playerTop + slot;
			var visible = index < playerRows.length;
			playerCards[slot].visible = playerTexts[slot].visible = visible;
			playerStripes[slot].visible = false;
			if (!visible)
				continue;
			var row = playerRows[index];
			var own = row.id == data.player.id;
			playerCards[slot].color = own ? MenuStyle.CARD_SELECTED : MenuStyle.CARD;
			playerCards[slot].alpha = own ? 1 : 0.8;
			playerStripes[slot].visible = own;
			var place = StringTools.lpad('#' + (index + 1), ' ', 4);
			var name = row.name.length > 16 ? row.name.substr(0, 15) + '.' : StringTools.rpad(row.name, ' ', 16);
			var status = row.quit ? 'LEFT' : (row.failed ? 'FAILED' : row.rank);
			playerTexts[slot].text = place + '  ' + name + '  ' + StringTools.lpad(ResultsModel.formatScore(row.score), ' ', 9)
				+ '  ' + StringTools.lpad(ResultsModel.formatAccuracy(row.accuracy), ' ', 7) + '  ' + StringTools.lpad(row.maxCombo + 'x', ' ', 6)
				+ '  ' + status;
			playerTexts[slot].color = row.quit ? MenuStyle.DISABLED : (own ? MenuStyle.CREAM : MenuStyle.TEXT);
		}
	}

	// ------------------------------------------------------------------ animation and input

	override function update(elapsed:Float):Void {
		super.update(elapsed);
		// The smoke gate's clock normally runs in PlayState; keep it running here too.
		RuntimeSmokeHarness.tick(elapsed);
		elapsedTime += elapsed;
		var t = (elapsedTime - FILL_DELAY) / FILL_TIME;
		var eased = ResultsModel.fillEase(t);
		var accuracy = data.player.failed ? 0 : data.player.accuracy;
		drawRing(accuracy * eased);
		scoreText.text = ResultsModel.formatScore(Std.int(Math.round(data.player.score * eased)));
		if (!rankShown && t >= 1) {
			rankShown = true;
			rankText.visible = true;
			rankText.scale.set(1.6, 1.6);
			FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt, 0.6);
		}
		if (rankShown && rankText.scale.x > 1)
			rankText.scale.set(Math.max(1, rankText.scale.x - elapsed * 3), Math.max(1, rankText.scale.y - elapsed * 3));
		for (index in 0...staged.length) {
			var start = FILL_DELAY + 0.25 + index * 0.04;
			staged[index].alpha = Math.max(0, Math.min(1, (elapsedTime - start) / 0.25));
		}
		if (leaving)
			return;
		if (data.players != null && data.players.length > VISIBLE_PLAYERS) {
			if (controls.UP_MENU && playerTop > 0) {
				playerTop--;
				renderLobby();
			}
			if (controls.DOWN_MENU && playerTop < playerRows.length - VISIBLE_PLAYERS) {
				playerTop++;
				renderLobby();
			}
		}
		if (canRetry() && FlxG.keys.justPressed.R) {
			retry();
			return;
		}
		if (controls.ACCEPT || controls.BACK)
			leave();
	}

	function retry():Void {
		leaving = true;
		if (FlxG.sound.music != null)
			FlxG.sound.music.stop();
		FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt);
		LoadingState.loadAndSwitchState(new PlayState());
	}

	function leave():Void {
		leaving = true;
		if (FlxG.sound.music != null)
			FlxG.sound.music.stop();
		if (onContinue != null) {
			onContinue();
			return;
		}
		if (data.storyMode)
			LoadingState.loadAndSwitchState(new StoryMenuState());
		else
			ImportedMenuEntry.returnToFreeplay();
	}
}
