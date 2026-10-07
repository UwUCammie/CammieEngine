package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
using StringTools;

/**
	Owner-scoped facade for the source `funkin.Mods` API. A singleton context
	retains its original package root; a catalog-backed family session can select
	other authenticated retained packages without changing the immutable lease.
	Config effects are delegated to the active host after the selected pack has
	been assigned, preserving source ordering and callback partial state.
*/
@:keep
class NightmareVisionModsContext {
	static inline var CORE_SUBTREE:String = '__nmv_core';
	static var sourceIgnoreModFolders:Array<String> = [
		'characters', 'events', 'notetypes', 'data', 'songs', 'music', 'sounds',
		'shaders', 'videos', 'images', 'stages', 'weeks', 'fonts', 'scripts', 'noteskins'
	];

	public static function sourceApiMethods():Array<String> return [
		'pushGlobalMods', 'getModDirectories', 'mergeAllTextsNamed', 'directoriesWithFile',
		'getPack', 'parseList', 'getListAsArray', 'updateModList', 'loadTopMod',
		'applyModConfig', 'getModIcon', 'getModName', 'getModFont'
	];

	/** No source Mods function is a placeholder anymore. Process-global effects
	 * are represented as owner-local operations or rejected at the specific call. */
	public static function unsupportedSourceApiMethods():Array<String> return [];

	/** Extract the package directory retained by the importer. Old receipts may
		use an inferred `modName`, which is the original directory basename. A
		display-name label is not a directory and requires a refreshed import. */
	public static function sourceDirectoryFromProvenance(provenance:Dynamic,
		?report:String->Void):Null<String> {
		if (provenance != null) {
			var direct = fieldString(provenance, 'sourceModDirectory');
			if (validDirectoryLabel(direct)) return direct;
			if (fieldString(provenance, 'nameSource') == 'inferred') {
				var legacy = fieldString(provenance, 'modName');
				if (validDirectoryLabel(legacy)) return legacy;
			}
		}
		var diagnostic = '[nightmare-vision-mods-owner-directory-missing] Import provenance does not retain a safe source mod directory; refresh the import to restore owner context';
		if (report != null) report(diagnostic) else trace(diagnostic);
		return null;
	}

	/** Stable identity of the imported package that owns this context. */
	public var ownerRoot(default, null):String;
	/** The selected source package label, session-shared for a family. */
	public var currentModDirectory(get, set):Null<String>;
	/** Source-shaped fields. Their values are detached and belong to this instance. */
	public var currentModConfig:Dynamic = null;
	public var ignoreModFolders:Array<String>;
	public var globalMods:Array<String> = [];
	public var released(default, null):Bool = false;
	/** One live source table shared by all interpreters in this owner session. */
	public var optionSession:NightmareVisionSourceOptions;
	/** Native host handle kept opaque so the pure resolver has no GPU dependency. */
	public var nativeConfig:Dynamic;

	var currentDirectory:Null<String>;
	final files:SourceScriptFileAccess;
	final familySession:NightmareVisionModFamilySession;
	var configApplier:NightmareVisionModConfigApplier;
	var ownerEnabled:Bool = true;
	var ownerModOrder:Array<String> = [];

	public function new(ownerRoot:String, ?sourceDirectory:String,
		?familySession:NightmareVisionModFamilySession) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[nightmare-vision-mods] Missing selected owner root';
		this.ownerRoot = normalizeOwner(ownerRoot);
		this.familySession = familySession;
		if (familySession != null) {
			if (!familySession.ownsRoot(this.ownerRoot))
				throw '[nightmare-vision-mods-family] Session does not authorize its immutable owner root';
			if (sourceDirectory != null && sourceDirectory != ''
				&& familySession.rootForDirectory(sourceDirectory) != this.ownerRoot)
				throw '[nightmare-vision-mods-family] Source directory does not match the immutable owner root';
			currentDirectory = familySession.selectedDirectory();
			familySession.attach();
		} else currentDirectory = sourceDirectory;
		files = new SourceScriptFileAccess(resolveOwnedPath);
		ignoreModFolders = sourceIgnoreModFolders.copy();
		if (familySession == null && sourceDirectory != null) ownerModOrder = [sourceDirectory];
	}

	/** Bind the native config effects once the runtime has captured this owner's
		window, Paths, transition, RPC, redirect, and private-save services. */
	public function bindConfigHost(host:NightmareVisionModConfigHost):Void {
		ensureAlive();
		if (host == null) throw '[nightmare-vision-mod-config] Missing native host';
		if (configApplier != null)
			throw '[nightmare-vision-mod-config] A native host is already bound to this owner context';
		configApplier = new NightmareVisionModConfigApplier(host);
	}

	public function canReuseFor(owner:String):Bool {
		if (released || owner == null) return false;
		return normalizeOwner(owner) == ownerRoot;
	}

	function get_currentModDirectory():Null<String> {
		ensureAlive();
		if (familySession != null) return familySession.selectedDirectory();
		if (currentDirectory == null)
			throw missingSourceDirectory();
		return currentDirectory;
	}

	function set_currentModDirectory(value:Null<String>):Null<String> {
		ensureAlive();
		if (familySession != null) {
			familySession.selectDirectory(value);
			currentDirectory = value;
			return currentDirectory;
		}
		if (currentDirectory == null)
			throw missingSourceDirectory();
		if (value != currentDirectory)
			throw '[nightmare-vision-mods-unsupported] funkin.Mods.currentModDirectory cannot switch the mounted Nightmare Vision owner; refresh the owner context to select another package';
		return currentDirectory;
	}

	/** Current asset root for this context. The singleton path deliberately keeps
		 its lease root even when provenance did not retain a source label. */
	public function selectedRoot():Null<String> {
		ensureAlive();
		return familySession == null ? ownerRoot : familySession.selectedRoot();
	}

	function activeDirectory():Null<String>
		return familySession == null ? currentDirectory : familySession.selectedDirectory();

	function activeRoot():Null<String> {
		var selected = selectedRoot();
		return selected == null ? ownerRoot : selected;
	}

	public function rootForDirectory(directory:String):Null<String> {
		ensureAlive();
		if (familySession != null) return familySession.rootForDirectory(directory);
		return directory != null && directory != '' && directory == activeDirectory() ? ownerRoot : null;
	}

	public function familyDirectories():Array<String> {
		ensureAlive();
		if (familySession != null) return familySession.familyDirectories();
		var selected = activeDirectory();
		return selected == null || selected == '' ? [] : [selected];
	}

	public function authorizedRoots():Array<String> {
		ensureAlive();
		return familySession == null ? [ownerRoot] : familySession.authorizedRoots();
	}

	public function ownsRoot(root:String):Bool {
		ensureAlive();
		if (familySession != null) return familySession.ownsRoot(root);
		return normalizeRootOrEmpty(root) == ownerRoot;
	}

	function missingSourceDirectory():String
		return '[nightmare-vision-mods-context-missing] source mod directory is unavailable for this imported owner; refresh the import to restore owner context';

	/** Enabled catalog members contribute global content in source order. */
	public function pushGlobalMods():Array<String> {
		ensureAlive();
		globalMods = [];
		if (familySession != null) {
			var parsed:Dynamic = parseList();
			var enabled:Array<String> = cast Reflect.field(parsed, 'enabled');
			for (directory in enabled) {
				var pack = getPack(directory);
				if (pack != null && field(pack, 'global') == true && !globalMods.contains(directory))
					globalMods.push(directory);
			}
		} else {
			var pack = getPack();
			var selected = activeDirectory();
			if (pack != null && field(pack, 'global') == true && selected != null)
				globalMods.push(selected);
		}
		return globalMods.copy();
	}

	public function getModDirectories():Array<String> {
		ensureAlive();
		if (familySession != null) {
			var result:Array<String> = [];
			for (directory in familySession.familyDirectories()) {
				if (ignoreModFolders.contains(directory.toLowerCase())) continue;
				var root = familySession.rootForDirectory(directory);
				if (root != null && files.isDirectory(root)) result.push(directory);
			}
			return result;
		}
		var selected = activeDirectory();
		if (selected == null || ignoreModFolders.contains(selected.toLowerCase())) return [];
		return [selected];
	}

	/** Search core first, then enabled global packages, then the selected package. */
	public function directoriesWithFile(path:String, fileToFind:String, mods:Bool = true):Array<String> {
		ensureAlive();
		var result:Array<String> = [];
		var base = resolveSourceDirectory(path);
		var candidate = resolveWithin(base, fileToFind);
		if (candidate != null && files.exists(candidate)) result.push(candidate);
		if (mods) {
			for (directory in globalMods) {
				var globalRoot = rootForDirectory(directory);
				var globalCandidate = globalRoot == null ? null : resolveWithin(globalRoot, fileToFind);
				if (globalCandidate != null && files.exists(globalCandidate) && !result.contains(globalCandidate))
					result.push(globalCandidate);
			}
			var selected = selectedRoot();
			var selectedCandidate = selected == null ? null : resolveWithin(selected, fileToFind);
			if (selectedCandidate != null && files.exists(selectedCandidate) && !result.contains(selectedCandidate))
				result.push(selectedCandidate);
		}
		return result;
	}

	public function mergeAllTextsNamed(path:String, ?defaultDirectory:String, allowDuplicates:Bool = false):Array<String> {
		ensureAlive();
		if (defaultDirectory == null) defaultDirectory = 'assets';
		var files = directoriesWithFile(defaultDirectory, path, true);
		var merged:Array<String> = [];
		for (file in files) {
			var text = this.files.getText(file);
			if (text == null) continue;
			for (value in text.trim().split('\n')) {
				value = value.trim();
				if (value.length > 0 && (allowDuplicates || !merged.contains(value))) merged.push(value);
			}
		}
		return merged;
	}

	function resolveSourceDirectory(value:String):String {
		var root = activeRoot();
		var coreRoot = root + '/' + CORE_SUBTREE;
		if (value == null || value.trim() == '') return coreRoot;
		var clean = value.replace('\\', '/').trim();
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		if (clean == 'assets') return coreRoot;
		if (clean.startsWith('assets/')) return coreRoot + '/' + clean.substr('assets/'.length);
		for (authorized in authorizedRoots())
			if (clean == authorized || clean.startsWith(authorized + '/')) return clean;
		if (clean.startsWith('content/')) {
			var tail = clean.substr('content/'.length);
			var slash = tail.indexOf('/');
			var label = slash < 0 ? tail : tail.substr(0, slash);
			var packageRoot = rootForDirectory(label);
			if (packageRoot != null) return packageRoot + (slash < 0 ? '' : '/' + tail.substr(slash + 1));
		}
		return coreRoot + '/' + clean;
	}

	function resolveWithin(base:String, child:String):Null<String> {
		if (base == null || child == null || child.trim() == '') return null;
		var joined = Path.join([base, child.replace('\\', '/')]);
		return files.resolve(joined);
	}

	/** Parse only the selected package or another catalog-authorized family
	 * member. Unregistered source labels never become filesystem paths. */
	public function getPack(?folder:String):Dynamic {
		ensureAlive();
		var packageRoot:Null<String>;
		if (familySession != null) {
			var directory = folder == null ? activeDirectory() : folder;
			if (directory == null || directory == '') {
				trace('[nightmare-vision-mods-config-unavailable] Empty source directory refers to shared content-root metadata, which is unavailable in this imported package context');
				return null;
			}
			packageRoot = rootForDirectory(directory);
		} else {
			if (folder != null && folder != '' && folder != activeDirectory()) return null;
			packageRoot = ownerRoot;
		}
		if (packageRoot == null) return null;
		var path = Path.join([packageRoot, 'meta.json']);
		if (!files.exists(path)) return null;
		var text = files.getText(path);
		if (text == null || text == '') return null;
		return parseModConfigJson5(text);
	}

	static function parseModConfigJson5(text:String):Dynamic {
		if (text == null) return null;
		try {
			#if json5hx
			return haxe.Json5.parse(text);
			#else
			return haxe.Json.parse(text);
			#end
		} catch (error:Dynamic) {
			trace('[nightmare-vision-json5] failed to parse content: ' + Std.string(error));
			return null;
		}
	}

	public function parseList():Dynamic {
		ensureAlive();
		updateModList();
		if (familySession != null) {
			var enabled:Array<String> = [];
			var disabled:Array<String> = [];
			var all:Array<String> = [];
			for (line in readListLines(familySession.getModListText())) {
				if (line.trim().length < 1) continue;
				var data = line.split('|');
				var directory = data[0];
				if (rootForDirectory(directory) == null) continue;
				all.push(directory);
				if (data.length > 1 && data[1] == '1') enabled.push(directory);
				else disabled.push(directory);
			}
			return {enabled:enabled, disabled:disabled, all:all};
		}
		var selected = activeDirectory();
		var enabled:Array<String> = ownerEnabled && selected != null ? [selected] : [];
		var disabled:Array<String> = !ownerEnabled && selected != null ? [selected] : [];
		return {enabled:enabled, disabled:disabled, all:enabled.concat(disabled)};
	}

	public function getListAsArray(?top:String = ''):Array<Dynamic> {
		ensureAlive();
		if (familySession != null) return getFamilyListAsArray(top);
		var selected = top == null || top == '' ? activeDirectory() : top;
		if (selected == null || selected == '') return [];
		if (selected != activeDirectory())
			throw '[nightmare-vision-mods-scope] Cannot enumerate source mod outside selected owner: ' + selected;
		return [{folder:selected, enabled:ownerEnabled}];
	}

	function getFamilyListAsArray(top:Null<String>):Array<Dynamic> {
		var selected = top == null || top == '' ? activeDirectory() : top;
		if (selected != null && selected != '' && rootForDirectory(selected) == null)
			throw '[nightmare-vision-mods-family-scope] Cannot enumerate an unrelated source directory: ' + selected;
		var result:Array<Dynamic> = [];
		var added:Array<String> = [];
		if (selected != null && selected.length > 0 && directoryExists(selected)) {
			added.push(selected);
			result.push({folder:selected, enabled:true});
		}
		for (line in readListLines(familySession.getModListText())) {
			var data = line.split('|');
			if (data.length < 1) continue;
			var folder = data[0];
			if (folder.trim().length < 1 || rootForDirectory(folder) == null
				|| !directoryExists(folder) || added.contains(folder) || folder == selected) continue;
			added.push(folder);
			result.push({folder:folder, enabled:data.length > 1 && data[1] == '1'});
		}
		for (folder in getModDirectories()) {
			if (folder.trim().length < 1 || ignoreModFolders.contains(folder.toLowerCase())
				|| added.contains(folder) || folder == selected) continue;
			added.push(folder);
			result.push({folder:folder, enabled:true});
		}
		return result;
	}

	function directoryExists(directory:String):Bool {
		var root = rootForDirectory(directory);
		return root != null && files.isDirectory(root);
	}

	static function readListLines(text:String):Array<String> {
		if (text == null || text == '') return [];
		var trimmed = text.trim();
		if (trimmed == '') return [];
		var lines = trimmed.split('\n');
		for (index in 0...lines.length) lines[index] = lines[index].trim();
		return lines;
	}

	/** Rebuild the owner-private family list without touching the source engine's
	 * shared modsList.txt or current-mod globals. */
	public function updateModList(?top:String = ''):Void {
		ensureAlive();
		if (familySession != null) {
			var list = getFamilyListAsArray('');
			var fileText = '';
			ownerModOrder = [];
			for (value in list) {
				var folder:String = Reflect.field(value, 'folder');
				var enabled:Bool = Reflect.field(value, 'enabled') == true;
				if (fileText.length > 0) fileText += '\n';
				fileText += folder + '|' + (enabled ? '1' : '0');
				ownerModOrder.push(folder);
			}
			familySession.setModListText(fileText);
			return;
		}
		if (top != null && top != '' && top != activeDirectory())
			throw '[nightmare-vision-mods-scope] Cannot reorder a mod outside selected owner: ' + top;
		var selected = activeDirectory();
		ownerModOrder = selected == null ? [] : [selected];
	}

	public function loadTopMod():Void {
		ensureAlive();
		if (familySession != null) {
			set_currentModDirectory('');
			var parsed:Dynamic = parseList();
			var enabled:Array<String> = cast Reflect.field(parsed, 'enabled');
			if (enabled != null && enabled.length > 0) set_currentModDirectory(enabled[0]);
			applyModConfig();
			return;
		}
		// The selected owner is already mounted; selecting it again is the only
		// valid operation in this owner-local context.
		applyModConfig();
	}

	/** Apply the source config to the currently selected owner. An explicit
		`directory` controls only metadata lookup; like the donor, options and
		Paths effects still belong to currentModDirectory. */
	public function applyModConfig(?directory:String):Void {
		ensureAlive();
		if (familySession != null) {
			if (directory != null && directory != '' && rootForDirectory(directory) == null)
				throw '[nightmare-vision-mods-family-scope] Cannot apply config outside the authorized family: ' + directory;
			var pack = getPack(directory);
			if (pack == null) return;
			currentModConfig = pack;
			applySelectedConfig(pack);
			return;
		}
		if (directory != null && directory != '' && directory != activeDirectory())
			throw '[nightmare-vision-mods-scope] Cannot apply config outside selected owner: ' + directory;
		var pack = getPack();
		if (pack == null) return;
		currentModConfig = pack;
		applySelectedConfig(pack);
	}

	function applySelectedConfig(pack:Dynamic):Void {
		if (configApplier == null)
			throw '[nightmare-vision-mod-config-host-missing] Source config was assigned but no native host is bound';
		var selected = selectedRoot();
		if (selected == null)
			throw '[nightmare-vision-mod-config-owner-missing] Source config was assigned but the family has no selected owner';
		configApplier.apply(pack, activeDirectory(), selected);
	}

	public function getModIcon(mod:String):String {
		ensureAlive();
		var pack = getPack(mod == null || mod == '' ? null : mod);
		var icon = field(pack, 'iconFile');
		return icon == null ? 'branding/icon/fallback' : Std.string(icon);
	}

	public function getModName(mod:String):String {
		ensureAlive();
		var folder = mod == null || mod == '' ? activeDirectory() : mod;
		var pack = getPack(folder);
		var name = field(pack, 'name');
		return name == null ? folder : Std.string(name);
	}

	public function getModFont(mod:String):String {
		ensureAlive();
		var pack = getPack(mod == null || mod == '' ? null : mod);
		var font = field(pack, 'defaultFont');
		return findFont(font == null ? 'vcr.ttf' : Std.string(font));
	}

	function findFont(name:String):String {
		var root = activeRoot();
		for (base in [root, root + '/' + CORE_SUBTREE])
			for (ext in ['ttf', 'otf']) {
				var candidate = files.resolve(Path.join([base, 'fonts/' + name + '.' + ext]));
				if (candidate != null && files.exists(candidate)) return candidate;
			}
		return files.resolve(Path.join([root + '/' + CORE_SUBTREE, 'fonts/' + name]))
			?? (root + '/' + CORE_SUBTREE + '/fonts/' + name);
	}

	/** Release this context when its imported owner is unmounted. */
	public function release():Void {
		if (released) return;
		released = true;
		if (configApplier != null) configApplier.release();
		configApplier = null;
		if (familySession != null) familySession.detach();
		currentDirectory = null;
		currentModConfig = null;
		ignoreModFolders = [];
		globalMods = [];
		ownerRoot = '';
	}

	function ensureAlive():Void {
		if (released)
			throw '[nightmare-vision-mods] This owner context has been released';
	}

	/** Translate source-relative/core ids to the captured owner and validate
	 * their nearest existing filesystem ancestor, including symlinks. */
	function resolveOwnedPath(path:String, write:Bool, absolute:Bool):Null<String> {
		if (path == null || path.trim() == '') return null;
		var clean = path.replace('\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0 || clean.indexOf('\x00') >= 0) return null;
		for (part in clean.split('/')) if (part == '.' || part == '..') return null;
		var selectedRoot = activeRoot();
		var coreRoot = selectedRoot + '/' + CORE_SUBTREE;
		var selected:String;
		var allowedRoot:Null<String> = null;
		for (root in authorizedRoots()) if (clean == root || clean.startsWith(root + '/')) {
			allowedRoot = root;
			break;
		}
		if (allowedRoot != null) selected = clean;
		else if (clean.startsWith('content/')) {
			var tail = clean.substr('content/'.length);
			var slash = tail.indexOf('/');
			var directory = slash < 0 ? tail : tail.substr(0, slash);
			var mapped = rootForDirectory(directory);
			if (mapped == null) return null;
			allowedRoot = mapped;
			selected = mapped + (slash < 0 ? '' : '/' + tail.substr(slash + 1));
		} else if (clean == 'assets') selected = coreRoot;
		else if (clean.startsWith('assets/')) selected = coreRoot + '/' + clean.substr('assets/'.length);
		else if (absolute) return null;
		else selected = coreRoot + '/' + clean;
		selected = Path.normalize(selected);
		if (allowedRoot == null) allowedRoot = selectedRoot;
		if (selected != allowedRoot && !selected.startsWith(allowedRoot + '/')) return null;
		#if sys
		if (FileSystem.exists(allowedRoot)) {
			var ancestor = selected;
			while (!FileSystem.exists(ancestor) && ancestor != allowedRoot) {
				var parent = Path.directory(ancestor);
				if (parent == ancestor || parent == '') break;
				ancestor = parent;
			}
			if (FileSystem.exists(ancestor)) {
			var canonicalOwner = Path.normalize(FileSystem.fullPath(allowedRoot));
				var canonical = Path.normalize(FileSystem.fullPath(ancestor));
				if (canonical != canonicalOwner && !canonical.startsWith(canonicalOwner + '/')) return null;
			}
		}
		#end
		return selected;
	}

	static function fieldString(value:Dynamic, name:String):String {
		var field:Dynamic = Reflect.field(value, name);
		return field == null || !Std.isOfType(field, String) ? null : cast field;
	}

	static function field(value:Dynamic, name:String):Dynamic
		return value == null ? null : Reflect.field(value, name);

	static function validDirectoryLabel(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..'
			|| value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.indexOf('\x00') >= 0)
			return false;
		for (invalid in [':', '|', '?', '*', '<', '>', '"']) if (value.indexOf(invalid) >= 0) return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (code < 32 || code == 127) return false;
		}
		return true;
	}

	static function normalizeRootOrEmpty(value:String):String {
		if (value == null) return '';
		return Path.normalize(normalizeOwner(value));
	}

	static function normalizeOwner(value:String):String
		return Path.normalize(StringTools.trim(StringTools.replace(value, '\\', '/')));
}
