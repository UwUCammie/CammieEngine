package;

/** Psych 1.0.4's live index cursor, with explicit non-hang guards for invalid slots. */
class PsychNoteIteration {
	var active:Bool = false;

	public function new() {}

	public function run(owner:PlayState, callback:Note->Void):Void {
		if (active) throw 'Psych note iteration cannot reenter an active pass';
		active = true;
		try {
			var index = 0;
			// Read the live group and length each time, as the donor does. Raw array
			// push does not extend group.length; add/insert and explicit length writes do.
			while (owner.notes != null && owner.notes.members != null
				&& index < owner.notes.length && index < owner.notes.members.length) {
				var note = owner.notes.members[index];
				// The donor stalls on a null slot or an unremoved dead entry. Skip those
				// invalid slots rather than hanging the game; do not cap finite additions.
				if (note == null || !note.exists) {
					index++;
					continue;
				}
				callback(note);
				// kill/remove retirement leaves the shifted next note at this index.
				// A live removal or reorder instead retains the donor's cursor effects.
				if (note.exists) index++;
			}
		} catch (error:Dynamic) {
			active = false;
			throw error;
		}
		active = false;
	}
}
