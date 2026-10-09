package;

/** Source-version singing decisions; native characters still own playback and rendering. */
class NightmareVisionLegacySinging {
	public static function sing(note:Note, owner:Character, gf:Character, player:Bool,
		animations:Array<String>, rows:Array<Array<Array<Note>>>, ghostsAllowed:Bool,
		sectionAlt:Null<Bool>, onGhost:(String, Note)->Dynamic):Void {
		var name = animations[Std.int(Math.abs(note.noteData))];
		if (player) {
			if (note.noAnimation) return;
			var suffix = note.noteType == 'Alt Animation' ? '-alt' : '';
			if (note.forceGfSing) {
				if (gf != null) { gf.playAnim(name + suffix, true); gf.holdTimer = 0; }
			} else if (owner != null && owner.animTimer <= 0 && !owner.voicelining) {
				owner.holdTimer = 0;
				animate(note, owner, true, name, suffix, animations, rows, ghostsAllowed, onGhost);
			}
			if (note.noteType == 'Hey!') {
				if (owner != null && owner.animTimer <= 0 && !owner.voicelining) special(owner, 'hey');
				special(gf, 'cheer');
			}
		} else {
			var actor = note.forceGfSing ? gf : owner;
			if (actor == null) return;
			if (note.noteType == 'Hey!' && actor.animOffsets.exists('hey')) special(actor, 'hey');
			else if (!note.noAnimation) {
				var suffix = sectionAlt != null && (sectionAlt || note.noteType == 'Alt Animation') ? '-alt' : '';
				actor.voicelining = false;
				actor.holdTimer = 0;
				animate(note, actor, false, name, suffix, animations, rows, ghostsAllowed, onGhost);
			}
		}
	}

	static function special(actor:Character, name:String):Void {
		if (actor == null || !actor.animOffsets.exists(name)) return;
		actor.playAnim(name, true);
		actor.specialAnim = true;
		actor.heyTimer = 0.6;
	}

	static function animate(note:Note, actor:Character, player:Bool, name:String, suffix:String,
		animations:Array<String>, rows:Array<Array<Array<Note>>>, ghostsAllowed:Bool,
		onGhost:(String, Note)->Dynamic):Void {
		var side = player && note.forceGfSing ? 2 : note.mustPress ? 0 : 1;
		var sideRows = rows == null ? null : rows[side];
		var chord = sideRows == null ? null : sideRows[note.row];
		if (!note.isSustainNote && chord != null && chord.length > 1 && note.noteType != 'Ghost Note' && ghostsAllowed) {
			var first = chord[0];
			var primary = animations[Std.int(Math.abs(first.noteData))] + suffix;
			if (actor.mostRecentRow != note.row) actor.playAnim(primary, true);
			if (player) {
				if (note != first && chord.indexOf(note) != first.noteData)
					actor.playGhostAnim(chord.indexOf(note), name, true);
			} else if (note.nextNote != null && note.prevNote != null) {
				if (note != first && !note.nextNote.isSustainNote && onGhost(name + suffix, note) != 1)
					actor.playGhostAnim(chord.indexOf(note), name + suffix, true);
				else if (note.nextNote.isSustainNote) {
					actor.playAnim(primary, true);
					actor.playGhostAnim(chord.indexOf(note), name + suffix, true);
				}
			}
			actor.mostRecentRow = note.row;
		} else if (note.noteType != 'Ghost Note') actor.playAnim(name + suffix, true);
		else actor.playGhostAnim(note.noteData, player ? name : name + suffix, true);
	}
}
