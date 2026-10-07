package;

import flixel.FlxG;
import flixel.FlxState;
import hscript.Interp;

private typedef PsychStandardOwner = {
	var root:String;
	var paths:Dynamic;
	var prefs:PsychOwnerClientPrefs;
	var ownsPrefs:Bool;
	var language:PsychLanguageRuntime;
	var discord:PsychDiscordClient;
	var released:Bool;
	var epoch:Int;
}

/** Owner services used by Lua, plain HScript and embedded HScript. The RPC
 * lease is shared across providers in one gameplay session, never per script. */
@:access(PlayState)
class PsychStandardServices {
	static var owners:Map<String, PsychStandardOwner> = new Map();
	static var listenerInstalled:Bool = false;
	static var epoch:Int = 0;
	static var primaryRoot:String;
	static var rpc:SourceDiscordPresenceLease;

	public static function installLua(host:PlayState, interp:Interp, origin:String):Void {
		var owner = runtimeFor(host, interp.variables.get('Paths'), origin);
		if (owner == null) return;
		PsychLanguageBindings.installLua(interp, owner.language);
		PsychDiscordBindings.installLua(interp, owner.discord);
	}
	public static function installHscript(host:PlayState, interp:Interp, origin:String):Void {
		if (!Std.isOfType(interp, SourceIrisBridge)) return;
		var owner = runtimeFor(host, interp.variables.get('Paths'), origin);
		if (owner == null) return;
		var evaluator = (cast interp:SourceIrisBridge).evaluator;
		PsychLanguageBindings.install(evaluator, owner.language);
		PsychDiscordBindings.install(evaluator, owner.discord);
	}
	public static function installScope(host:PlayState, scope:SourceNativeClassScope, paths:Dynamic):Void {
		var owner = runtimeFor(host, paths, null);
		if (owner == null) return;
		PsychLanguageBindings.installScope(scope, owner.language);
		PsychDiscordBindings.installScope(scope, owner.discord);
	}
	public static function languageFor(host:PlayState, paths:Dynamic, origin:String):Null<PsychLanguageRuntime> {
		var owner = runtimeFor(host, paths, origin);
		return owner == null ? null : owner.language;
	}

	static function runtimeFor(host:PlayState, paths:Dynamic, origin:String):Null<PsychStandardOwner> {
		var resolved = PsychSourceOwnerAccess.resolve(host, paths, origin);
		if (resolved == null) return null;
		var key = CompatScriptManifest.destinationKey(resolved.root);
		if (!listenerInstalled) {
			listenerInstalled = true;
			FlxG.signals.preStateCreate.add(retainForState);
		}
		var selected = PsychOwnerAssetPath.normalizeOwner(host.selectedPsychSkinRoot());
		if (selected == '') selected = resolved.root;
		if (rpc == null || primaryRoot != selected) {
			releaseAll(); primaryRoot = selected; rpc = new SourceDiscordPresenceLease();
		}
		var existing = owners.get(key);
		if (existing != null && !existing.released) {
			if (existing.epoch != epoch) {
				existing.epoch = epoch;
				existing.language.reloadPhrases();
			}
			PsychOwnerPaths.bindFileTranslation(resolved.paths,
				function(key:String) return existing.language.getFileTranslation(key));
			return existing;
		}
		var prefs = host.psychClientPrefs;
		var ownsPrefs = prefs == null || !prefs.canReuseFor(resolved.root);
		if (ownsPrefs) {
			prefs = new PsychOwnerClientPrefs(resolved.root, new CodenameOwnerSaveData(resolved.root), OptionsHandler.options);
			prefs.loadPrefs();
		}
		var owner:PsychStandardOwner = {root:resolved.root, paths:resolved.paths, prefs:prefs,
			ownsPrefs:ownsPrefs, language:null, discord:null, released:false, epoch:epoch};
		owners.set(key, owner);
		try {
			var alphabet = PsychAlphabetRegistry.get(owner.root, PsychAlphabetOwnerAccess.create(owner.paths,
				function() return owner.prefs.data), false);
			owner.language = new PsychLanguageRuntime(owner.root, prefs, {
				ownerActive:function() return !owner.released,
				mergedLines:function(language) return mergedLines(owner, language),
				loadAlphabetData:function(request) alphabet.loadAlphabetData(request),
				report:function(message) trace('[psych-language] ' + message)
			});
			owner.language.reloadPhrases();
			PsychOwnerPaths.bindFileTranslation(owner.paths,
				function(key:String) return owner.language.getFileTranslation(key));
			owner.discord = new PsychDiscordClient(rpc, function() return !owner.released);
		} catch (error:Dynamic) {
			retire(owner); throw error;
		}
		return owner;
	}

	static function mergedLines(owner:PsychStandardOwner, language:String):Array<String> {
		var relative = PsychOwnerAssetPath.cleanId('data/' + language + '.lang');
		if (relative == null) throw '[psych-language] Unsafe owner language path';
		var paths:Array<String> = [];
		var add = function(path:String):Void {
			if (path == null || !FNFAssets.exists(path) || !PsychOwnerAssetPath.withinOwner(owner.root, path)) return;
			var key = pathKey(path);
			for (previous in paths) if (pathKey(previous) == key) return;
			paths.push(path);
		};
		var shared = Reflect.callMethod(owner.paths, Reflect.field(owner.paths, 'getSharedPath'), [relative]);
		add(shared);
		var level = Reflect.callMethod(owner.paths, Reflect.field(owner.paths, '__sourceCurrentLevel'), []);
		if (level != null) add(Reflect.callMethod(owner.paths, Reflect.field(owner.paths, 'getFolderPath'), [relative, level]));
		// Full source enabled-Mods order remains an explicit importer profile
		// contract. Only this authenticated package's published layers are read.
		add(FNFAssets.resolveCaseInsensitivePath(owner.root + '/' + relative));
		var lines:Array<String> = [];
		for (path in paths) for (line in CoolUtil.coolTextFile(path))
			if (line.length > 0 && !lines.contains(line)) lines.push(line);
		return lines;
	}
	static function pathKey(path:String):String {
		#if sys
		path = sys.FileSystem.fullPath(path);
		#end
		var key = haxe.io.Path.normalize(StringTools.replace(path, '\\', '/'));
		#if windows
		return key.toLowerCase();
		#else
		return key;
		#end
	}

	static function retainForState(next:FlxState):Void {
		epoch++;
		if (!Std.isOfType(next, PlayState)) {releaseAll(); return;}
		var play:PlayState = cast next;
		var selected = PsychOwnerAssetPath.normalizeOwner(play.selectedPsychSkinRoot());
		if (selected != primaryRoot) {releaseAll(); return;}
		var keep = [for (root in PsychSourceOwnerAccess.retainedRoots(play)) CompatScriptManifest.destinationKey(root)];
		var retiring:Array<PsychStandardOwner> = [];
		for (key => owner in owners) if (!keep.contains(key)) retiring.push(owner);
		for (owner in retiring) retire(owner);
	}
	static function retire(owner:PsychStandardOwner):Void {
		if (owner.released) return;
		owner.released = true;
		owners.remove(CompatScriptManifest.destinationKey(owner.root));
		PsychOwnerSoundCache.releaseOwner(owner.root);
		PsychOwnerAssetPath.releaseOwner(owner.root);
		if (owner.language != null) owner.language.release();
		if (owner.discord != null) owner.discord.release();
		if (owner.ownsPrefs) owner.prefs.release();
	}
	public static function releaseAll():Void {
		var retiring = [for (owner in owners) owner];
		for (owner in retiring) retire(owner);
		if (rpc != null) rpc.release();
		rpc = null; primaryRoot = null;
	}
}
