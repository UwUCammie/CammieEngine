package;

import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup;
import flixel.group.FlxGroup.FlxTypedGroup;

/**
	A copied, engine-owned note descriptor for a foreign chart difficulty.

	V-Slice calls this object SongNoteData.  Keeping the small descriptor here
	means an imported script can ask which receptor owns a note without receiving
	the donor chart, section object, or any other arbitrary object graph.  The
	values are copied when the view is made; the source chart can subsequently be
	destroyed or reloaded without changing the live adapter.
*/
class CompatSongNoteData {
	public var strumTime:Float;
	public var data:Int;
	public var length:Float;
	public var kind:String;
	public var strumlineIndex:Int;

	/** V-Slice's noteData.data spelling. */
	public var noteData(get, never):CompatSongNoteData;
	function get_noteData():CompatSongNoteData return this;

	/** Keep both names used by V-Slice and older HXC scripts. */
	public var sustainLength(get, never):Float;
	function get_sustainLength():Float return length;
	public var time(get, never):Float;
	function get_time():Float return strumTime;

	public function new(strumTime:Float, data:Int, length:Float = 0,
		?kind:String = null, ?strumlineIndex:Null<Int>) {
		this.strumTime = strumTime;
		this.data = data;
		this.length = length < 0 || Math.isNaN(length) ? 0 : length;
		this.kind = kind == null ? '' : kind;
		this.strumlineIndex = strumlineIndex == null
			? (data >= 4 ? 1 : 0) : Std.int(strumlineIndex);
	}

	public function getDirection():Int {
		var direction = data < 0 ? -data : data;
		return direction % 4;
	}

	public function getStrumlineIndex():Int return strumlineIndex;
	public function getMustHitNote():Bool return strumlineIndex == 0;

	public static function fromDynamic(value:Dynamic, ?mustHitSection:Bool = true,
		?noteAmount:Int = 4):Null<CompatSongNoteData> {
		if (value == null)
			return null;
		if (Std.isOfType(value, CompatSongNoteData)) {
			var source:CompatSongNoteData = cast value;
			return new CompatSongNoteData(source.strumTime, source.data, source.length,
				source.kind, source.strumlineIndex);
		}
		if (noteAmount <= 0)
			noteAmount = 4;

		var values:Array<Dynamic> = Std.isOfType(value, Array) ? cast value : null;
		var timeValue:Dynamic = values != null && values.length > 0 ? values[0] : Reflect.field(value, 'strumTime');
		if (timeValue == null) timeValue = Reflect.field(value, 'time');
		if (timeValue == null) timeValue = Reflect.field(value, 't');
		var strumTime = parseNumber(timeValue);
		if (Math.isNaN(strumTime))
			return null;

		var dataValue:Dynamic = values != null && values.length > 1 ? values[1] : Reflect.field(value, 'data');
		if (dataValue == null) dataValue = Reflect.field(value, 'd');
		if (dataValue == null) {
			var nested = Reflect.field(value, 'noteData');
			dataValue = nested == null ? null : Reflect.field(nested, 'data');
			if (dataValue == null)
				dataValue = nested;
		}
		var data = parseInt(dataValue);
		if (data == null)
			return null;

		var lengthValue:Dynamic = values != null && values.length > 2 ? values[2] : Reflect.field(value, 'sustainLength');
		if (lengthValue == null) lengthValue = Reflect.field(value, 'length');
		if (lengthValue == null) lengthValue = Reflect.field(value, 'l');
		var length = parseNumber(lengthValue);
		if (Math.isNaN(length))
			length = 0;
		var kindValue:Dynamic = values != null && values.length > 3 ? values[3] : Reflect.field(value, 'kind');
		if (kindValue == null) kindValue = Reflect.field(value, 'k');
		var kind = kindValue == null ? '' : Std.string(kindValue);

		var side:Null<Int> = null;
		var sideValue:Dynamic = Reflect.field(value, 'strumlineIndex');
		if (sideValue == null) sideValue = Reflect.field(value, 'mustHitNote');
		if (sideValue != null) {
			if (Std.isOfType(sideValue, Bool))
				side = (cast sideValue:Bool) ? 0 : 1;
			else
				side = parseInt(sideValue);
		}
		if (side == null) {
			var lane = data % (noteAmount * 2);
			if (lane < 0) lane += noteAmount * 2;
			var flipped = lane >= noteAmount;
			side = (mustHitSection != flipped) ? 0 : 1;
		}
		return new CompatSongNoteData(strumTime, data, length, kind, side);
	}

	static function parseNumber(value:Dynamic):Float {
		if (value == null || Std.isOfType(value, Bool))
			return Math.NaN;
		var result = Std.parseFloat(Std.string(value));
		return result;
	}

	static function parseInt(value:Dynamic):Null<Int> {
		if (value == null || Std.isOfType(value, Bool))
			return null;
		var parsed = Std.parseInt(Std.string(value));
		if (parsed != null)
			return parsed;
		var number = parseNumber(value);
		return Math.isNaN(number) ? null : Std.int(number);
	}
}

/**
	A read-only difficulty view used by HXC's extra-strumline scripts.

	Native PlayState charts retain their section rows.  This view flattens those
	rows into copied CompatSongNoteData values and leaves the original chart
	untouched.  `sections` remains available to diagnostics, but imported code
	gets the donor-facing `.notes` list it actually consumes.
*/
class CompatSongDifficultyView {
	public var notes:Array<CompatSongNoteData> = [];
	public var sections:Array<Dynamic> = [];
	public var song:String = '';
	public var bpm:Float = 0;
	public var speed:Float = 1;
	public var scrollSpeed(get, never):Float;
	function get_scrollSpeed():Float return speed;

	public function new(chart:Dynamic) {
		if (chart == null)
			return;
		var songValue = Reflect.field(chart, 'song');
		if (songValue != null && Std.isOfType(songValue, String))
			song = Std.string(songValue);
		bpm = positiveNumber(Reflect.field(chart, 'bpm'), 0);
		speed = positiveNumber(Reflect.field(chart, 'speed'), 1);
		var amount = Std.int(positiveNumber(Reflect.field(chart, 'preferredNoteAmount'), 4));
		if (amount <= 0)
			amount = 4;
		var source = Reflect.field(chart, 'notes');
		if (!Std.isOfType(source, Array))
			return;
		// Keep the diagnostic section view data-only as well. A shallow array copy
		// would still expose the native chart's section/row objects to HScript and
		// let a foreign callback mutate the active gameplay chart.
		for (section in (cast source:Array<Dynamic>))
			sections.push(copyData(section));
		for (section in (cast source:Array<Dynamic>)) {
			if (section == null)
				continue;
			var rows:Dynamic = Reflect.field(section, 'sectionNotes');
			if (Std.isOfType(rows, Array)) {
				var mustHit = Reflect.field(section, 'mustHitSection') == true;
				for (row in (cast rows:Array<Dynamic>)) {
					var converted = CompatSongNoteData.fromDynamic(row, mustHit, amount);
					if (converted != null)
						notes.push(converted);
				}
			} else {
				var converted = CompatSongNoteData.fromDynamic(section, true, amount);
				if (converted != null)
					notes.push(converted);
			}
		}
		notes.sort(function(a, b):Int return a.strumTime < b.strumTime ? -1 : a.strumTime > b.strumTime ? 1 : 0);
	}

	static function positiveNumber(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var result = Std.parseFloat(Std.string(value));
		return Math.isNaN(result) || result <= 0 ? fallback : result;
	}

	static function copyData(value:Dynamic):Dynamic {
		if (value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool)
			|| Std.isOfType(value, Int) || Std.isOfType(value, Float))
			return value;
		if (Std.isOfType(value, Array)) {
			var copied:Array<Dynamic> = [];
			for (entry in (cast value:Array<Dynamic>))
				copied.push(copyData(entry));
			return copied;
		}
		var copiedObject:Dynamic = {};
		for (field in Reflect.fields(value))
			Reflect.setField(copiedObject, field, copyData(Reflect.field(value, field)));
		return copiedObject;
	}
}

/** A deliberately tiny signal with both HXC (`add`) and native (`connect`) names. */
class ExtraStrumlineSignal {
	var callbacks:Array<Dynamic->Void> = [];

	public function new() {}
	public function add(callback:Dynamic->Void):Void {
		if (callback != null && callbacks.indexOf(callback) < 0)
			callbacks.push(callback);
	}
	public function connect(callback:Dynamic->Void):Void add(callback);
	public function remove(callback:Dynamic->Void):Void callbacks.remove(callback);
	public function disconnect(callback:Dynamic->Void):Void remove(callback);
	public function reset():Void callbacks.resize(0);
	public function dispatch(value:Dynamic):Void {
		for (callback in callbacks.copy())
			callback(value);
	}
}

/**
	HXC's note view.  The native Note remains private to the adapter's ownership
	path; scripts see only copied note data and the bounded lifecycle flags below.
*/
class ExtraStrumlineNoteView {
	public var nativeNote:Note;
	public var noteData:CompatSongNoteData;
	/** Head that owns this sustain segment, or null for a tap/head note. */
	public var holdHead:Null<ExtraStrumlineNoteView>;
	public var hitNote:Bool = false;
	public var missedNote:Bool = false;
	public var handledMiss:Bool = false;
	public var ID:Int = 0;

	public var strumTime(get, never):Float;
	function get_strumTime():Float return nativeNote == null ? 0 : nativeNote.strumTime;
	public var sustainLength(get, never):Float;
	function get_sustainLength():Float return nativeNote == null ? 0 : nativeNote.sustainLength;
	public var isSustainNote(get, never):Bool;
	function get_isSustainNote():Bool return nativeNote != null && nativeNote.isSustainNote;
	public var alive(get, never):Bool;
	function get_alive():Bool return nativeNote != null && nativeNote.alive;
	public var active(get, set):Bool;
	function get_active():Bool return nativeNote != null && nativeNote.active;
	function set_active(value:Bool):Bool {
		if (nativeNote != null) nativeNote.active = value;
		return value;
	}
	public var visible(get, set):Bool;
	function get_visible():Bool return nativeNote != null && nativeNote.visible;
	function set_visible(value:Bool):Bool {
		if (nativeNote != null) nativeNote.visible = value;
		return value;
	}
	public var holdNoteSprite(get, never):Dynamic;
	function get_holdNoteSprite():Dynamic {
		return nativeNote != null && nativeNote.sustainLength > 0 ? this : null;
	}
	public var alpha(get, set):Float;
	function get_alpha():Float return nativeNote == null ? 0 : nativeNote.alpha;
	function set_alpha(value:Float):Float {
		if (nativeNote != null) nativeNote.alpha = value;
		return value;
	}

	public function new(note:Note, data:CompatSongNoteData, id:Int = 0,
		?holdHead:ExtraStrumlineNoteView) {
		nativeNote = note;
		noteData = data;
		this.ID = id;
		this.holdHead = holdHead;
	}
	public function kill():Void if (nativeNote != null) nativeNote.kill();
	public function destroy():Void if (nativeNote != null) nativeNote.destroy();
	public function updateHitbox():Void if (nativeNote != null) nativeNote.updateHitbox();
}

/** A small view object matching Flixel's `.members` surface. */
class ExtraStrumlineNoteList {
	public var members:Array<ExtraStrumlineNoteView> = [];
	public function new() {}
	public function clear():Void members.resize(0);
}

/**
	The reusable native owner for a second foreign strumline.

	It owns separate pending/head/hold collections and separate Note sprites, so
	applying an imported difficulty cannot enter PlayState.unspawnNotes or alter
	native score/combo counters.  The class intentionally exposes only the
	operations used by the selected donor API; arbitrary donor objects are not
	stored or reflected through the interpreter.
*/
class ExtraStrumlineAdapter extends FlxSpriteGroup {
	/** Shared V-Slice geometry constant exposed by the script Strumline alias. */
	public static var INITIAL_OFFSET:Float = Strumline.INITIAL_OFFSET;
	public var noteStyle:Dynamic;
	public var notes:ExtraStrumlineNoteList = new ExtraStrumlineNoteList();
	public var holdNotes:ExtraStrumlineNoteList = new ExtraStrumlineNoteList();
	public var noteHoldCovers:FlxTypedGroup<NoteHoldCover>;
	public var onNoteIncoming:ExtraStrumlineSignal = new ExtraStrumlineSignal();
	public var skippedNotes:Int = 0;
	public var hitNotes:Int = 0;
	public var missedNotes:Int = 0;
	public var botplay:Bool = false;
	public var scrollSpeed:Float = 1;
	public var strumlineNotes(get, never):FlxTypedSpriteGroup<Strumline.StrumNote>;
	function get_strumlineNotes():FlxTypedSpriteGroup<Strumline.StrumNote> return receptors.strumlineNotes;
	public var strumlineScale(get, never):Dynamic;
	function get_strumlineScale():Dynamic return scale;

	var receptors:Strumline;
	var pending:Array<ExtraStrumlineNoteView> = [];
	var rendered:Array<FlxSprite> = [];
	var styleId:String = 'normal';

	public function new(style:Dynamic, ?botplay:Bool = false, ?foreignScrollSpeed:Dynamic) {
		super(0, 0);
		this.botplay = botplay;
		styleId = resolveStyleId(style);
		noteStyle = {id: styleId};
		receptors = new Strumline(0, 0, styleId);
		noteHoldCovers = receptors.noteHoldCovers;
		add(receptors);
		var parsedSpeed = foreignScrollSpeed == null ? 1 : Std.parseFloat(Std.string(foreignScrollSpeed));
		if (!Math.isNaN(parsedSpeed) && parsedSpeed > 0)
			scrollSpeed = parsedSpeed;
	}

	public function changeType(type:String = 'normal', ?transition:Bool = false):Void {
		if (type == null || StringTools.trim(type) == '')
			type = 'normal';
		styleId = type;
		noteStyle = {id: styleId};
		receptors.changeType(type, transition);
		noteHoldCovers = receptors.noteHoldCovers;
	}

	public function setNoteSpacing(multiplier:Float = 1):Void receptors.setNoteSpacing(multiplier);
	public function fadeInArrows(?duration:Float = 0.2):Void receptors.fadeInArrows(duration);
	public function enterMiniMode(multiplier:Float = 1):Void {
		if (Math.isNaN(multiplier) || multiplier <= 0)
			return;
		// Scale the owner, not both owner and nested receptors. This keeps the
		// donor's width/height positioning and `strumlineScale` read in the same
		// coordinate space as the visible line.
		scale.set(multiplier, multiplier);
		receptors.scale.set(1, 1);
		receptors.setNoteSpacing(multiplier);
	}

	/** Clone a native difficulty view into this adapter's private queues. */
	public function applyNoteData(values:Array<Dynamic>):Void {
		clean();
		if (values == null)
			return;
		for (value in values) {
			var data = CompatSongNoteData.fromDynamic(value);
			if (data == null)
				continue;
			var direction = data.getDirection();
			var previous:Note = null;
			var head = new Note(data.strumTime, direction, null, false);
			configureNote(head, data, false);
			var headView = new ExtraStrumlineNoteView(head, data, pending.length);
			pending.push(headView);
			previous = head;
			var count = sustainPieces(data.length);
			for (index in 0...count) {
				var sustain = new Note(data.strumTime + Conductor.stepCrochet * (index + 1),
					direction, previous, true);
				configureNote(sustain, data, true);
				var holdView = new ExtraStrumlineNoteView(sustain, data, pending.length, headView);
				pending.push(holdView);
				holdNotes.members.push(holdView);
				previous = sustain;
			}
		}
		pending.sort(compareNotes);
		// Hold views are materialized only when their head enters the active
		// queue.  The temporary list above is not ownership; clear it now.
		holdNotes.clear();
	}

	/** Return whether the adapter still owns any pending or active notes. */
	public function hasPendingNotes():Bool return pending.length > 0
		|| notes.members.length > 0 || holdNotes.members.length > 0;

	/** Generic hit path used by translated donor scripts. */
	public function hitNote(value:Dynamic):Void {
		var view = unwrapView(value);
		if (view == null || view.hitNote || view.missedNote)
			return;
		view.hitNote = true;
		if (view.nativeNote != null) {
			view.nativeNote.wasGoodHit = true;
			view.nativeNote.canBeHit = false;
		}
		markHoldChain(view, true);
		removeActive(view, false);
		hitNotes++;
	}

	/** Generic miss path; it never writes PlayState score or health counters. */
	public function missNote(value:Dynamic):Void {
		var view = unwrapView(value);
		if (view == null || view.hitNote || view.missedNote)
			return;
		view.missedNote = true;
		if (view.nativeNote != null)
			view.nativeNote.tooLate = true;
		markHoldChain(view, false);
		removeActive(view, true);
		missedNotes++;
	}

	/** Process only this adapter's stream. `autoHit` is never global score state. */
	public function processNotes(?autoHit:Bool = false):Int {
		var processed = 0;
		var current = Conductor.songPosition;
		for (view in notes.members.copy()) {
			if (view == null || !view.alive)
				continue;
			var due = view.strumTime <= current;
			if ((autoHit || botplay) && due) {
				hitNote(view);
				processed++;
			} else if (current - view.strumTime > Judge.wayoffJudge) {
				missNote(view);
				processed++;
			}
		}
		return processed;
	}

	/** Remove all owned notes/covers without touching the donor chart. */
	public function clean():Void {
		for (view in pending) disposeView(view);
		for (view in notes.members) disposeView(view);
		for (view in holdNotes.members) disposeView(view);
		pending.resize(0);
		notes.clear();
		holdNotes.clear();
		if (noteHoldCovers != null) {
			// Covers are added as adapter children when they first play. Clearing
			// the pooled group alone would leave those children rendered after a
			// retry, so detach the same owned sprites before resetting the pool.
			for (cover in noteHoldCovers.members.copy()) {
				if (cover != null && members.indexOf(cover) >= 0)
					remove(cover, true);
				if (cover != null)
					cover.kill();
			}
			noteHoldCovers.clear();
		}
		removeRenderedNotes();
	}

	/** Hide the current stream before the retry cleanup removes its ownership. */
	public function vwooshNotes():Void {
		for (view in pending) if (view != null && view.nativeNote != null) view.nativeNote.alpha = 0;
		for (view in notes.members) if (view != null && view.nativeNote != null) view.nativeNote.alpha = 0;
		for (view in holdNotes.members) if (view != null && view.nativeNote != null) view.nativeNote.alpha = 0;
	}

	/** Drop notes that a retry/seek skipped, but retain future pending notes. */
	public function handleSkippedNotes():Int {
		var cutoff = Conductor.songPosition - Judge.wayoffJudge;
		var dropped = 0;
		for (view in pending.copy()) {
			if (view != null && view.strumTime < cutoff) {
				pending.remove(view);
				disposeView(view);
				dropped++;
			}
		}
		for (view in notes.members.copy()) {
			if (view != null && view.strumTime < cutoff) {
				missNote(view);
				dropped++;
			}
		}
		for (view in holdNotes.members.copy())
			if (view != null && view.strumTime < cutoff) {
				holdNotes.members.remove(view);
				disposeView(view);
				dropped++;
			}
		skippedNotes += dropped;
		return dropped;
	}

	public function playNoteHoldCover(holdNote:Dynamic):Void {
		var view = unwrapView(holdNote);
		if (view == null)
			return;
		receptors.playNoteHoldCover(view.nativeNote);
		if (noteHoldCovers == null)
			return;
		for (cover in noteHoldCovers.members)
			if (cover != null && members.indexOf(cover) < 0)
				add(cover);
	}

	public function endNoteHoldCover(holdNote:Dynamic):Void {
		var view = unwrapView(holdNote);
		if (view != null) receptors.endNoteHoldCover(view.nativeNote);
	}

	public function endNoteHoldCoverAtLane(lane:Int):Void receptors.endNoteHoldCoverAtLane(lane);

	override public function update(elapsed:Float):Void {
		spawnPending();
		super.update(elapsed);
		positionNotes();
		if (botplay)
			processNotes(true);
	}

	override public function destroy():Void {
		clean();
		onNoteIncoming.reset();
		super.destroy();
	}

	function spawnPending():Void {
		var lookahead = Math.max(500, 1500 / Math.max(0.1, scrollSpeed));
		while (pending.length > 0 && pending[0].strumTime - Conductor.songPosition < lookahead) {
			var view = pending.shift();
			if (view == null || view.nativeNote == null || !view.nativeNote.alive)
				continue;
			if (view.isSustainNote)
				holdNotes.members.push(view);
			else
				notes.members.push(view);
			add(view.nativeNote);
			rendered.push(view.nativeNote);
			onNoteIncoming.dispatch(view);
			if (!view.alive) {
				if (view.isSustainNote) holdNotes.members.remove(view); else notes.members.remove(view);
				disposeView(view);
			}
		}
	}

	function positionNotes():Void {
		var downscroll = OptionsHandler.options != null && OptionsHandler.options.downscroll;
		for (view in notes.members.concat(holdNotes.members)) {
			if (view == null || view.nativeNote == null || !view.alive)
				continue;
			var lane = view.noteData.getDirection();
			if (lane < 0 || lane >= receptors.members.length)
				continue;
			var receptor = receptors.members[lane];
			view.nativeNote.x = receptor.x + (receptor.width - view.nativeNote.width) / 2;
			var delta = 0.45 * (Conductor.songPosition - view.strumTime) * scrollSpeed;
			view.nativeNote.y = downscroll ? receptor.y + delta : receptor.y - delta;
		}
	}

	function removeActive(view:ExtraStrumlineNoteView, missed:Bool):Void {
		if (view.isSustainNote)
			holdNotes.members.remove(view);
		else
			notes.members.remove(view);
		if (!view.isSustainNote || missed)
			if (view.nativeNote != null) view.nativeNote.kill();
	}

	function markHoldChain(view:ExtraStrumlineNoteView, hit:Bool):Void {
		if (view == null || view.isSustainNote)
			return;
		for (hold in pending.copy().concat(holdNotes.members.copy())) {
			if (hold == null || hold.holdHead != view)
				continue;
			if (hit) {
				hold.hitNote = true;
				if (hold.nativeNote != null)
					hold.nativeNote.wasGoodHit = true;
			} else {
				hold.missedNote = true;
				if (hold.nativeNote != null)
					hold.nativeNote.tooLate = true;
			}
		}
	}

	function disposeView(view:ExtraStrumlineNoteView):Void {
		if (view == null || view.nativeNote == null)
			return;
		if (rendered.indexOf(view.nativeNote) >= 0)
			rendered.remove(view.nativeNote);
		if (members.indexOf(view.nativeNote) >= 0)
			remove(view.nativeNote, true);
		if (view.nativeNote.exists)
			view.nativeNote.kill();
	}

	function removeRenderedNotes():Void {
		for (sprite in rendered.copy()) {
			if (sprite != null && members.indexOf(sprite) >= 0)
				remove(sprite, true);
		}
		rendered.resize(0);
	}

	function configureNote(note:Note, data:CompatSongNoteData, sustain:Bool):Void {
		note.mustPress = data.getStrumlineIndex() == 0;
		note.oppMode = false;
		note.funnyMode = false;
		note.sourceKind = data.kind == '' ? null : data.kind;
		// Foreign HXC processing checks `holdNote.sustainLength` before
		// processing sustain callbacks. Keep the authored hold length on each
		// segment so an imported hold cannot silently become a tap.
		note.sustainLength = sustain
			? Math.max(0, data.length - (note.strumTime - data.strumTime))
			: data.length;
		note.scrollFactor.set();
	}

	function sustainPieces(length:Float):Int {
		var step = Conductor.stepCrochet;
		if (length <= 0 || Math.isNaN(length) || step <= 0)
			return 0;
		return Std.int(Math.ceil((length - 0.0001) / step));
	}

	static function compareNotes(a:ExtraStrumlineNoteView, b:ExtraStrumlineNoteView):Int {
		return a.strumTime < b.strumTime ? -1 : a.strumTime > b.strumTime ? 1 : 0;
	}

	static function unwrapView(value:Dynamic):ExtraStrumlineNoteView {
		if (value == null)
			return null;
		if (Std.isOfType(value, ExtraStrumlineNoteView))
			return cast value;
		var native = NoteHoldCoverCompat.unwrap(value);
		if (native == null)
			return null;
		return null;
	}

	static function resolveStyleId(style:Dynamic):String {
		if (style == null)
			return 'normal';
		var value = Reflect.field(style, 'id');
		if (value == null)
			value = Reflect.field(style, 'name');
		var result = value == null ? 'normal' : StringTools.trim(Std.string(value));
		return result == '' ? 'normal' : result;
	}

	/** Wrap native chart data without retaining a reference to donor objects. */
	public static function chartView(chart:Dynamic):Dynamic {
		return chart == null ? null : new CompatSongDifficultyView(chart);
	}
}

/** Bounded class alias used by HXC's NoteStyleRegistry lookup. */
class ExtraStrumlineNoteStyleRegistry {
	public static var instance:ExtraStrumlineNoteStyleRegistry = new ExtraStrumlineNoteStyleRegistry();
	public function new() {}
	public function fetchEntry(id:Dynamic):Dynamic {
		var value = id == null ? 'normal' : StringTools.trim(Std.string(id));
		return {id: value == '' ? 'normal' : value};
	}
}

/** Native equivalent of the small GRhythmUtil result consumed by DokiDoggle. */
class ExtraStrumlineRhythm {
	public static function processWindow(note:Dynamic, player:Bool = false):Dynamic {
		var native:Dynamic = note;
		if (note != null && Reflect.hasField(note, 'nativeNote'))
			native = Reflect.field(note, 'nativeNote');
		var time:Dynamic = note == null ? null : Reflect.field(note, 'strumTime');
		if (time == null && native != null)
			time = Reflect.field(native, 'strumTime');
		var strumTime = time == null ? 0 : Std.parseFloat(Std.string(time));
		var signedDiff = Conductor.songPosition - strumTime;
		var due = !Math.isNaN(strumTime) && signedDiff >= 0;
		var canBeHit = !Math.isNaN(strumTime)
			&& Math.abs(signedDiff) < Judge.wayoffJudge;
		return {
			botplayHit: due && !player,
			canBeHit: canBeHit,
			tooLate: !Math.isNaN(strumTime) && signedDiff > Judge.wayoffJudge
		};
	}
}
