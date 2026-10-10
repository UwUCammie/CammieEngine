package;

/** Public source argument bindings over disposable native values and sprites. */
@:access(PlayState)
class RuntimeSmokePsychInstanceArguments {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		var old = state.variables;var oldLegacy = state.nightmareVisionLegacyFieldCameras;
		var lua = new LuaCompatInterp();var sprite:flixel.FlxSprite = null;
		var cleanup = function() {
			if (sprite != null) sprite.destroy();
			state.variables = old;state.nightmareVisionLegacyFieldCameras = oldLegacy;lua.variables.clear();
		};
		try {
			state.variables = [];state.nightmareVisionLegacyFieldCameras = false;
			var bag:Dynamic = {rows:[[15]],payload:null};
			state.variables.set('bag',bag);state.variables.set('rows',[[23]]);state.variables.set('health',null);
			new PsychSourceBindings(state).install(lua);new PsychReflectionBindings(state,lua).install();
			lua.execute(new hscript.Parser().parseString('setVar("raw",7);setVar("resolved",instanceArg("bag.rows[0][0]"));setVar("fallback",instanceArg("health"));setVar("classValue",instanceArg("instance.health","states.PlayState"));setVar("delimiter","long_ordinary_text_with_delimiter::health");', '__native_instance_args'));
			check(state.variables.get('raw') == 7 && state.variables.get('resolved') == 23, 'Native scalar and bracket registry precedence');
			check(state.variables.get('fallback') == state.health && state.variables.get('classValue') == state.health && state.variables.get('delimiter') == state.health, 'Null field fallback, class path and source delimiter recognition');
			var marker = SourceScriptReflection.INSTANCE_PREFIX + 'bag.rows[0][0]';
			var input:Array<Dynamic> = [marker,[marker,9]];lua.variables.set('sourceArgs',input);
			lua.execute(new hscript.Parser().parseString('setProperty("bag.payload",sourceArgs,true,true);if(!createInstance("parsedSprite","flixel.FlxSprite",[instanceArg("health"),17]))throw "native constructor arguments";', '__native_recursive_args'));
			sprite = cast state.variables.get('parsedSprite');
			check(bag.payload[0] == 23 && bag.payload[1][0] == 23 && bag.payload[1][1] == 9 && input[0] == marker && input[1][0] == marker, 'Recursive arguments preserve input ownership');
			check(sprite != null && sprite.x == state.health && sprite.y == 17, 'Parsed arguments reach native constructor');
			@:privateAccess RuntimeSmokeHarness.emit('psych_instance_arguments_native_verified',{publicBindings:true,nativeScalars:true,bracketPrecedence:true,nullFallback:true,classPath:true,sourceDelimiter:true,recursiveArguments:true,inputPreserved:true,nativeConstructor:true});
		} catch(error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
