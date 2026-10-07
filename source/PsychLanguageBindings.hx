package;

import hscript.Interp;

/** Source-shaped Language class and translated-Lua callbacks for one owner. */
@:keep
@:access(PsychLanguageRuntime)
class PsychLanguageBindings {
	static final SOURCE_FIELDS:Array<String> = [
		'defaultLangName', 'phrases', 'reloadPhrases', 'getPhrase', 'getFileTranslation'
	];

	public static function install(interp:NightmareVisionScriptInterp,
		runtime:PsychLanguageRuntime):Void {
		if (interp == null || runtime == null)
			throw '[psych-language] HScript bindings require an interpreter and owner runtime';
		var type:Dynamic = PsychLanguageRuntime;
		interp.variables.set('Language', type);
		interp.bindImport('backend.Language', type);
		installScope(interp.sourceClassScope(), runtime);
	}

	/** Install the same real class token for owner-local class reflection routes. */
	public static function installScope(scope:SourceNativeClassScope,
		runtime:PsychLanguageRuntime):Void {
		if (scope == null || runtime == null)
			throw '[psych-language] Class bindings require a source scope and owner runtime';

		var type:Dynamic = PsychLanguageRuntime;
		var guard:Void->Void = function():Void runtime.ensureActive();
		scope.bindRuntimeClass('backend.Language', type);
		scope.bindRuntimeClass('Language', type);

		scope.bindStaticField(type, 'defaultLangName', function() {
			guard();
			return runtime.defaultLangName;
		}, function(value) {
			guard();
			runtime.defaultLangName = cast value;
			return value;
		});
		scope.bindStaticField(type, 'phrases', function() {
			guard();
			return runtime.phrases;
		}, function(value) {
			guard();
			runtime.phrases = cast value;
			return value;
		});
		for (name in ['reloadPhrases', 'getPhrase', 'getFileTranslation']) {
			var field = name;
			scope.bindStaticField(type, field, function() {
				guard();
				return guardedMethod(runtime, field, guard);
			});
		}

		// Compose with existing scoped reflection adapters rather than replacing
		// the interpreter's shared Reflect/Type views.
		SourceClassFieldDiscovery.install(scope, type, SOURCE_FIELDS);
	}

	/** Register the donor's two names directly into one translated Lua scope. */
	public static function installLua(interp:Interp, runtime:PsychLanguageRuntime):Void {
		if (interp == null || runtime == null)
			throw '[psych-language] Lua callbacks require an interpreter and owner runtime';

		interp.variables.set('getTranslationPhrase', function(key:String,
			?defaultPhrase:String, ?values:Array<Dynamic> = null):String {
			return runtime.getPhrase(key, defaultPhrase, values);
		});
		interp.variables.set('getFileTranslation', function(key:String):String {
			return runtime.getFileTranslation(key);
		});
	}

	static function guardedMethod(runtime:PsychLanguageRuntime, name:String,
		guard:Void->Void):Dynamic {
		return switch (name) {
			case 'reloadPhrases': function():Void {guard(); return runtime.reloadPhrases();};
			case 'getPhrase': function(key:String, ?defaultPhrase:String,
				?values:Array<Dynamic> = null):String {guard(); return runtime.getPhrase(key, defaultPhrase, values);};
			case 'getFileTranslation': function(key:String):String {guard(); return runtime.getFileTranslation(key);};
			default: throw '[psych-language] Unknown source method binding: ' + name;
		};
	}

}
