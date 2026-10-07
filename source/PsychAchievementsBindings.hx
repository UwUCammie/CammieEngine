package;

/** Installs Psych's static `backend.Achievements` class identity into one
	interpreter while routing every source field to its captured owner service. */
@:keep
class PsychAchievementsBindings {
	static final SOURCE_FIELDS:Array<String> = [
		'achievements', 'variables', 'achievementsUnlocked', 'showingPopups', 'get_showingPopups',
		'init', 'get', 'exists', 'load', 'save', 'getScore', 'setScore', 'addScore',
		'unlock', 'isUnlocked', 'startPopup', 'createAchievement', 'reloadList'
	];

	public static function install(interp:NightmareVisionScriptInterp,
		achievements:PsychAchievements, requireActive:Void->Void):Void {
		if (interp == null || achievements == null || requireActive == null)
			throw '[psych-achievements] Class bindings require an interpreter, owner service, and guard';
		var type:Dynamic = PsychAchievements;
		interp.variables.set('Achievements', type);
		interp.bindImport('backend.Achievements', type);
		installScope(interp.sourceClassScope(), achievements, requireActive);
	}

	/** Installs the same real source class token in non-Iris source scopes, such
		as Psych Lua class reflection, without creating a second API surface. */
	public static function installScope(scope:SourceNativeClassScope,
		achievements:PsychAchievements, requireActive:Void->Void):Void {
		if (scope == null || achievements == null || requireActive == null)
			throw '[psych-achievements] Class bindings require a scope, owner service, and guard';
		var type:Dynamic = PsychAchievements;
		var guard:Void->Void = function():Void {
			requireActive();
		};
		scope.bindRuntimeClass('backend.Achievements', type);
		scope.bindRuntimeClass('Achievements', type);

		for (name in ['achievements', 'variables', 'achievementsUnlocked']) {
			var field = name;
			scope.bindStaticField(type, field,
				function() {guard(); return Reflect.getProperty(achievements, field);},
				function(value) {
					guard();
					Reflect.setProperty(achievements, field, value);
					return value;
				});
		}
		scope.bindStaticField(type, 'showingPopups', function() {
			guard(); return Reflect.getProperty(achievements, 'showingPopups');
		});
		for (name in ['get_showingPopups', 'init', 'get', 'exists', 'load', 'save', 'getScore',
			'setScore', 'addScore', 'unlock', 'isUnlocked', 'startPopup', 'createAchievement', 'reloadList']) {
			var field = name;
			scope.bindStaticField(type, field, function() {
				guard(); return guardedMethod(achievements, field, guard);
			});
		}

		// Native Reflect/Type do not discover the virtual statics on an owner
		// class token. Wrap the existing scoped operations so other source class
		// adapters already installed on this interpreter remain composable.
		SourceClassFieldDiscovery.install(scope, type, SOURCE_FIELDS);
	}

	static function guardedMethod(service:PsychAchievements, name:String,
		guard:Void->Void):Dynamic {
		return switch (name) {
			case 'get_showingPopups': function() {guard(); return service.showingPopups;};
			case 'init': function() {guard(); return service.init();};
			case 'get': function(name:String) {guard(); return service.get(name);};
			case 'exists': function(name:String) {guard(); return service.exists(name);};
			case 'load': function() {guard(); return service.load();};
			case 'save': function() {guard(); return service.save();};
			case 'getScore': function(name:String) {guard(); return service.getScore(name);};
			case 'setScore': function(name:String, value:Float, saveIfNotUnlocked:Bool = true) {
				guard(); return service.setScore(name, value, saveIfNotUnlocked);
			};
			case 'addScore': function(name:String, value:Float = 1, saveIfNotUnlocked:Bool = true) {
				guard(); return service.addScore(name, value, saveIfNotUnlocked);
			};
			case 'unlock': function(name:String, autoStartPopup:Bool = true) {
				guard(); return service.unlock(name, autoStartPopup);
			};
			case 'isUnlocked': function(name:String) {guard(); return service.isUnlocked(name);};
			case 'startPopup': function(name:String, endFunc:Void->Void = null) {
				guard(); return service.startPopup(name, endFunc);
			};
			case 'createAchievement': function(name:String, info:PsychAchievementInfo, mod:String = null) {
				guard(); return service.createAchievement(name, info, mod);
			};
			case 'reloadList': function() {guard(); return service.reloadList();};
			default: throw '[psych-achievements] Unknown source method binding: ' + name;
		};
	}

}
