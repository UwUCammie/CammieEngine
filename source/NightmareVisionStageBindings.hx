package;

import flixel.FlxSprite;
import NightmareVisionStageOwner.NightmareVisionStageBopper;

/** Real source Stage construction uses the caller's class scope and paths. */
class NightmareVisionStageBindings {
	public static function owner(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		antialiasing:Void->Bool, fromFile:(String, Null<Map<String, Dynamic>>)->NightmareVisionScriptModule, legacy:Bool = false):NightmareVisionStageOwner {
		var classes = interp.sourceClassScope().captureClassMap();
		var factories = interp.captureSourceConstructors();
		var lease = NightmareVisionSpriteRegistry.capture(paths);
		var selected:NightmareVisionStageOwner = null;
		selected = {
			paths:paths,
			requireActive:lease.requireActive,
			stageFile:function(name) {lease.requireActive(); return cast (legacy ? NightmareVisionStageData.getLegacyStageFile(paths.root, name) : NightmareVisionStageData.load(paths.root, name));},
			template:function() return cast (legacy ? NightmareVisionStageData.getLegacyTemplateStageFile() : NightmareVisionStageData.getTemplateStageFile()),
			antialiasing:antialiasing,
			resolveClass:function(name) return cast (classes.exists(name) ? classes.get(name) : Type.resolveClass(name)),
			createInstance:function(type:Class<Dynamic>, args:Array<Dynamic>):Dynamic {
				lease.requireActive();
				if (type == NightmareVisionStage) return new NightmareVisionStage(args.length > 0 ? args[0] : 'stage', selected);
				for (factory in factories) if (factory.type == type) return factory.create(args);
				return Type.createInstance(type, args);
			},
			setZIndex:function(object, value) HxcCompatRuntime.setZIndex(object, value),
			setProperty:setNestedProperty,
			warn:function(message) trace('[nightmare-vision-stage] ' + message),
			scriptPath:function(logical) {lease.requireActive(); return legacy ? legacyScriptPath(logical, paths) : NightmareVisionScriptBindings.getPath(logical, paths);},
			scriptExists:paths.exists,
			fromFile:function(path, shared) {lease.requireActive(); return fromFile(path, shared);},
			bopper:characterOperations
		};
		return selected;
	}
	public static function defaultIsLegacy(paths:NightmareVisionPaths):Bool
		return NightmareVisionStageProfile.read(paths.root) == NightmareVisionStageProfile.LEGACY;

	/** Extensions take precedence over owner/core selection in historical Stage. */
	public static function legacyScriptPath(logical:String, paths:NightmareVisionPaths):Null<String> {
		for (extension in ['hx', 'hscript', 'hxs', 'lua']) {
			var path = paths.getPath(logical + '.' + extension, null, true);
			if (paths.exists(path)) return path;
		}
		return null;
	}

	/** Pinned ReflectUtil.setProperty walks dots; bracket segments remain literal. */
	public static function setNestedProperty(object:Dynamic, field:String, value:Dynamic):Void {
		if (field.indexOf('.') < 0) {Reflect.setProperty(object, field, value); return;}
		var fields = field.split('.');
		var property = Reflect.getProperty(object, fields.shift());
		while (fields.length > 1) property = Reflect.getProperty(property, fields.shift());
		Reflect.setProperty(property, fields[0], value);
	}

	static function characterOperations(sprite:FlxSprite):Null<NightmareVisionStageBopper> {
		if (!Std.isOfType(sprite, Character)) return null;
		var character:Character = cast sprite;
		character.enableNightmareVisionStageSprite();
		return {
			loadAtlas:function(path) {character.loadAtlas(path);},
			addAnimByPrefix:character.addAnimByPrefix,
			addAnimByIndices:character.addAnimByIndices,
			addOffset:function(name, x, y) character.addOffset(name, x, y),
			playAnim:function(name) character.playAnim(name)
		};
	}
	public static function install(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		antialiasing:Void->Bool, fromFile:(String, Null<Map<String, Dynamic>>)->NightmareVisionScriptModule):Void {
		interp.variables.set('Stage', defaultIsLegacy(paths) ? NightmareVisionLegacyStage : NightmareVisionStage);
		interp.bindImport('funkin.objects.Stage', NightmareVisionStage);
		interp.sourceClassScope().bindRuntimeClass('funkin.objects.Stage', NightmareVisionStage);
		interp.bindImport('gameObjects.Stage', NightmareVisionLegacyStage);
		interp.sourceClassScope().bindRuntimeClass('gameObjects.Stage', NightmareVisionLegacyStage);
		var selected = owner(interp, paths, antialiasing, fromFile);
		interp.bindConstructorFactory(NightmareVisionStage, function(args) {
			return new NightmareVisionStage(args.length > 0 ? args[0] : 'stage', selected);
		}, null);
		var historical = owner(interp, paths, antialiasing, fromFile, true);
		interp.bindConstructorFactory(NightmareVisionLegacyStage, function(args) {
			return new NightmareVisionLegacyStage(args.length > 0 ? args[0] : 'stage', historical);
		}, null);
	}
}
