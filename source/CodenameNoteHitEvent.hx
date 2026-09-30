package;

/** Mutable v1.0.1 note-hit payload. The constructor follows the donor's
 * EventManager.recycle field order so PlayState can pass its native defaults. */
@:keep
class CodenameNoteHitEvent extends CodenameGameEvent {
	public var animCancelled:Bool = false;
	public var strumGlowCancelled:Bool = false;
	public var deleteNote:Bool = true;
	public var unmuteVocals:Bool = true;
	public var enableCamZooming:Bool = true;
	public var autoHitLastSustain:Bool = true;
	public var clipSustain:Bool = true;

	public var misses:Bool = true;
	public var countAsCombo:Bool = true;
	public var countScore:Bool = true;
	public var showRating:Null<Bool> = null;
	public var displayRating:Bool;
	public var displayCombo:Bool;
	public var note:Note;
	public var character(get, set):Character;
	public var characters:Array<Character>;
	public var player:Bool;
	public var noteType:String;
	public var animSuffix:String;
	public var ratingPrefix:String;
	public var ratingSuffix:String;
	public var direction:Int;
	public var score:Int;
	public var accuracy:Null<Float>;
	public var healthGain:Float;
	public var rating:String = 'sick';
	public var showSplash:Bool = false;
	public var numScale:Float = 0.5;
	public var numAntialiasing:Bool = true;
	public var ratingScale:Float = 0.7;
	public var ratingAntialiasing:Bool = true;
	public var forceAnim:Null<Bool> = true;
	public var healthIcon:HealthIcon;

	public function new(misses:Bool = true, countAsCombo:Bool = true, countScore:Bool = true,
		?showRating:Bool, displayRating:Bool = true, displayCombo:Bool = true,
		?note:Note, ?characters:Array<Character>, player:Bool = true, ?noteType:String,
		animSuffix:String = '', ratingPrefix:String = 'game/score/', ratingSuffix:String = '',
		direction:Int = 0, score:Int = 0, ?accuracy:Float, healthGain:Float = 0,
		rating:String = 'sick', showSplash:Bool = false, numScale:Float = 0.5,
		numAntialiasing:Bool = true, ratingScale:Float = 0.7,
		ratingAntialiasing:Bool = true, forceAnim:Null<Bool>, ?healthIcon:HealthIcon) {
		super();
		recycle(misses, countAsCombo, countScore, showRating, displayRating, displayCombo,
			note, characters, player, noteType, animSuffix, ratingPrefix, ratingSuffix,
			direction, score, accuracy, healthGain, rating, showSplash, numScale,
			numAntialiasing, ratingScale, ratingAntialiasing, forceAnim, healthIcon);
	}

	public function recycle(misses:Bool, countAsCombo:Bool, countScore:Bool,
		showRating:Null<Bool>, displayRating:Bool, displayCombo:Bool, note:Note,
		characters:Array<Character>, player:Bool, noteType:String, animSuffix:String,
		ratingPrefix:String, ratingSuffix:String, direction:Int, score:Int,
		accuracy:Null<Float>, healthGain:Float, rating:String, showSplash:Bool,
		numScale:Float, numAntialiasing:Bool, ratingScale:Float,
		ratingAntialiasing:Bool, forceAnim:Null<Bool>, healthIcon:HealthIcon):CodenameNoteHitEvent {
		recycleBase();
		animCancelled = false;
		strumGlowCancelled = false;
		deleteNote = true;
		unmuteVocals = true;
		enableCamZooming = true;
		autoHitLastSustain = true;
		clipSustain = true;
		this.misses = misses;
		this.countAsCombo = countAsCombo;
		this.countScore = countScore;
		this.showRating = showRating;
		this.displayRating = displayRating;
		this.displayCombo = displayCombo;
		this.note = note;
		this.characters = characters;
		this.player = player;
		this.noteType = noteType;
		this.animSuffix = animSuffix;
		this.ratingPrefix = ratingPrefix;
		this.ratingSuffix = ratingSuffix;
		this.direction = direction;
		this.score = score;
		this.accuracy = accuracy;
		this.healthGain = healthGain;
		this.rating = rating;
		this.showSplash = showSplash;
		this.numScale = numScale;
		this.numAntialiasing = numAntialiasing;
		this.ratingScale = ratingScale;
		this.ratingAntialiasing = ratingAntialiasing;
		this.forceAnim = forceAnim;
		this.healthIcon = healthIcon;
		return this;
	}

	public function preventAnim():Void animCancelled = true;
	public function cancelAnim():Void preventAnim();
	public function preventDeletion():Void deleteNote = false;
	public function cancelDeletion():Void preventDeletion();
	public function forceDeletion():Void deleteNote = true;
	public function preventVocalsUnmute():Void unmuteVocals = false;
	public function cancelVocalsUnmute():Void preventVocalsUnmute();
	public function preventVocalsMute():Void unmuteVocals = true;
	public function cancelVocalsMute():Void preventVocalsMute();
	public function preventCamZooming():Void enableCamZooming = false;
	public function cancelCamZooming():Void preventCamZooming();
	public function preventLastSustainHit():Void autoHitLastSustain = false;
	public function cancelLastSustainHit():Void preventLastSustainHit();
	public function preventSustainClip():Void clipSustain = false;
	public function preventStrumGlow():Void strumGlowCancelled = true;
	public function cancelStrumGlow():Void preventStrumGlow();

	function get_character():Character return characters == null || characters.length == 0 ? null : characters[0];
	function set_character(value:Character):Character {
		characters = [value];
		return value;
	}
}
