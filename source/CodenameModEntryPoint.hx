package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Select one authored menu entry point from a single imported Codename owner.
	The candidate's own source must transition to another state listed for that
	owner. This keeps arbitrary state files out of the package picker and avoids
	resolving a same-named class from a sibling package.
*/
class CodenameModEntryPoint {
	static inline var MAX_STATE_SOURCE_BYTES:Int = 262144;
	static inline var MAX_STATES:Int = 512;

	/** Prefer authored intro/title screens, then a conventional authored menu.
		Returns an owner-relative path, or an empty string for native Freeplay.
	*/
	public static function find(root:String, statePaths:Array<String>):String {
		#if sys
		if (root == null || !FileSystem.isDirectory(root) || statePaths == null
			|| statePaths.length == 0 || statePaths.length > MAX_STATES)
			return '';
		var states = statePaths.copy();
		states.sort(Reflect.compare);
		for (pass in 0...3) {
			for (candidate in states) {
				var basename = Path.withoutExtension(Path.withoutDirectory(candidate)).toLowerCase();
				var wanted = switch (pass) {
					case 0: basename == 'titlestate' || basename == 'title';
					case 1: basename == 'introstate' || basename == 'intro';
					default: basename == 'mainmenustate' || basename == 'mainmenu';
				};
				if (wanted && routesToOwnerState(root, candidate, states))
					return candidate;
			}
		}
		#end
		return '';
	}

	#if sys
	static function routesToOwnerState(root:String, sourcePath:String,
		statePaths:Array<String>):Bool {
		var resolution = CodenameScriptDiscovery.scopedResolution(root, sourcePath);
		if (resolution.relative == null) return false;
		var source = '';
		try {
			var absolute = Path.join([root, resolution.relative]);
			if (FileSystem.stat(absolute).size > MAX_STATE_SOURCE_BYTES) return false;
			source = File.getContent(absolute);
		} catch (_:Dynamic) return false;
		var ownerTargets:Array<String> = [];
		for (path in statePaths) if (path != sourcePath) ownerTargets.push(path);
		// Only constructors passed to a state transition count as authored
		// routing evidence. Capture the actual class expression so a qualified
		// namespace is resolved exactly rather than reduced to a basename.
		var transition = new EReg('(?:switchState|loadAndSwitchState|switchSubState|openSubState)\\s*\\(([^;]{0,240})', 'i');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 64 && transition.match(remaining)) {
			var body = transition.matched(1);
			var constructor = new EReg('\\bnew\\s+([A-Za-z0-9_$.]+)\\s*\\(', 'i');
			if (constructor.match(body)) {
				var className = constructor.matched(1);
				var resolution = CodenameModStateResolver.resolve(ownerTargets, className, sourcePath);
				if (resolution.path != '' && !resolution.ambiguous) return true;
			}
			var position = transition.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
			remaining = remaining.substr(position.pos + position.len);
		}
		return false;
	}
	#end
}
