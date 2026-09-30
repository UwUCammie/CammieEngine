package;

import HxcMenuSpec.HxcMenuSpecData;

import flixel.FlxG;
import flixel.FlxState;
import flixel.FlxSubState;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/**
	A manifest-owned HXC state candidate.  The candidate carries the translated
	program and its destination root; it never carries a donor class name which
	could be handed to Type.resolveClass().
*/
typedef HxcStateFactoryEntry = {
	var name:String;
	var kind:String;
	var path:String;
	var root:String;
	var relativePath:String;
	var generatedHscript:String;
	/** Complete menu graphs are materialized by the native MainMenuState host. */
	@:optional var menuSpec:Null<HxcMenuSpecData>;
	/** Diagnostics are kept dynamic so the factory remains usable without
	 * exposing HxcCompat's module-private typedef in another compilation unit. */
	var diagnostics:Array<Dynamic>;
}

/** One cached find() outcome: the resolved entry, or the failure diagnostic. */
typedef HxcStateFactoryLookup = {
	var entry:Null<HxcStateFactoryEntry>;
	var diagnostic:String;
}

/**
	Resolve the narrow state factory vocabulary used by imported HXC files.

	Native aliases are delegated to HxcCompatRuntime, whose allow-list is
	explicit.  Foreign names are resolved only by scanning the selected
	compatScripts.json destination root and are materialized as one of the two
	HXC wrapper states.  There is intentionally no arbitrary reflection here:
	a class-looking name outside the selected root is a failed lookup.
*/
class HxcStateFactory {
	public static var lastDiagnostic(default, null):String = '';

	public static function stateInit(root:String, name:Dynamic):Dynamic {
		return init(root, name, 'state');
	}

	public static function subStateInit(root:String, name:Dynamic):Dynamic {
		return init(root, name, 'substate');
	}

	/**
		Materialize the small constructor vocabulary used by imported transition
		closures.  A closure is lowered to this helper before HScript executes, so
		we never call an arbitrary donor class or reflect over a package name.  The
		optional legacy boolean accepted by newer MainMenuState donors is ignored;
		this engine's native MainMenuState has no constructor argument and the
		argument only selected donor-side menu plumbing.
	*/
	public static function stateFactory(root:String, name:Dynamic, ?args:Array<Dynamic>):Dynamic {
		var requested = name == null ? '' : StringTools.trim(Std.string(name));
		var key = HxcScriptDiscovery.normalizeToken(requested);
		var supplied = args == null ? 0 : args.length;
		if (key == 'mainmenustate' && (supplied == 0
			|| (supplied == 1 && (args[0] == true || args[0] == false))))
			return stateInit(root, requested);
		if (supplied > 0)
			return fail('unsupported-hxc-state-constructor', 'HXC state factory ' + requested
				+ ' received constructor arguments which are not part of the native or manifest adapter.');
		return stateInit(root, requested);
	}

	/** Explicit native aliases remain available to every HXC interpreter. */
	public static function nativeState(name:Dynamic):Dynamic {
		return name == null ? null : HxcCompatRuntime.stateInit(Std.string(name));
	}

	static function init(root:String, name:Dynamic, kind:String):Dynamic {
		lastDiagnostic = '';
		var requested = name == null ? '' : StringTools.trim(Std.string(name));
		if (requested == '')
			return fail('unsupported-hxc-state-factory', 'HXC ' + kind + ' factory received an empty state name.');

		// Keep the old, audited native aliases intact even when a manifest happens
		// to contain a same-named file. Native state identity always wins.
		var native = kind == 'state' ? HxcCompatRuntime.stateInit(requested) : null;
		if (native != null)
			return native;

		#if sys
		var entry = find(root, requested, kind);
		if (entry == null)
			return null;
		if (entry.generatedHscript == null || StringTools.trim(entry.generatedHscript) == '') {
			fail('unsupported-hxc-state-body', 'HXC ' + kind + ' ' + requested
				+ ' has no executable lifecycle body after compatibility lowering (' + entry.path + ').');
			return null;
		}
		if (kind == 'state' && entry.menuSpec != null)
			return new HxcImportedMenuState(entry);
		if (kind == 'substate')
			return new HxcImportedSubState(entry);
		return new HxcImportedState(entry);
		#else
		return fail('unsupported-hxc-state-factory', 'Imported HXC ' + kind
			+ ' factories require a filesystem-backed manifest on this target.');
		#end
	}

	#if sys
	// One resolved lookup per imported root/kind/name for the whole run.
	// Translated module bodies legitimately call state factories from per-frame
	// callbacks (CatFightFreeplayFix's update installs its confirm popup every
	// frame), and an uncached find() re-walks and re-analyzes the entire
	// imported tree each call - seconds of menu lag per frame on large donors.
	// Import roots are content-addressed directories (a reimport lands in a new
	// hash-suffixed folder), so a resolved entry cannot go stale mid-session.
	// clearLookupCache() exists for callers which genuinely swap tree contents
	// under an existing root.
	static var lookupCache:Map<String, HxcStateFactoryLookup> = new Map();

	public static function clearLookupCache():Void {
		lookupCache = new Map();
	}

	/** How many distinct root/kind/name lookups were resolved from the walk. */
	public static var lookupCacheMisses(default, null):Int = 0;

	static function cacheKey(cleanRoot:String, kind:String, wanted:String):String {
		return cleanRoot + '|' + kind + '|' + wanted;
	}

	/** Find exactly one state in one manifest root; sibling roots are ignored. */
	public static function find(root:String, name:String, kind:String):Null<HxcStateFactoryEntry> {
		lastDiagnostic = '';
		var cleanRoot = safeManifestRoot(root);
		if (cleanRoot == '') {
			fail('unsupported-hxc-state-root', 'HXC ' + kind + ' ' + name
				+ ' was not resolved because its caller has no selected import manifest root.');
			return null;
		}
		var wanted = HxcScriptDiscovery.normalizeToken(name);
		if (wanted == '') {
			fail('unsupported-hxc-state-factory', 'HXC ' + kind + ' factory name ' + name + ' is not a valid identifier.');
			return null;
		}
		var key = cacheKey(cleanRoot, kind, wanted);
		if (lookupCache.exists(key)) {
			var cached = lookupCache.get(key);
			// A cached miss keeps its original diagnostic so callers which read
			// lastDiagnostic after a failed lookup still see the real reason.
			if (cached.entry == null)
				lastDiagnostic = cached.diagnostic;
			return cached.entry;
		}
		lookupCacheMisses++;
		var candidates:Array<HxcStateFactoryEntry> = [];
		var plan = HxcScriptDiscovery.discoverRoot(cleanRoot, '');
		// Donor trees also place state classes beside UI/modules (for example
		// `scripts/ui/CreditsMikuAnim.hxc`). Inspect the bounded manifest tree and
		// let HxcCompat's class/base classifier choose the exact runtime kind;
		// paths outside this root are never considered.
		var paths:Array<String> = plan.all == null ? [] : plan.all.copy();
		for (path in paths) {
			if (path == null || !insideRoot(path, cleanRoot))
				continue;
			var source:String;
			try {
				source = File.getContent(path);
			} catch (error:Dynamic) {
				fail('unsupported-hxc-state-read', 'Could not read manifest-owned HXC ' + kind
					+ ' candidate ' + path + ': ' + Std.string(error));
				continue;
			}
			var result = HxcCompat.analyze(source, path);
			if (result == null || result.kind != kind)
				continue;
			var names:Array<String> = [HxcScriptDiscovery.stem(path), result.className, result.identifier];
			var matched = false;
			for (candidate in names)
				if (candidate != null && HxcScriptDiscovery.normalizeToken(candidate) == wanted)
					matched = true;
			if (!matched)
				continue;
			var relative = relativeTo(path, cleanRoot);
			candidates.push({
				name: result.className == '' ? HxcScriptDiscovery.stem(path) : result.className,
				kind: kind,
				path: path,
				root: cleanRoot,
				relativePath: relative,
				generatedHscript: result.generatedHscript,
				menuSpec: result.menuSpec,
				diagnostics: result.diagnostics == null ? [] : result.diagnostics.copy()
			});
		}
		if (candidates.length == 0) {
			var missing = 'No manifest-owned HXC ' + kind + ' named ' + name
				+ ' exists under ' + cleanRoot + '.';
			lookupCache.set(key, {entry: null, diagnostic: missing});
			fail('unsupported-hxc-state-factory', missing);
			return null;
		}
		if (candidates.length > 1) {
			var pathsText:Array<String> = [];
			for (candidate in candidates)
				pathsText.push(candidate.path);
			var ambiguous = 'HXC ' + kind + ' name ' + name
				+ ' is ambiguous within manifest root ' + cleanRoot + ': ' + pathsText.join(', ') + '.';
			lookupCache.set(key, {entry: null, diagnostic: ambiguous});
			fail('unsupported-hxc-state-ambiguous', ambiguous);
			return null;
		}
		var selected = candidates[0];
		// Debug hook: DUMP_GENERATED_HXC=<dir> also captures manifest-owned
		// state/substate programs resolved through this factory, mirroring the
		// PlayState and freeplay module dumps, so a headless run can audit the
		// exact generated body an imported menu will execute.
		var dumpDir = Sys.environment().get('DUMP_GENERATED_HXC');
		if (dumpDir != null && StringTools.trim(dumpDir) != '') {
			try {
				if (!FileSystem.exists(dumpDir))
					FileSystem.createDirectory(dumpDir);
				var safeName = StringTools.replace(selected.path, '/', '_');
				safeName = StringTools.replace(safeName, '\\', '_');
				File.saveContent(dumpDir + '/' + safeName + '.generated.hscript',
					selected.generatedHscript == null ? '' : selected.generatedHscript);
			} catch (_:Dynamic) {}
		}
		// Preserve donor-only behavior as a diagnostic on the selected entry. The
		// wrapper still runs safe generated callbacks; unsupported callbacks are
		// omitted by HxcCompat and remain visible to the runtime log.
		for (diagnostic in selected.diagnostics)
			if (diagnostic != null && diagnostic.severity == 'warning')
				trace('[hxc-state-' + diagnostic.code + '] ' + diagnostic.message + ' (' + selected.path + ')');
		lookupCache.set(key, {entry: selected, diagnostic: ''});
		return selected;
	}

	static function safeManifestRoot(root:String):String {
		if (root == null || StringTools.trim(root) == '')
			return '';
		var clean = StringTools.replace(StringTools.trim(root), '\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		var parts = clean.split('/');
		for (part in parts)
			if (part == '' || part == '..')
				return '';
		var normalized = Path.normalize(clean);
		if (!normalized.startsWith(CompatScriptManifest.ROOT_PREFIX + '/'))
			return '';
		return normalized;
	}

	static function insideRoot(path:String, root:String):Bool {
		var fullPath = Path.normalize(StringTools.replace(FileSystem.fullPath(path), '\\', '/'));
		var fullRoot = Path.normalize(StringTools.replace(FileSystem.fullPath(root), '\\', '/'));
		return fullPath == fullRoot || fullPath.startsWith(fullRoot + '/');
	}

	static function relativeTo(path:String, root:String):String {
		var fullPath = Path.normalize(StringTools.replace(FileSystem.fullPath(path), '\\', '/'));
		var fullRoot = Path.normalize(StringTools.replace(FileSystem.fullPath(root), '\\', '/'));
		return fullPath.startsWith(fullRoot + '/') ? fullPath.substr(fullRoot.length + 1) : Path.withoutDirectory(path);
	}
	#end

	/** Switch only to native allow-listed states or wrappers from this runtime. */
	public static function switchState(target:Dynamic):Bool {
		if (target == null)
			return fail('unsupported-hxc-state-switch', 'HXC state switch target was null or unresolved.');
		if (Std.isOfType(target, HxcImportedSubState)) {
			if (FlxG.state == null)
				return fail('unsupported-hxc-state-switch', 'Cannot open an HXC substate without an active FlxState.');
			FlxG.state.openSubState(cast target);
			return true;
		}
		if (Std.isOfType(target, HxcImportedState)
			|| Std.isOfType(target, MainMenuState)
			|| Std.isOfType(target, StoryMenuState)
			|| Std.isOfType(target, FreeplayState)
			|| Std.isOfType(target, TitleState)
			|| Std.isOfType(target, CreditsState)
			|| Std.isOfType(target, SaveDataState)) {
			FlxG.switchState(cast target);
			return true;
		}
		return fail('unsupported-hxc-state-switch', 'HXC state switch target '
			+ Type.getClassName(Type.getClass(target))
			+ ' is not a native alias or a state materialized from the selected manifest.');
	}

	/** Switch with the caller's manifest namespace enforced. */
	public static function switchStateScoped(root:String, target:Dynamic):Bool {
		if (target != null && (Std.isOfType(target, HxcImportedMenuState)
			|| Std.isOfType(target, HxcImportedState)
			|| Std.isOfType(target, HxcImportedSubState))) {
			var entry:HxcStateFactoryEntry = null;
			if (Std.isOfType(target, HxcImportedMenuState))
				entry = (cast target:HxcImportedMenuState).factoryEntry;
			else if (Std.isOfType(target, HxcImportedState))
				entry = (cast target:HxcImportedState).factoryEntry;
			else
				entry = (cast target:HxcImportedSubState).factoryEntry;
			var callerRoot = root == null ? '' : Path.normalize(StringTools.replace(StringTools.trim(root), '\\', '/'));
			var targetRoot = entry == null || entry.root == null ? '' : Path.normalize(entry.root);
			if (callerRoot == '' || targetRoot == '' || callerRoot != targetRoot)
				return fail('unsupported-hxc-cross-import-switch', 'HXC state switch crossed manifest roots ('
					+ callerRoot + ' -> ' + targetRoot + ').');
		}
		return switchState(target);
	}

	/**
		V-Slice's currentState.startExitState(target) is a bounded state switch,
		not a second reflection/factory surface. Keep the caller manifest check in
		one place so generated HXC cannot cross imported roots.
	*/
	public static function startExitState(root:String, target:Dynamic):Bool {
		return switchStateScoped(root, target);
	}

	/** Open a manifest-owned substate from the current HXC owner. */
	public static function openSubStateScoped(root:String, owner:Dynamic, target:Dynamic):Bool {
		if (target == null)
			return fail('unsupported-hxc-substate-switch', 'HXC openSubState target was null or unresolved.');
		if (!Std.isOfType(target, HxcImportedSubState))
			return fail('unsupported-hxc-substate-switch', 'HXC openSubState target '
				+ Type.getClassName(Type.getClass(target))
				+ ' is not a substate materialized from the selected manifest.');
		var entry:HxcStateFactoryEntry = (cast target:HxcImportedSubState).factoryEntry;
		var callerRoot = root == null ? '' : Path.normalize(StringTools.replace(StringTools.trim(root), '\\', '/'));
		var targetRoot = entry == null || entry.root == null ? '' : Path.normalize(entry.root);
		if (callerRoot == '' || targetRoot == '' || callerRoot != targetRoot)
			return fail('unsupported-hxc-cross-import-switch', 'HXC substate open crossed manifest roots ('
				+ callerRoot + ' -> ' + targetRoot + ').');
		var host:FlxState = null;
		if (Std.isOfType(owner, FlxState))
			host = cast owner;
		else if (FlxG.state != null)
			host = FlxG.state;
		if (host == null)
			return fail('unsupported-hxc-substate-switch', 'Cannot open an HXC substate without an active FlxState.');
		host.openSubState(cast target);
		return true;
	}

	/** Back closes an imported substate; a top-level imported state returns home. */
	public static function back(current:Dynamic):Bool {
		if (current != null && Std.isOfType(current, HxcImportedSubState)) {
			(cast current:HxcImportedSubState).close();
			return true;
		}
		var home = HxcCompatRuntime.stateInit('MainMenuState');
		if (home == null)
			return fail('unsupported-hxc-state-back', 'Native MainMenuState is unavailable for HXC back navigation.');
		return switchState(home);
	}

	public static function resetState():Bool {
		if (FlxG.state == null)
			return fail('unsupported-hxc-state-reset', 'Cannot reset HXC state without an active FlxState.');
		FlxG.resetState();
		return true;
	}

	static function fail(code:String, message:String):Dynamic {
		lastDiagnostic = code + ': ' + message;
		trace('[' + code + '] ' + message);
		return null;
	}
}
