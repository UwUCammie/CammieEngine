package;

import flixel.FlxSprite;
import Judgement.TUI;
import DynamicSprite.DynamicAtlasFrames;

using StringTools;

/**
 * The small runtime bridge for V-Slice's NoteHoldCover effect.
 *
 * A V-Slice note style supplies one Sparrow atlas and three prefixes for each
 * lane.  The legacy engine has no separate sustain-cover object, so keep the
 * effect as a pooled HUD sprite owned by its Strumline.  The bridge is data
 * driven by the generated TUI fields and deliberately does not know any donor
 * song or character ids.
 */
class NoteHoldCover extends FlxSprite {
	public var uiType:String;
	public var direction:Int = 0;
	public var endTime:Float = Math.POSITIVE_INFINITY;
	public var holdNote:Dynamic;

	static final DIRECTIONS:Array<String> = ['left', 'down', 'up', 'right'];

	public function new(type:String) {
		super();
		uiType = type == null ? 'normal' : type;
		var ui:TUI = Reflect.field(Judgement.uiJson, uiType);
		if (ui == null || ui.holdCoverEnabled != true)
			return;

		var assets = ui.holdCoverAssets;
		var xmlFlags = ui.holdCoverAssetXml;
		var pairs:Array<Dynamic> = [];
		if (assets != null)
			for (index in 0...assets.length) {
				var asset = assets[index];
				var xml = xmlFlags != null && index < xmlFlags.length && xmlFlags[index] == true;
				if (!xml || asset == null || StringTools.trim(asset) == '')
					continue;
				var base = 'assets/images/custom_ui/ui_packs/' + ui.uses + '/' + asset;
				if (FNFAssets.exists(base + '.png') && FNFAssets.exists(base + '.xml'))
					pairs.push([base + '.png', base + '.xml']);
			}
		if (pairs.length == 0)
			return;
		frames = DynamicAtlasFrames.combineSparrow(pairs);
		if (frames == null)
			return;

		var starts = ui.holdCoverStartPrefixes;
		var holds = ui.holdCoverHoldPrefixes;
		var ends = ui.holdCoverEndPrefixes;
		for (index in 0...DIRECTIONS.length) {
			var start = starts != null && index < starts.length ? starts[index] : '';
			var hold = holds != null && index < holds.length ? holds[index] : '';
			var end = ends != null && index < ends.length ? ends[index] : '';
			if (start != '') animation.addByPrefix('start' + DIRECTIONS[index], start, 24, false);
			if (hold != '') animation.addByPrefix('hold' + DIRECTIONS[index], hold, 24, true);
			if (end != '') animation.addByPrefix('end' + DIRECTIONS[index], end, 24, false);
		}
		var scale = ui.holdCoverScale == null || ui.holdCoverScale <= 0 ? 1 : ui.holdCoverScale;
		setGraphicSize(Std.int(width * scale));
		antialiasing = !ui.isPixel;
		updateHitbox();
	}

	public function playStart(lane:Int):Void {
		direction = lane < 0 ? 0 : lane % DIRECTIONS.length;
		// Covers are pooled with FlxBasic.kill(), which clears `exists` as well
		// as `alive`; assigning alive alone leaves a reused cover invisible and
		// outside the group's update/draw pass.
		revive();
		var pooledState = NoteHoldCoverCompat.activate();
		alive = pooledState.alive;
		exists = pooledState.exists;
		active = pooledState.active;
		visible = true;
		var name = 'start' + DIRECTIONS[direction];
		if (animation.exists(name))
			animation.play(name, true);
		else
			playContinue(direction);
	}

	public function playContinue(?lane:Int):Void {
		if (lane != null)
			direction = lane < 0 ? 0 : lane % DIRECTIONS.length;
		var name = 'hold' + DIRECTIONS[direction];
		if (animation.exists(name))
			animation.play(name, true);
	}

	public function playEnd(?lane:Int):Void {
		if (lane != null)
			direction = lane < 0 ? 0 : lane % DIRECTIONS.length;
		var name = 'end' + DIRECTIONS[direction];
		if (animation.exists(name))
			animation.play(name, true);
		else
			kill();
	}

	public function configurePosition(strum:Strumline.StrumNote, ui:TUI):Void {
		if (strum == null)
			return;
		x = strum.x + (strum.width - width) / 2;
		y = strum.y + (strum.height - height) / 2;
		if (ui != null) {
			if (ui.holdCoverOffsetX != null)
				x += ui.holdCoverOffsetX;
			if (ui.holdCoverOffsetY != null)
				y += ui.holdCoverOffsetY;
		}
	}

	override public function update(elapsed:Float):Void {
		if (NoteHoldCoverCompat.shouldEnd(endTime, Conductor.songPosition)
			&& animation.curAnim != null && !animation.curAnim.name.startsWith('end'))
			playEnd(direction);
		if (animation.curAnim != null && animation.curAnim.finished) {
			if (animation.curAnim.name.startsWith('start'))
				playContinue(direction);
			else if (animation.curAnim.name.startsWith('end'))
				kill();
		}
		super.update(elapsed);
	}

	override public function kill():Void {
		if (holdNote != null && Reflect.hasField(holdNote, 'cover'))
			try Reflect.setField(holdNote, 'cover', null) catch (_:Dynamic) {}
		holdNote = null;
		endTime = Math.POSITIVE_INFINITY;
		visible = false;
		super.kill();
	}
}
