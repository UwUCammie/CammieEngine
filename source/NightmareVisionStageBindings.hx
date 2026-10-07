package;

import flixel.FlxSprite;
import NightmareVisionStageOwner.NightmareVisionStageBopper;

/** Real source Stage construction uses the caller's class scope and paths. */
class NightmareVisionStageBindings {
	public static function owner(interp:NightmareVisionScriptInterp, paths:NightmareVisionPaths,
		antialiasing:Void->Bool, fromFile:(String, Null<Map<String, Dynamic>>)->NightmareVisionScriptModule):NightmareVisionStageOwner {
		var classes = interp.sourceClassScope().captureClassMap();
		var factories = interp.captureSourceConstructors();
		var lease = NightmareVisionSpriteRegistry.capture(paths);
		var selected:NightmareVisionStageOwner = null;
		selected = {
			paths:paths,
			requireActive:lease.requireActive,
			stageFile:function(name) {lease.requireActive(); return cast NightmareVisionStageData.load(paths.root, name);},
			template:function() return cast NightmareVisionStageData.getTemplateStageFile(),
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
			scriptPath:function(logical) {lease.requireActive(); return NightmareVisionScriptBindings.getPath(logical, paths);},
			scriptExists:paths.exists,
			fromFile:function(path, shared) {lease.requireActive(); return fromFile(path, shared);},
			bopper:characterOperations
		};
		return selected;
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
		interp.variables.set('Stage', NightmareVisionStage);
		interp.bindImport('funkin.objects.Stage', NightmareVisionStage);
		interp.sourceClassScope().bindRuntimeClass('funkin.objects.Stage', NightmareVisionStage);
		var selected = owner(interp, paths, antialiasing, fromFile);
		interp.bindConstructorFactory(NightmareVisionStage, function(args) {
			return new NightmareVisionStage(args.length > 0 ? args[0] : 'stage', selected);
		}, null);
	}
}
