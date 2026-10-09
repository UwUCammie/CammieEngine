package;

import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;

/** Scene integration for distinct source Stage ownership contracts. */
class NightmareVisionStageScene {
	public static function legacy(stage:FlxTypedGroup<FlxBasic>):Bool
		return Std.isOfType(stage, NightmareVisionLegacyStage);

	public static function create(name:String, owner:NightmareVisionStageOwner, historical:Bool):FlxTypedGroup<FlxBasic>
		return historical ? new NightmareVisionLegacyStage(name, owner) : new NightmareVisionStage(name, owner);

	public static function data(stage:FlxTypedGroup<FlxBasic>):Dynamic
		return legacy(stage) ? (cast stage:NightmareVisionLegacyStage).stageData : (cast stage:NightmareVisionStage).stageData;

	public static function foreground(stage:FlxTypedGroup<FlxBasic>):FlxTypedGroup<FlxBasic>
		return legacy(stage) ? (cast stage:NightmareVisionLegacyStage).foreground : null;

	public static function load(stage:FlxTypedGroup<FlxBasic>, group:NightmareVisionScriptGroup):Void {
		if (legacy(stage)) {
			var value:NightmareVisionLegacyStage = cast stage;
			value.buildStage();
			for (script in value.stageScripts) group.addScript(script);
		} else {
			var value:NightmareVisionStage = cast stage;
			value.buildStage();
			if (value.runScript(group)) group.addScript(value.script);
		}
	}

	public static function mount(scene:FlxTypedGroup<FlxBasic>, stage:FlxTypedGroup<FlxBasic>, actors:Array<FlxBasic>):Void {
		scene.add(stage);
		var parent = legacy(stage) ? scene : stage;
		for (actor in actors) parent.add(actor);
		var front = foreground(stage);
		if (front != null) scene.add(front);
	}

	public static function insertBehind(scene:FlxTypedGroup<FlxBasic>, stage:FlxTypedGroup<FlxBasic>,
		actor:FlxBasic, object:FlxBasic):Void {
		var parent = legacy(stage) ? scene : stage;
		parent.insert(parent.members.indexOf(actor), object);
	}

	public static function releaseScripts(stage:FlxTypedGroup<FlxBasic>, group:NightmareVisionScriptGroup):Void {
		if (stage == null) return;
		var modules = legacy(stage) ? (cast stage:NightmareVisionLegacyStage).stageScripts.copy()
			: [(cast stage:NightmareVisionStage).script];
		for (script in modules) if (script != null && group.removeScript(script)) {
			if (script.exists('onDestroy')) script.call('onDestroy');
			script.destroy();
		}
	}
}
