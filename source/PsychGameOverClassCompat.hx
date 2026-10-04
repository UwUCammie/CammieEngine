package;

using StringTools;

/** Per-song static GameOverSubstate surface for imported Psych stage classes.
 * The native game-over state reads its settings through PlayState's class
 * property bridge, so source stage writes must reach that same bridge. */
class PsychGameOverClassCompat {
	final host:Dynamic;
	final chart:Dynamic;
	var characterValue:String;
	var deathSoundValue:String;
	var loopSoundValue:String;
	var endSoundValue:String;
	var delayValue:Float = 0;

	public function new(host:Dynamic, chart:Dynamic) {
		this.host = host;
		this.chart = chart;
		characterValue = chartValue('gameOverChar', 'bf-dead');
		deathSoundValue = chartValue('gameOverSound', 'fnf_loss_sfx');
		loopSoundValue = chartValue('gameOverLoop', 'gameOver');
		endSoundValue = chartValue('gameOverEnd', 'gameOverEnd');
	}

	function chartValue(field:String, fallback:String):String {
		var value = chart == null ? null : Reflect.field(chart, field);
		if (value == null) return fallback;
		var name = Std.string(value).trim();
		return name == '' ? fallback : name;
	}

	function write(field:String, value:String):String {
		if (host == null)
			throw '[psych-gameover] A live PlayState is required for ' + field;
		var method = Reflect.field(host, 'setPsychClassProperty');
		if (method == null)
			throw '[psych-gameover] The native class property bridge is unavailable';
		Reflect.callMethod(host, method, ['GameOverSubstate', field, value]);
		return value;
	}

	public var characterName(get, set):String;
	function get_characterName():String return characterValue;
	function set_characterName(value:String):String return characterValue = write('characterName', value);

	public var deathSoundName(get, set):String;
	function get_deathSoundName():String return deathSoundValue;
	function set_deathSoundName(value:String):String return deathSoundValue = write('deathSoundName', value);

	public var loopSoundName(get, set):String;
	function get_loopSoundName():String return loopSoundValue;
	function set_loopSoundName(value:String):String return loopSoundValue = write('loopSoundName', value);

	public var endSoundName(get, set):String;
	function get_endSoundName():String return endSoundValue;
	function set_endSoundName(value:String):String return endSoundValue = write('endSoundName', value);

	public var deathDelay(get, set):Float;
	function get_deathDelay():Float return delayValue;
	function set_deathDelay(value:Float):Float {
		if (Math.isNaN(value) || !Math.isFinite(value) || value < 0)
			throw '[psych-gameover] deathDelay must be a finite nonnegative number';
		write('deathDelay', Std.string(value));
		return delayValue = value;
	}

	public var instance(get, never):Dynamic;
	function get_instance():Dynamic {
		var getter = host == null ? null : Reflect.field(host, 'sourceGameOverInstance');
		return Reflect.isFunction(getter) ? Reflect.callMethod(host, getter, []) : null;
	}

	public function resetVariables():Void {
		characterName = chartValue('gameOverChar', 'bf-dead');
		deathSoundName = chartValue('gameOverSound', 'fnf_loss_sfx');
		loopSoundName = chartValue('gameOverLoop', 'gameOver');
		endSoundName = chartValue('gameOverEnd', 'gameOverEnd');
		deathDelay = 0;
	}
}
