package modchart.backend.standalone.adapters.cammie;

import flixel.FlxCamera;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import haxe.ds.ObjectMap;
import modchart.backend.standalone.IAdapter;
import modchart.Manager;
import CodenameModchartClock;
import Conductor;
import Note;
import NoteHoldCover;
import NoteHoldCoverCompat;
import NoteSplash;
import OptionsHandler;
import PlayState;
import Strumline;

/** FunkinModchart adapter for this fork's native PlayState/Strumline model. */
class Cammie implements IAdapter {
	static var activeAdapter:Cammie;
	var owner:PlayState;
	var trackedSprites:Array<FlxSprite> = [];
	var trackedSet:ObjectMap<FlxSprite, Bool> = new ObjectMap();
	var preparedArrowItems:Null<Array<Array<Array<FlxSprite>>>>;

	public function new() {}

	public function onModchartingInitialization():Void {
		try {
			owner = currentState();
			validateLineMappings();
			validateChartNotes();
			activeAdapter = this;
		} catch (error:Dynamic) {
			// Manager.new() assigns Manager.instance before it calls the adapter.
			// If validation throws, construction never returns a value for the
			// caller to add/destroy, so release our owner reference and clear that
			// partially constructed singleton before allowing the source error out.
			try onModchartingDispose() catch (cleanupError:Dynamic)
				trace('[funkin-modchart-cleanup] adapter cleanup after initialization failure failed: '
					+ Std.string(cleanupError));
			if (Manager.instance != null)
				Manager.instance = null;
			throw error;
		}
	}

	public function onModchartingDispose():Void {
		// CtxRenderer hides the native FlxSprite after capturing its original
		// visibility in FlxBasic._fmVisible. Restore that original state if the
		// manager is removed before PlayState itself is destroyed.
		for (sprite in trackedSprites) {
			if (sprite == null || !sprite.exists)
				continue;
			if (sprite._fmVisible != null)
				sprite.visible = sprite._fmVisible;
		}
		trackedSprites.resize(0);
		trackedSet = new ObjectMap();
		preparedArrowItems = null;
		if (activeAdapter == this)
			activeAdapter = null;
		owner = null;
	}

	/** Suppress the ordinary native sprite pass before PlayState draws its
		members. The modchart renderer reads each sprite's preserved _fmVisible
		value and consumes this same snapshot later in the frame. */
	public static function prepareNativeDraw(state:PlayState, parentWillDrawMembers:Bool):Void {
		if (activeAdapter != null)
			activeAdapter.prepareNativeDrawForOwner(state, parentWillDrawMembers);
	}

	function prepareNativeDrawForOwner(state:PlayState, parentWillDrawMembers:Bool):Void {
		if (!parentWillDrawMembers || owner != state
			|| !CodenameModchartDrawOwnership.managerOwnsVisibleDraw(state, Manager.instance)) {
			preparedArrowItems = null;
			restoreTrackedSprites();
			return;
		}

		preparedArrowItems = collectArrowItems();
		for (playerItems in preparedArrowItems)
			for (category in playerItems)
				for (sprite in category)
					if (sprite != null)
						@:bypassAccessor sprite.visible = false;
	}

	function restoreTrackedSprites():Void {
		for (sprite in trackedSprites)
			if (sprite != null && sprite.exists && sprite._fmVisible != null)
				sprite.visible = sprite._fmVisible;
	}

	public function getSongPosition():Float {
		state();
		return Conductor.songPosition;
	}

	public function getCurrentBeat():Float {
		state();
		var initialBpm = PlayState.SONG == null ? Math.NaN : PlayState.SONG.bpm;
		return CodenameModchartClock.beatAtTime(Conductor.songPosition, initialBpm, Conductor.bpmChangeMap);
	}

	public function getCurrentCrochet():Float {
		state();
		var initialBpm = PlayState.SONG == null ? Math.NaN : PlayState.SONG.bpm;
		return CodenameModchartClock.crochetAtTime(Conductor.songPosition, initialBpm, Conductor.bpmChangeMap);
	}

	public function getCurrentScrollSpeed():Float
		return PlayState.effectiveScrollSpeed * 0.45;

	/** FunkinModchart 1.2.5 passes song-time milliseconds despite this parameter name. */
	public function getBeatFromStep(songTime:Float):Float {
		state();
		var initialBpm = PlayState.SONG == null ? Math.NaN : PlayState.SONG.bpm;
		return CodenameModchartClock.beatAtTime(songTime, initialBpm, Conductor.bpmChangeMap);
	}

	public function getDefaultReceptorX(lane:Int, player:Int):Float
		return receptor(lane, player).x;

	public function getDefaultReceptorY(lane:Int, player:Int):Float
		return receptor(lane, player).y;

	public function getTimeFromArrow(arrow:FlxSprite):Float {
		if (Std.isOfType(arrow, Note))
			return (cast arrow:Note).strumTime;
		return 0;
	}

	public function isTapNote(sprite:FlxSprite):Bool
		return Std.isOfType(sprite, Note);

	public function isHoldEnd(sprite:FlxSprite):Bool {
		if (!Std.isOfType(sprite, Note))
			return false;
		var note:Note = cast sprite;
		return note.isSustainNote && note.animation != null && note.animation.curAnim != null
			&& StringTools.endsWith(note.animation.curAnim.name.toLowerCase(), 'holdend');
	}

	public function arrowHit(sprite:FlxSprite):Bool {
		if (Std.isOfType(sprite, Note))
			return (cast sprite:Note).wasGoodHit;
		if (Std.isOfType(sprite, NoteHoldCover)) {
			var note = holdCoverNote(cast sprite);
			return note != null && note.wasGoodHit;
		}
		return false;
	}

	public function getHoldParentTime(sprite:FlxSprite):Float {
		var note = requireNote(sprite, 'hold parent time');
		var head = note;
		while (head.prevNote != null && head.prevNote != head) {
			if (!head.prevNote.isSustainNote) {
				head = head.prevNote;
				break;
			}
			head = head.prevNote;
		}
		return head.strumTime;
	}

	/** Native notes are segmented; FunkinModchart needs the interval of each fragment. */
	public function getHoldLength(sprite:FlxSprite):Float {
		var note = requireNote(sprite, 'hold fragment length');
		if (!note.isSustainNote)
			return Math.max(0, note.sustainLength);
		if (note.prevNote != null && note.prevNote != note) {
			var interval = note.strumTime - note.prevNote.strumTime;
			if (Math.isFinite(interval) && interval > 0)
				return interval;
		}
		if (Math.isFinite(Conductor.stepCrochet) && Conductor.stepCrochet > 0)
			return Conductor.stepCrochet;
		throw '[funkin-modchart-adapter] cannot determine the hold fragment duration';
	}

	public function getLaneFromArrow(sprite:FlxSprite):Int {
		if (Std.isOfType(sprite, Note))
			return Std.int(Math.abs((cast sprite:Note).noteData));
		if (Std.isOfType(sprite, Strumline.StrumNote))
			return (cast sprite:Strumline.StrumNote).ID;
		if (Std.isOfType(sprite, NoteSplash))
			return (cast sprite:NoteSplash).direction;
		if (Std.isOfType(sprite, NoteHoldCover))
			return (cast sprite:NoteHoldCover).direction;
		throw unsupportedSprite(sprite, 'lane');
	}

	public function getPlayerFromArrow(sprite:FlxSprite):Int {
		if (Std.isOfType(sprite, Note))
			return playerForNote(cast sprite);
		if (Std.isOfType(sprite, Strumline.StrumNote)) {
			var receptor:Strumline.StrumNote = cast sprite;
			if (receptor.parentLine == null)
				throw '[funkin-modchart-adapter] receptor has no owning Strumline';
			return playerForNativeGroup(receptor.parentLine);
		}
		if (Std.isOfType(sprite, NoteSplash)) {
			var splash:NoteSplash = cast sprite;
			if (splash.sourceStrumline == null)
				throw '[funkin-modchart-adapter] active splash has no source Strumline metadata';
			return playerForNativeGroup(splash.sourceStrumline);
		}
		if (Std.isOfType(sprite, NoteHoldCover)) {
			var note = holdCoverNote(cast sprite);
			if (note == null)
				throw '[funkin-modchart-adapter] active hold cover has no source note';
			return playerForNote(note);
		}
		throw unsupportedSprite(sprite, 'player');
	}

	public function getKeyCount(?player:Int = 0):Int {
		var members = lineMembers(player == null ? 0 : player);
		return members == null ? 0 : members.length;
	}

	public function getPlayerCount():Int {
		var count = sourceLineCount();
		return count > 0 ? count : 2;
	}

	public function getArrowCamera():Array<FlxCamera> {
		var ps = state();
		// The native note group supplies its camera only during its own draw.
		// Preserve that assignment when FunkinModchart takes over rendering.
		var cameras = ModchartCameraCompat.explicitCameras(ps.notes);
		return cameras == null ? [ps.camHUD] : cameras;
	}

	public function getHoldSubdivisions(item:FlxSprite):Int
		return 4;

	public function getDownscroll():Bool {
		if (OptionsHandler.options == null)
			throw '[funkin-modchart-adapter] gameplay options are unavailable';
		return OptionsHandler.options.downscroll;
	}

	/**
		Each row follows FunkinModchart's four-list contract: receptors, taps,
		hold fragments, then attached splashes/hold covers. Authored Codename line
		indices are retained; non-Codename charts use opponent 0 / player 1.
	*/
	public function getArrowItems():Array<Array<Array<FlxSprite>>> {
		if (preparedArrowItems != null) {
			var prepared = preparedArrowItems;
			preparedArrowItems = null;
			return prepared;
		}
		return collectArrowItems();
	}

	function collectArrowItems():Array<Array<Array<FlxSprite>>> {
		var ps = state();
		var result:Array<Array<Array<FlxSprite>>> = [];
		var count = getPlayerCount();
		for (player in 0...count) {
			var row:Array<Array<FlxSprite>> = [[], [], [], []];
			if (!lineVisible(player)) {
				result.push(row);
				continue;
			}
			var receptors = lineMembers(player);
			if (receptors != null)
				for (receptor in receptors)
					if (receptor != null && receptor.exists && receptor.alive) {
						row[0].push(receptor);
						track(receptor);
					}
			result.push(row);
		}

		if (ps.notes != null)
			ps.notes.forEachAlive(function(note:Note):Void {
				var player = playerForNote(note);
				if (!lineVisible(player)) return;
				var category = note.isSustainNote ? 2 : 1;
				result[player][category].push(note);
				track(note);
			});

		var splashes = getSplashGroup();
		if (splashes != null)
			for (splash in splashes.members)
				if (splash != null && splash.exists && splash.alive && splash.sourceStrumline != null) {
					var player = playerForNativeGroup(splash.sourceStrumline);
					if (!lineVisible(player)) continue;
					result[player][3].push(splash);
					track(splash);
				}

		if (sourceLineCount() > 0) {
			for (player in 0...sourceLineCount())
				if (lineVisible(player))
					appendHoldCovers(ps.getCodenameLineStrumline(player), result);
		} else {
			appendHoldCovers(ps.opponentStrumline, result);
			appendHoldCovers(ps.playerStrumline, result);
		}
		return result;
	}

	function lineVisible(player:Int):Bool {
		var ps = state();
		if (sourceLineCount() > 0) {
			var sourceLine = ps.getCodenameInputLine(player);
			var nativeLine = ps.getCodenameLineStrumline(player);
			return sourceLine != null && sourceLine.visible && nativeLine != null && nativeLine.visible;
		}
		var line = player == 0 ? ps.opponentStrumline : ps.playerStrumline;
		return line != null && line.visible;
	}

	function appendHoldCovers(line:Strumline, result:Array<Array<Array<FlxSprite>>>):Void {
		if (line == null || line.noteHoldCovers == null)
			return;
		for (cover in line.noteHoldCovers.members)
			if (cover != null && cover.exists && cover.alive) {
				var note = holdCoverNote(cover);
				if (note == null)
					throw '[funkin-modchart-adapter] active hold cover has no source note';
				var player = playerForNote(note);
				result[player][3].push(cover);
				track(cover);
			}
	}

	function playerForNote(note:Note):Int {
		if (note == null)
			throw '[funkin-modchart-adapter] missing note while resolving source line';
		if (note.codenameOrigin != null) {
			var lineIndex = note.codenameOrigin.lineIndex;
			if (sourceLineCount() <= 0 || lineIndex < 0 || lineIndex >= sourceLineCount()
				|| lineMembers(lineIndex) == null || note.codenameInputLine == null)
				throw '[funkin-modchart-unsupported] Codename note source line $lineIndex has no live native receptor mapping';
			return lineIndex;
		}
		return note.mustPress ? 1 : 0;
	}

	function playerForNativeGroup(line:Strumline):Int {
		var ps = state();
		if (sourceLineCount() > 0) {
			for (index in 0...sourceLineCount())
				if (groupForLine(index) == line)
					return index;
			throw '[funkin-modchart-unsupported] native Strumline has no unique authored Codename line';
		}
		if (line == ps.opponentStrumline) return 0;
		if (line == ps.playerStrumline) return 1;
		throw '[funkin-modchart-unsupported] Strumline does not belong to the active PlayState';
	}

	function receptor(lane:Int, player:Int):Strumline.StrumNote {
		var members = lineMembers(player);
		if (members == null)
			throw '[funkin-modchart-unsupported] source player $player has no live native receptor mapping';
		if (lane < 0 || lane >= members.length || members[lane] == null)
			throw '[funkin-modchart-unsupported] source player $player lane $lane has no live receptor';
		return members[lane];
	}

	function lineMembers(player:Int):Array<Strumline.StrumNote> {
		var ps = state();
		if (player < 0)
			throw '[funkin-modchart-adapter] negative player index $player';
		if (sourceLineCount() > 0) {
			if (player >= sourceLineCount())
				throw '[funkin-modchart-adapter] source player index $player is outside the authored line table';
			var sourceLine = ps.getCodenameInputLine(player);
			return sourceLine == null || sourceLine.members == null
				? null : cast sourceLine.members;
		}
		if (player == 0) return ps.opponentStrumline == null ? null : ps.opponentStrumline.members;
		if (player == 1) return ps.playerStrumline == null ? null : ps.playerStrumline.members;
		throw '[funkin-modchart-adapter] player index $player has no native Strumline';
	}

	function groupForLine(player:Int):Strumline {
		var members = lineMembers(player);
		if (members == null || members.length == 0 || members[0] == null)
			return null;
		return members[0].parentLine;
	}

	function validateLineMappings():Void {
		var count = sourceLineCount();
		for (left in 0...count) {
			var leftGroup = groupForLine(left);
			if (leftGroup == null)
				continue; // actor-only authored rows have no gameplay receptor set.
			for (right in 0...left)
				if (leftGroup == groupForLine(right))
					throw '[funkin-modchart-unsupported] Codename source lines $right and $left share one native receptor group';
		}
	}

	function validateChartNotes():Void {
		var ps = state();
		var pending = pendingNotes();
		for (note in pending)
			validateNoteLine(note);
		if (ps.notes != null)
			ps.notes.forEachAlive(function(note:Note):Void validateNoteLine(note));
	}

	function validateNoteLine(note:Note):Void {
		if (note == null || note.codenameOrigin == null)
			return;
		var lineIndex = note.codenameOrigin.lineIndex;
		if (sourceLineCount() <= 0 || lineIndex < 0 || lineIndex >= sourceLineCount()
			|| lineMembers(lineIndex) == null || note.codenameInputLine == null)
			throw '[funkin-modchart-unsupported] Codename note source line $lineIndex has no live native receptor mapping';
	}

	function sourceLineCount():Int {
		var ps = state();
		var lines:Array<Dynamic> = cast Reflect.field(ps, 'codenameInputLines');
		return lines == null ? 0 : lines.length;
	}

	function pendingNotes():Array<Note> {
		var ps = state();
		var pending:Array<Note> = cast Reflect.field(ps, 'unspawnNotes');
		return pending == null ? [] : pending;
	}

	function getSplashGroup():FlxTypedGroup<NoteSplash> {
		var ps = state();
		return cast Reflect.field(ps, 'grpNoteSplashes');
	}

	function holdCoverNote(cover:NoteHoldCover):Note {
		if (cover == null || cover.holdNote == null)
			return null;
		return cast NoteHoldCoverCompat.unwrap(cover.holdNote);
	}

	function requireNote(sprite:FlxSprite, operation:String):Note {
		if (!Std.isOfType(sprite, Note))
			throw '[funkin-modchart-adapter] $operation requested for a non-Note sprite';
		return cast sprite;
	}

	function track(sprite:FlxSprite):Void {
		if (sprite == null || trackedSet.exists(sprite))
			return;
		trackedSet.set(sprite, true);
		trackedSprites.push(sprite);
	}

	function state():PlayState {
		var current = PlayState.instance;
		if (current == null)
			throw '[funkin-modchart-adapter] no active PlayState';
		if (owner != null && current != owner)
			throw '[funkin-modchart-unsupported] modchart manager outlived its PlayState';
		return current;
	}

	function currentState():PlayState {
		if (PlayState.instance == null)
			throw '[funkin-modchart-adapter] manager initialized without an active PlayState';
		return PlayState.instance;
	}

	function unsupportedSprite(sprite:FlxSprite, request:String):String {
		var type = sprite == null || Type.getClass(sprite) == null
			? 'null' : Type.getClassName(Type.getClass(sprite));
		return '[funkin-modchart-unsupported] cannot resolve $request for sprite $type';
	}
}
