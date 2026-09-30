package;

/** Mutable event passed through Codename's pre and post note creation hooks. */
@:keep
class CodenameNoteCreationEvent extends CodenameGameEvent {
	public var note:Note;
	public var strumID:Int;
	public var noteType:String;
	public var noteTypeID:Int;
	public var strumLineID:Int;
	public var mustHit:Bool;
	public var noteSprite:String;
	public var noteScale:Null<Float>;
	public var animSuffix:String;

	public function new(note:Note, strumID:Int, noteType:String, noteTypeID:Int,
		strumLineID:Int, mustHit:Bool, noteSprite:String, animSuffix:String,
		?noteScale:Null<Float>) {
		super();
		this.note = note;
		this.strumID = strumID;
		this.noteType = noteType;
		this.noteTypeID = noteTypeID;
		this.strumLineID = strumLineID;
		this.mustHit = mustHit;
		this.noteSprite = noteSprite;
		this.noteScale = noteScale;
		this.animSuffix = animSuffix == null ? '' : animSuffix;
	}
}
