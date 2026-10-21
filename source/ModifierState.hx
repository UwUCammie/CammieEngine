package;

import flixel.FlxG;
using StringTools;

typedef TModifierNoName = {
	var value:Bool;
	var conflicts:Array<String>;
	var multi:Float;
	var ?times:Null<Bool>;
	var desc:String;
	var ?amount:Null<Float>;
	var ?defAmount:Null<Float>;
	var ?precision:Null<Float>;
	var ?minimum:Null<Float>;
	var ?maximum:Null<Float>;
	// used for things that give you points in both directions
	var ?absolute:Null<Bool>;
}
typedef TModifier = {
	> TModifierNoName,
	var name:String;
	var internName:String;
	/** Section of the modifiers panel: Rules, Visual, Health or Play style. */
	var ?group:String;
}

/**
	The gameplay modifiers: what each one is, which ones are on, and the
	standardised score multiplier they make. PlayState and scripts read the
	switches through `namedModifiers`; the choices are made in
	ModifierMenuSubState, opened from Freeplay and Story mode (F2) or as this
	song setup screen (from the pause menu and character select).

	Modifiers never switch each other off. A modifier that clashes with one that
	is on is shown as unavailable, with the reason, until that one is turned off.
**/
class ModifierState extends MusicBeatState {
	public static inline var RULES:String = 'Rules';
	public static inline var VISUAL:String = 'Visual';
	public static inline var HEALTH:String = 'Health';
	public static inline var PLAY_STYLE:String = 'Play style';
	public static final GROUPS:Array<String> = [RULES, VISUAL, HEALTH, PLAY_STYLE];

	static final FAIL_RULES:Array<String> = ['mfc', 'gfc', 'fc'];
	static final HEALTH_IDS:Array<String> = ['healthloss', 'healthgain', 'regen', 'degen', 'poison'];
	static final PLAYERS:Array<String> = ['nos', 'duo', 'oppnt', 'demo'];

	public static var modifiers:Array<TModifier> = [
		{
			name: "Sicks Only",
			internName: "mfc",
			group: RULES,
			value: false,
			conflicts: ["gfc", "fc", "practice", "healthloss", "healthgain", "regen", "degen", "poison", "duo", "demo"],
			multi: StandardScore.multiplierOf("mfc"),
			desc: "Anything worse than a Sick ends the song."
		},
		{
			name: "Goods or Better",
			internName: "gfc",
			group: RULES,
			value: false,
			conflicts: ["mfc", "fc", "practice", "healthloss", "healthgain", "regen", "degen", "poison", "duo", "demo"],
			multi: StandardScore.multiplierOf("gfc"),
			desc: "Anything worse than a Good ends the song."
		},
		{
			name: "Full Combo",
			internName: "fc",
			group: RULES,
			value: false,
			conflicts: ["mfc", "gfc", "practice", "healthloss", "healthgain", "regen", "degen", "poison", "duo", "demo"],
			multi: StandardScore.multiplierOf("fc"),
			desc: "A single miss ends the song."
		},
		{
			name: "Practice",
			internName: "practice",
			group: RULES,
			value: false,
			conflicts: ["mfc", "gfc", "fc", "duo", "demo", "loop"],
			multi: StandardScore.multiplierOf("practice"),
			desc: "You cannot die. The score is not saved."
		},
		{
			name: "Restart on Death",
			internName: "loop",
			group: RULES,
			value: false,
			conflicts: ["practice"],
			multi: StandardScore.multiplierOf("loop"),
			desc: "The song restarts right away when you die."
		},
		{
			name: "Flipped Notes",
			internName: "flipped",
			group: VISUAL,
			value: false,
			conflicts: ["invis"],
			multi: StandardScore.multiplierOf("flipped"),
			desc: "Notes are drawn upside down."
		},
		{
			name: "Vanishing Notes",
			internName: "vanish",
			group: VISUAL,
			value: false,
			conflicts: ["invis"],
			multi: StandardScore.multiplierOf("vanish"),
			desc: "Notes fade out as they get close to the receptors."
		},
		{
			name: "Invisible Notes",
			internName: "invis",
			group: VISUAL,
			value: false,
			conflicts: ["flipped", "vanish", "snake", "drunk"],
			multi: StandardScore.multiplierOf("invis"),
			desc: "Notes cannot be seen at all."
		},
		{
			name: "Snake Notes",
			internName: "snake",
			group: VISUAL,
			value: false,
			conflicts: ["invis"],
			multi: StandardScore.multiplierOf("snake"),
			desc: "Notes sway from side to side as they scroll."
		},
		{
			name: "Drunk Notes",
			internName: "drunk",
			group: VISUAL,
			value: false,
			conflicts: ["invis"],
			multi: StandardScore.multiplierOf("drunk"),
			desc: "Notes wobble on their way to the receptors."
		},
		{
			name: "Health Loss",
			internName: "healthloss",
			group: HEALTH,
			value: false,
			conflicts: ["mfc", "fc", "gfc"],
			multi: StandardScore.multiplierOf("healthloss"),
			amount: 1,
			defAmount: 1,
			precision: 0.5,
			minimum: 0,
			maximum: 10,
			desc: "How much health a miss costs, as a multiple of normal."
		},
		{
			name: "Health Gain",
			internName: "healthgain",
			group: HEALTH,
			value: false,
			conflicts: ["mfc", "fc", "gfc"],
			multi: StandardScore.multiplierOf("healthgain"),
			amount: 1,
			defAmount: 1,
			precision: 0.5,
			minimum: 0,
			maximum: 10,
			desc: "How much health a hit gives, as a multiple of normal."
		},
		{
			name: "Health Regen",
			internName: "regen",
			group: HEALTH,
			value: false,
			conflicts: ["fc", "mfc", "gfc", "degen", "duo", "demo"],
			multi: StandardScore.multiplierOf("regen"),
			amount: 0,
			defAmount: 0,
			precision: 5,
			minimum: 0,
			maximum: 500,
			desc: "Health slowly refills over time."
		},
		{
			name: "Health Drain",
			internName: "degen",
			group: HEALTH,
			value: false,
			conflicts: ["fc", "mfc", "gfc", "regen", "duo", "demo"],
			multi: StandardScore.multiplierOf("degen"),
			amount: 0,
			defAmount: 0,
			precision: 5,
			minimum: 0,
			maximum: 500,
			desc: "Health slowly drains over time."
		},
		{
			name: "Fragile",
			internName: "poison",
			group: HEALTH,
			value: false,
			conflicts: ["fc", "mfc", "gfc", "duo", "demo"],
			multi: StandardScore.multiplierOf("poison"),
			desc: "Every miss costs a lot of health."
		},
		{
			name: "Play Both Sides",
			internName: "nos",
			group: PLAY_STYLE,
			value: false,
			conflicts: ["oppnt", "duo", "demo"],
			multi: StandardScore.multiplierOf("nos"),
			desc: "You play the opponent's notes too. The score is not saved."
		},
		{
			name: "Two Players",
			internName: "duo",
			group: PLAY_STYLE,
			value: false,
			conflicts: ["mfc", "fc", "gfc", "practice", "healthloss", "regen", "degen", "poison", "oppnt", "demo", "nos"],
			multi: StandardScore.multiplierOf("duo"),
			desc: "A second player takes the opponent's side. The score is not saved."
		},
		{
			name: "Opponent Play",
			internName: "oppnt",
			group: PLAY_STYLE,
			value: false,
			conflicts: ["duo", "demo", "nos"],
			multi: StandardScore.multiplierOf("oppnt"),
			desc: "Play as the opponent. The score is not saved."
		},
		{
			name: "Autoplay",
			internName: "demo",
			group: PLAY_STYLE,
			value: false,
			conflicts: ["mfc", "fc", "gfc", "practice", "healthloss", "regen", "degen", "poison", "oppnt", "duo", "nos"],
			multi: StandardScore.multiplierOf("demo"),
			desc: "The game plays the song by itself. The score is not saved."
		}
	];

	/**
		Modifiers that no longer exist. Speed changes moved to the scroll speed
		option; the old menu's Play and Char Select rows are now keys. They stay
		readable (always off) because PlayState and older scripts look them up.
	**/
	static final RETIRED:Array<String> = ['slow', 'fast', 'accel', 'play', 'charselect', 'antijank', 'chart'];

	public static var isStoryMode:Bool = false;
	public static var scoreMultiplier:Float = 1;
	public static var namedModifiers:Dynamic = {};

	public static function init() {
		for (id in RETIRED)
			if (!Reflect.hasField(namedModifiers, id))
				Reflect.setField(namedModifiers, id, {name: id, internName: id, value: false, conflicts: [], multi: 1.0, desc: ''});
		for (modifier in modifiers)
			Reflect.setField(namedModifiers, modifier.internName, modifier);
	}

	public static function find(id:String):Null<TModifier> {
		for (modifier in modifiers)
			if (modifier.internName == id)
				return modifier;
		return null;
	}

	/** The name of a modifier that is on and clashes with `id`, or null when `id` can be turned on. */
	public static function blockedBy(id:String):Null<String> {
		var target = find(id);
		for (modifier in modifiers) {
			if (!modifier.value || modifier.internName == id)
				continue;
			if (modifier.conflicts.indexOf(id) >= 0 || (target != null && target.conflicts.indexOf(modifier.internName) >= 0))
				return modifier.name;
		}
		return null;
	}

	/** Turn a modifier on or off. Turning on a blocked one does nothing and returns false. */
	public static function setOn(id:String, on:Bool):Bool {
		var modifier = find(id);
		if (modifier == null)
			return false;
		if (on && blockedBy(id) != null)
			return false;
		modifier.value = on;
		if (modifier.amount != null) {
			if (!on)
				modifier.amount = modifier.defAmount;
			else if (modifier.amount == modifier.defAmount)
				modifier.amount = stepAmount(modifier, true);
		}
		refreshScoreMultiplier();
		return true;
	}

	/** Step a numeric modifier. It is on exactly while its amount is away from the default. */
	public static function changeAmount(id:String, increase:Bool):Bool {
		var modifier = find(id);
		if (modifier == null || modifier.amount == null)
			return false;
		var next = stepAmount(modifier, increase);
		if (next == modifier.amount)
			return false;
		var on = next != modifier.defAmount;
		if (on && !modifier.value && blockedBy(id) != null)
			return false;
		modifier.amount = next;
		modifier.value = on;
		refreshScoreMultiplier();
		return true;
	}

	static function stepAmount(modifier:TModifier, increase:Bool):Float {
		var step = modifier.precision == null ? 1.0 : modifier.precision;
		var next = modifier.amount + (increase ? step : -step);
		if (modifier.minimum != null && next < modifier.minimum)
			next = modifier.minimum;
		if (modifier.maximum != null && next > modifier.maximum)
			next = modifier.maximum;
		// Steps are halves or whole numbers; drop float noise so equality with the default holds.
		return Math.round(next * 1000) / 1000;
	}

	public static function resetAll():Void {
		for (modifier in modifiers) {
			modifier.value = false;
			if (modifier.amount != null)
				modifier.amount = modifier.defAmount;
		}
		refreshScoreMultiplier();
	}

	/** Internal names of the modifiers that are switched on. `applied` is kept for older callers. */
	public static function modifierIds(applied:Bool = true):Array<String> {
		var ids:Array<String> = [];
		for (modifier in modifiers)
			if (modifier.value)
				ids.push(modifier.internName);
		return ids;
	}

	/** The multiplier a play starting now uses, also stored in `scoreMultiplier`. */
	public static function refreshScoreMultiplier():Float {
		scoreMultiplier = StandardScore.multiplierFor(modifierIds(true));
		return scoreMultiplier;
	}

	public static function unrankedActive():Bool
		return StandardScore.isUnranked(modifierIds(false));

	/** Detached copy of the switches, for storing with a score. */
	public static function snapshot():Dynamic {
		var copy:Dynamic = {};
		for (modifier in modifiers)
			Reflect.setField(copy, modifier.internName, {value: modifier.value, amount: modifier.amount});
		return copy;
	}

	/** Put back switches saved by snapshot(), e.g. after a multiplayer match fixed them. */
	public static function restore(saved:Dynamic):Void {
		if (saved == null)
			return;
		for (modifier in modifiers) {
			var entry:Dynamic = Reflect.field(saved, modifier.internName);
			if (entry == null)
				continue;
			modifier.value = entry.value == true;
			if (modifier.amount != null && entry.amount != null)
				modifier.amount = entry.amount;
		}
		refreshScoreMultiplier();
	}

	/** The score line under the panel: the multiplier, or why nothing is saved. */
	public static function multiplierLabel():String {
		if (unrankedActive())
			return 'Unranked: the score will not be saved';
		var value = Math.round(refreshScoreMultiplier() * 100) / 100;
		var text = Std.string(value);
		if (text.indexOf('.') < 0)
			text += '.00';
		else if (text.length - text.indexOf('.') == 2)
			text += '0';
		return 'Score x' + text;
	}

	/** The song setup screen: the modifiers panel with a Start song row, over the menu background. */
	override function create() {
		MenuWidgets.background(this);
		super.create();
		persistentUpdate = false;
		openPanel();
	}

	function openPanel():Void {
		var panel = new ModifierMenuSubState(true);
		panel.onStart = startSong;
		panel.onBack = leave;
		openSubState(panel);
	}

	function startSong():Void {
		if (FlxG.sound.music != null)
			FlxG.sound.music.stop();
		LoadingState.loadAndSwitchState(new PlayState());
	}

	function leave():Void {
		if (isStoryMode)
			LoadingState.loadAndSwitchState(new StoryMenuState());
		else
			LoadingState.loadAndSwitchState(new FreeplayState());
	}
}
