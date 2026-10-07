package;

import flixel.FlxG;
import haxe.Json;

/** Metadata persists with the selected owner; IO can be rebound between scenes. */
@:keep
class PsychAlphabetContext
{
	public var allLetters:Map<String, Null<PsychAlphabetLetter>>;
	public var loadAlphabetData(default, null):(?String)->Void;
	var owner:Null<PsychAlphabetOwner>;
	var initialized:Bool = false;

	public function new(owner:PsychAlphabetOwner)
	{
		this.owner = owner;
		loadAlphabetData = function(request:String = 'alphabet') loadData(request);
	}

	public function initialize():Void
	{
		if (!initialized) loadAlphabetData();
	}

	public function rebindOwner(owner:PsychAlphabetOwner):Void this.owner = owner;
	public function release():Void owner = null;
	function selected():PsychAlphabetOwner
	{
		if (owner == null) throw '[source-alphabet] Selected owner has been released';
		return owner;
	}
	public function atlas(name:String):flixel.graphics.frames.FlxAtlasFrames return selected().atlas(name);
	public function antialiasing():Bool return selected().antialiasing();

	function loadData(request:String):Void
	{
		var provider = selected();
		var path = provider.getPath('images/$request.json');
		if (!provider.exists(path)) path = provider.getPath('images/alphabet.json');
		initialized = true;
		allLetters = new Map<String, Null<PsychAlphabetLetter>>();
		try {
			var data:Dynamic = Json.parse(provider.text(path));
			if (data.allowed != null && data.allowed.length > 0) {
				for (i in 0...data.allowed.length) {
					var char:String = data.allowed.charAt(i);
					if (char == ' ') continue;
					allLetters.set(char.toLowerCase(), null);
				}
			}
			if (data.characters != null) {
				for (char in Reflect.fields(data.characters)) {
					var letterData = Reflect.field(data.characters, char);
					var character = char.toLowerCase().substr(0, 1);
					if ((letterData.animation != null || letterData.normal != null || letterData.bold != null) && allLetters.exists(character))
						allLetters.set(character, {anim:letterData.animation, offsets:letterData.normal, offsetsBold:letterData.bold});
				}
			}
			trace('Reloaded letters successfully ($path)!');
		} catch (error:Dynamic) {
			FlxG.log.error('Error on loading alphabet data: $error');
			trace('Error on loading alphabet data: $error');
		}
		if (!allLetters.exists('?')) allLetters.set('?', {anim:'question'});
	}
}
