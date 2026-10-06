package;

/** Owner-local source NoteUtil skin list and resolver; other NoteUtil APIs are separate. */
@:keep
class NightmareVisionNoteSkinRegistry {
	public var noteskins:Array<NightmareVisionNoteSkin> = [];
	var createDefault:Void->NightmareVisionNoteSkin;
	public function new(createDefault:Void->NightmareVisionNoteSkin) this.createDefault = createDefault;
	public function getSkinFromID(id:Int = 0):NightmareVisionNoteSkin {
		for (skin in noteskins) if (skin.ID == id) return skin;
		var first = noteskins[0];
		return first == null ? createDefault() : first;
	}
	public function destroy():Void {
		if (noteskins != null) noteskins.resize(0);
		createDefault = null;
	}
}
