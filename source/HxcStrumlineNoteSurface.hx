package;

import haxe.ds.ObjectMap;

/** Source-facing hold state, separate from the native per-step sustain sprites. */
class HxcStrumlineHoldView {
	public var head:Note;
	public var noteData:Dynamic;
	public var hitNote:Bool = false;
	public var missedNote:Bool = false;
	public var handledMiss:Bool = false;
	public var spawned:Bool = false;
	public var player:Bool;
	public var endTime:Float;
	public var alive:Bool = false;
	public var sustainLength:Float = 0;

	public function new(head:Note) {
		this.head = head;
		var source = EngineCompat.hxcNoteView(head);
		noteData = Reflect.field(source, 'noteData');
		player = head.mustPress;
		endTime = head.strumTime + head.sustainLength;
	}

	public function refresh(position:Float):Void {
		alive = spawned && position < endTime;
		sustainLength = Math.max(0, endTime - position);
	}
}

/** Keeps one authored hold alive while native sustain segments are retired. */
class HxcStrumlineNoteSurface {
	var holds:Array<HxcStrumlineHoldView> = [];
	var byHead:ObjectMap<Note, HxcStrumlineHoldView> = new ObjectMap();

	public function new(chartNotes:Array<Note>) {
		if (chartNotes == null) return;
		for (note in chartNotes)
			if (note != null && !note.isSustainNote && note.sustainLength > 0) {
				var view = new HxcStrumlineHoldView(note);
				holds.push(view);
				byHead.set(note, view);
			}
	}

	static function headFor(note:Note):Note {
		var current = note;
		var budget = 8192;
		while (current != null && current.isSustainNote && current.prevNote != null && budget-- > 0)
			current = current.prevNote;
		return current == null || current.isSustainNote ? null : current;
	}

	public function spawn(note:Note):Void {
		if (note == null || note.isSustainNote) return;
		var view = byHead.get(note);
		if (view != null) view.spawned = true;
	}

	public function hit(note:Note):Void {
		var head = headFor(note);
		var view = head == null ? null : byHead.get(head);
		if (view != null) view.hitNote = true;
	}

	public function miss(note:Note):Void {
		var head = headFor(note);
		var view = head == null ? null : byHead.get(head);
		if (view != null) view.missedNote = true;
	}

	/** A donor difficulty swap replaces only one native scored lane. Keep the
	 * opposite lane's authored hold state and discard the removed lane's heads. */
	public function replaceSide(player:Bool, chartNotes:Array<Note>):Void {
		for (view in holds.copy())
			if (view.player == player) {
				holds.remove(view);
				byHead.remove(view.head);
			}
		if (chartNotes == null) return;
		for (note in chartNotes)
			if (note != null && note.mustPress == player && !note.isSustainNote
				&& note.sustainLength > 0) {
				var view = new HxcStrumlineHoldView(note);
				holds.push(view);
				byHead.set(note, view);
			}
	}

	public function holdMembers(player:Bool):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		for (view in holds) {
			view.refresh(Conductor.songPosition);
			if (view.player == player && view.alive)
				result.push(view);
		}
		return result;
	}

	public function noteMembers(player:Bool, active:Array<Note>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (active != null)
			for (note in active)
				if (note != null && note.alive && !note.isSustainNote && note.mustPress == player)
					result.push(EngineCompat.hxcNoteView(note));
		return result;
	}
}
