package;

import flixel.FlxG;
import flixel.FlxState;
import hscript.Interp;
import PsychAchievementPopup.PsychAchievementPopupAssets;

/** One source achievement runtime per authenticated Psych import, shared by
 * Lua, plain HScript and embedded HScript rather than by script file. */
@:access(PlayState)
class PsychAchievementsIntegration {
	static var leaseInstalled:Bool = false;

	public static function installHscript(host:PlayState, interp:Interp, origin:String):Void {
		if (!Std.isOfType(interp, SourceIrisBridge)) return;
		var runtime = runtimeFor(host, interp.variables.get('Paths'), origin);
		if (runtime == null) return;
		PsychAchievementsBindings.install((cast interp:SourceIrisBridge).evaluator,
			runtime.service, function() requireRuntime(runtime));
	}

	public static function installLua(host:PlayState, interp:Interp, origin:String):Void {
		var runtime = runtimeFor(host, interp.variables.get('Paths'), origin);
		if (runtime == null) return;
		PsychAchievementsLuaBindings.install(interp, runtime.service, report);
	}

	public static function installScope(host:PlayState, scope:SourceNativeClassScope, paths:Dynamic):Void {
		var runtime = runtimeFor(host, paths, null);
		if (runtime != null) PsychAchievementsBindings.installScope(scope, runtime.service,
			function() requireRuntime(runtime));
	}

	public static function runtimeFor(host:PlayState, paths:Dynamic, origin:String):PsychAchievementsRuntime {
		var owner = PsychSourceOwnerAccess.resolve(host, paths, origin);
		if (owner == null) return null;
		var root = owner.root;
		paths = owner.paths;
		if (!leaseInstalled) {
			leaseInstalled = true;
			FlxG.signals.preStateCreate.add(retainForState);
		}
		var existing = PsychAchievementsRuntime.lookup(root);
		if (existing != null) return existing;
		var capturedPaths = paths;
		var language = PsychStandardServices.languageFor(host, capturedPaths, origin);
		var assets:PsychAchievementPopupAssets = {
			fileExists:function(file:String):Bool {
				var resolved = Reflect.callMethod(capturedPaths, Reflect.field(capturedPaths, 'getPath'),
					[file, openfl.utils.AssetType.IMAGE]);
				return resolved != null && FNFAssets.exists(resolved);
			},
			image:function(key:String) return Reflect.callMethod(capturedPaths, Reflect.field(capturedPaths, 'image'), [key]),
			font:function(key:String):String {
				var path:String = Reflect.callMethod(capturedPaths, Reflect.field(capturedPaths, 'font'), [key]);
				return HxcOwnerFont.family(root, key, path) ?? path;
			}
		};
		var facades:Map<String, PsychAchievementPopupAssets> = [''=>assets];
		var source = FNFAssets.resolveCaseInsensitivePath(root + '/data/achievements.json');
		// The enabled source Mods registry is a separate open contract. Only the
		// captured package's real base JSON is registered until that context exists.
		var sources:Array<PsychAchievementsHost.PsychAchievementSource> = source == null ? [] : [{path:source, mod:null}];
		return PsychAchievementsRuntime.adopt(root, paths,
			new CodenameOwnerSaveData(root, CodenameOwnerSaveStorage.create(false)), {
				sources:sources, assetFacades:facades,
				readText:function(path:String) return FNFAssets.getText(path), report:report,
				playConfirmSound:function(key:String, volume:Float):Void {
					var sound = Reflect.callMethod(capturedPaths, Reflect.field(capturedPaths, 'sound'), [key]);
					if (sound != null) FlxG.sound.play(sound, volume);
				},
				phrase:function(key:String, fallback:String):String {
					return language == null ? fallback : language.getPhrase(key, fallback);
				},
				antialiasing:function():Bool return PsychClientPrefsCompat.data.antialiasing,
				stage:FlxG.stage, game:FlxG.game
			});
	}

	static function retainForState(next:FlxState):Void {
		if (!Std.isOfType(next, PlayState)) {PsychAchievementsRuntime.releaseAll(); return;}
		var play:PlayState = cast next;
		PsychAchievementsRuntime.retainOwners(PsychSourceOwnerAccess.retainedRoots(play));
	}

	static function requireRuntime(runtime:PsychAchievementsRuntime):Void {
		if (runtime == null || runtime.released) throw '[psych-achievements] Released imported owner';
	}
	static function report(message:String):Void trace('[psych-achievements] ' + message);
}
