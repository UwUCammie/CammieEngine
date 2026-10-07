package;

import hscript.Interp;

/** Installs the pinned Psych Discord callbacks and class API on one owner. */
@:keep
class PsychDiscordBindings {
	static final SOURCE_FIELDS:Array<String> = [
		'isInitialized', 'clientID', 'changePresence', 'changeDiscordClientID',
		'resetClientID', 'updatePresence'
	];

	/** Psych's Lua API is registered as two globals rather than a class import. */
	public static function installLua(interp:Interp, facade:PsychDiscordClient):Void {
		if (interp == null || facade == null)
			throw '[psych-discord] Lua bindings require an interpreter and owner facade';
		interp.variables.set('changeDiscordPresence', function(details:String = 'In the Menus',
			?state:String, ?smallImageKey:String, ?hasStartTimestamp:Bool, ?endTimestamp:Float,
			largeImageKey:String = 'icon'):Void {
			facade.changePresence(details, state, smallImageKey, hasStartTimestamp,
				endTimestamp, largeImageKey);
		});
		interp.variables.set('changeDiscordClientID', function(?newID:String):Void {
			facade.changeDiscordClientID(newID);
		});
	}

	/** Installs the real backend class token and routes its source statics through
	 * this interpreter's native scope to the captured owner facade. */
	public static function install(interp:NightmareVisionScriptInterp,
			facade:PsychDiscordClient):Void {
		if (interp == null || facade == null)
			throw '[psych-discord] Class bindings require an interpreter and owner facade';
		var type:Dynamic = PsychDiscordClient;
		interp.variables.set('DiscordClient', type);
		interp.bindImport('backend.DiscordClient', type);
		installScope(interp.sourceClassScope(), facade);
	}

	/** Installs owner-backed statics for Lua reflection scopes and other source
	 * interpreters that already own a SourceNativeClassScope. */
	public static function installScope(scope:SourceNativeClassScope,
			facade:PsychDiscordClient):Void {
		if (scope == null || facade == null)
			throw '[psych-discord] Class bindings require a native scope and owner facade';
		var type:Dynamic = PsychDiscordClient;
		var guard:Void->Void = function():Void facade.ensureActive();
		for (name in ['backend.DiscordClient', 'DiscordClient']) scope.bindRuntimeClass(name, type);
		scope.bindStaticField(type, 'clientID', function():String {
			guard(); return facade.clientID;
		}, function(value:Dynamic):Dynamic {
			guard(); facade.clientID = cast value; return facade.clientID;
		});
		scope.bindStaticField(type, 'isInitialized', function():Bool {
			guard(); return facade.isInitialized;
		});
		for (name in ['changePresence', 'changeDiscordClientID', 'resetClientID', 'updatePresence']) {
			var field = name;
			scope.bindStaticField(type, field, function():Dynamic {
				guard(); return sourceMethod(facade, field, guard);
			});
		}

		SourceClassFieldDiscovery.install(scope, type, SOURCE_FIELDS);
	}

	static function sourceMethod(facade:PsychDiscordClient, name:String,
			guard:Void->Void):Dynamic {
		return switch (name) {
			case 'changePresence': function(details:String = 'In the Menus', ?state:String,
				?smallImageKey:String, ?hasStartTimestamp:Bool, ?endTimestamp:Float,
				largeImageKey:String = 'icon'):Void {
				guard(); facade.changePresence(details, state, smallImageKey, hasStartTimestamp,
					endTimestamp, largeImageKey);
			};
			case 'changeDiscordClientID': function(?newID:String):Void {
				guard(); facade.changeDiscordClientID(newID);
			};
			case 'resetClientID': function():Void {guard(); facade.resetClientID();};
			case 'updatePresence': function():Void {guard(); facade.updatePresence();};
			default: throw '[psych-discord] Unknown source method binding: ' + name;
		};
	}

}
