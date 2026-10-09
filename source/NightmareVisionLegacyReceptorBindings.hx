package;

/** Historical PlayState pointers stay stable when source field IDs/order change. */
class NightmareVisionLegacyReceptorBindings {
	public static function install(interp:NightmareVisionScriptInterp, state:Dynamic, refs:NightmareVisionLegacyReceptors,
		fields:Void->Array<NightmareVisionPlayFieldView>):Void {
		var target = function() return state;
		for (name in ['playerStrums','opponentStrums','strumLineNotes']) {
			bind(interp, state, name, function() return refs.readProperty(name, fields()),
				name == 'strumLineNotes' ? null : function(value) return refs.writeProperty(name, value), target);
		}
	}
	static function bind(interp:NightmareVisionScriptInterp, state:Dynamic, name:String,
		read:Void->Dynamic, write:Dynamic->Dynamic, target:Void->Dynamic):Void {
		interp.bindLiveValue(name, read, write, target);
		// Reflect.field/getProperty use the same source pointer as ordinary syntax.
		interp.sourceClassScope().bindStaticField(state, name, read, write == null
			? function(_:Dynamic):Dynamic throw '[nightmare-vision-script] Read-only source property: ' + name : write);
	}
}
