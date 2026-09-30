package;

/** Mutable v1.0.1 note-miss payload in the donor recycle field order. */
@:keep
class CodenameNoteMissEvent extends CodenameGameEvent {
	public var animCancelled:Bool = false;
	public var deleteNote:Bool = true;
	public var stunned:Bool = true;
	public var resetCombo:Bool = true;
	public var playMissSound:Bool = true;

	public var note:Note;
	public var score:Int;
	public var misses:Int;
	public var muteVocals:Bool;
	public var healthGain:Float;
	public var missSound:String;
	public var missVolume:Float;
	public var ghostMiss:Bool;
	public var gfSad:Bool;
	public var gfSadAnim:String;
	public var forceGfAnim:Bool;
	public var forceAnim:Null<Bool>;
	public var animSuffix:String;
	public var character(get, set):Character;
	public var characters:Array<Character>;
	public var playerID:Int;
	public var noteType:String;
	public var direction:Int;
	public var accuracy:Null<Float>;

	public function new(?note:Note, score:Int = -10, misses:Int = 1,
		muteVocals:Bool = true, healthGain:Float = -0.04, missSound:String = '',
		missVolume:Float = 0.1, ghostMiss:Bool = false, gfSad:Bool = false,
		gfSadAnim:String = 'sad', forceGfAnim:Bool = true, ?forceAnim:Bool,
		animSuffix:String = 'miss', ?characters:Array<Character>, playerID:Int = 0,
		?noteType:String, direction:Int = 0, ?accuracy:Float) {
		super();
		recycle(note, score, misses, muteVocals, healthGain, missSound, missVolume,
			ghostMiss, gfSad, gfSadAnim, forceGfAnim, forceAnim, animSuffix,
			characters, playerID, noteType, direction, accuracy);
	}

	public function recycle(note:Note, score:Int, misses:Int, muteVocals:Bool,
		healthGain:Float, missSound:String, missVolume:Float, ghostMiss:Bool,
		gfSad:Bool, gfSadAnim:String, forceGfAnim:Bool, forceAnim:Null<Bool>,
		animSuffix:String, characters:Array<Character>, playerID:Int,
		noteType:String, direction:Int, accuracy:Null<Float>):CodenameNoteMissEvent {
		recycleBase();
		animCancelled = false;
		deleteNote = true;
		stunned = true;
		resetCombo = true;
		playMissSound = true;
		this.note = note;
		this.score = score;
		this.misses = misses;
		this.muteVocals = muteVocals;
		this.healthGain = healthGain;
		this.missSound = missSound;
		this.missVolume = missVolume;
		this.ghostMiss = ghostMiss;
		this.gfSad = gfSad;
		this.gfSadAnim = gfSadAnim;
		this.forceGfAnim = forceGfAnim;
		this.forceAnim = forceAnim;
		this.animSuffix = animSuffix;
		this.characters = characters;
		this.playerID = playerID;
		this.noteType = noteType;
		this.direction = direction;
		this.accuracy = accuracy;
		return this;
	}

	public function preventMissSound():Void playMissSound = false;
	public function cancelMissSound():Void preventMissSound();
	public function preventResetCombo():Void resetCombo = false;
	public function cancelResetCombo():Void preventResetCombo();
	public function preventStunned():Void stunned = false;
	public function cancelStunned():Void preventStunned();
	public function preventAnim():Void animCancelled = true;
	public function cancelAnim():Void preventAnim();
	public function preventDeletion():Void deleteNote = false;
	public function cancelDeletion():Void preventDeletion();
	public function preventVocalsUnmute():Void muteVocals = true;
	public function cancelVocalsUnmute():Void preventVocalsUnmute();
	public function preventVocalsMute():Void muteVocals = false;
	public function cancelVocalsMute():Void preventVocalsMute();

	function get_character():Character return characters == null || characters.length == 0 ? null : characters[0];
	function set_character(value:Character):Character {
		characters = [value];
		return value;
	}
}
