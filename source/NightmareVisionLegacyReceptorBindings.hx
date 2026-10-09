package;

/** Historical PlayState pointers stay stable when source field IDs/order change. */
class NightmareVisionLegacyReceptorBindings {
	public static function install(interp:NightmareVisionScriptInterp, state:Dynamic, refs:NightmareVisionLegacyReceptors,
		fields:Void->Array<NightmareVisionPlayFieldView>):Void {
		var target = function() return state;
		bind(interp, state, 'playerStrums', function() return refs.player, function(value) return refs.player = cast value, target);
		bind(interp, state, 'opponentStrums', function() return refs.opponent, function(value) return refs.opponent = cast value, target);
		bind(interp, state, 'strumLineNotes', function():Dynamic {
			var notes:Array<Dynamic> = [];
			var collection = fields();
			if (collection != null) for (field in collection) for (note in field.members) notes.push(note);
			return notes;
		}, null, target);
	}
	static function bind(interp:NightmareVisionScriptInterp, state:Dynamic, name:String,
		read:Void->Dynamic, write:Dynamic->Dynamic, target:Void->Dynamic):Void {
		interp.bindLiveValue(name, read, write, target);
		// Reflect.field/getProperty use the same source pointer as ordinary syntax.
		interp.sourceClassScope().bindStaticField(state, name, read, write == null
			? function(_:Dynamic):Dynamic throw '[nightmare-vision-script] Read-only source property: ' + name : write);
	}
}
