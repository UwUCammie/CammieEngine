package;

import flixel.FlxState;

/**
	Stand-in for a source menu class the engine has no native port of, such as
	StoryMenuState or OptionsState. It is a plain object: `new` on it goes
	through the session's state factory, so a package's stateRedirects still
	apply, and any static field a script writes (OptionsState.onPlayState and
	friends) lives on this one session-owned object instead of a process-wide
	static.
*/
@:keep
class NightmareVisionSourceStateClass {
	public static function make(sourceName:String, construct:Void->FlxState, ?statics:Dynamic):Dynamic {
		if (sourceName == null || sourceName == '' || construct == null)
			throw '[nightmare-vision-state-class] A source state needs a name and a constructor';
		var token:Dynamic = {};
		if (statics != null) for (field in Reflect.fields(statics)) Reflect.setField(token, field, Reflect.field(statics, field));
		Reflect.setField(token, 'sourceName', sourceName);
		// `OptionsState.new` is passed around as a constructor reference.
		Reflect.setField(token, 'new', construct);
		return token;
	}

	public static function construct(token:Dynamic):FlxState {
		var create:Dynamic = token == null ? null : Reflect.field(token, 'new');
		if (!Reflect.isFunction(create)) throw '[nightmare-vision-state-class] Not a source state stand-in';
		return Reflect.callMethod(null, create, []);
	}
}
