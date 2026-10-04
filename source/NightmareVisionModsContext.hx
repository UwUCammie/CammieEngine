package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
using StringTools;

/**
	Owner-local facade for the source `funkin.Mods` API.

	`currentModDirectory` reports the selected source package directory. Since
	assets are mounted once for that owner, switching it at runtime would make
	this label disagree with `Paths`. Mod enumeration and configuration reads
	therefore operate on this owner only; global loader side effects do not leak
	into the game or another imported script.
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
	/** The mounted source package label, immutable for this owner lifetime. */
	public var currentModDirectory(get, set):Null<String>;
	/** Source-shaped fields. Their values are detached and belong to this instance. */
	public var currentModConfig:Dynamic = null;
	public var ignoreModFolders:Array<String>;
	public var globalMods:Array<String> = [];
	public var released(default, null):Bool = false;

	var currentDirectory:Null<String>;
	final files:SourceScriptFileAccess;
	var ownerEnabled:Bool = true;
	var ownerModOrder:Array<String> = [];

	public function new(ownerRoot:String, ?sourceDirectory:String) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[nightmare-vision-mods] Missing selected owner root';
		this.ownerRoot = normalizeOwner(ownerRoot);
		currentDirectory = sourceDirectory;
		files = new SourceScriptFileAccess(resolveOwnedPath);
		ignoreModFolders = sourceIgnoreModFolders.copy();
		if (sourceDirectory != null) ownerModOrder = [sourceDirectory];
	}

	public function canReuseFor(owner:String):Bool {
		if (released || owner == null) return false;
		return normalizeOwner(owner) == ownerRoot;
	}

	function get_currentModDirectory():Null<String> {
		ensureAlive();
		if (currentDirectory == null)
			throw missingSourceDirectory();
		return currentDirectory;
	}

	function set_currentModDirectory(value:Null<String>):Null<String> {
		ensureAlive();
		if (currentDirectory == null)
			throw missingSourceDirectory();
		if (value != currentDirectory)
			throw '[nightmare-vision-mods-unsupported] funkin.Mods.currentModDirectory cannot switch the mounted Nightmare Vision owner; refresh the owner context to select another package';
		return currentDirectory;
	}

	function missingSourceDirectory():String
		return '[nightmare-vision-mods-context-missing] source mod directory is unavailable for this imported owner; refresh the import to restore owner context';

	/** Global mods collapse to the selected owner. No other imported package is
	 * visible to this script context. */
	public function pushGlobalMods():Array<String> {
		ensureAlive();
		globalMods = [];
		var pack = getPack();
		if (pack != null && field(pack, 'global') == true && currentDirectory != null)
			globalMods.push(currentDirectory);
		return globalMods.copy();
	}

	public function getModDirectories():Array<String> {
		ensureAlive();
		if (currentDirectory == null || ignoreModFolders.contains(currentDirectory.toLowerCase())) return [];
		return [currentDirectory];
	}

	/** Search the source core first, followed by this selected owner, mirroring
	 * source precedence while omitting process-global and sibling mod roots. */
	public function directoriesWithFile(path:String, fileToFind:String, mods:Bool = true):Array<String> {
		ensureAlive();
		var result:Array<String> = [];
		var base = resolveSourceDirectory(path);
		var candidate = resolveWithin(base, fileToFind);
		if (candidate != null && files.exists(candidate)) result.push(candidate);
		if (mods) {
			var ownerCandidate = resolveWithin(ownerRoot, fileToFind);
			if (ownerCandidate != null && files.exists(ownerCandidate) && !result.contains(ownerCandidate))
				result.push(ownerCandidate);
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
		if (value == null || value.trim() == '') return ownerRoot + '/' + CORE_SUBTREE;
		var clean = value.replace('\\', '/').trim();
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		if (clean == 'assets') return ownerRoot + '/' + CORE_SUBTREE;
		if (clean.startsWith('assets/')) return ownerRoot + '/' + CORE_SUBTREE + '/' + clean.substr('assets/'.length);
		if (clean == ownerRoot || clean.startsWith(ownerRoot + '/')) return clean;
		if (clean.startsWith('content/') && currentDirectory != null
			&& (clean == 'content/' + currentDirectory || clean.startsWith('content/' + currentDirectory + '/')))
			return ownerRoot + clean.substr(('content/' + currentDirectory).length);
		return ownerRoot + '/' + CORE_SUBTREE + '/' + clean;
	}

	function resolveWithin(base:String, child:String):Null<String> {
		if (base == null || child == null || child.trim() == '') return null;
		var joined = Path.join([base, child.replace('\\', '/')]);
		return files.resolve(joined);
	}

	/** Parse only this context's source package record. A request for another
	 * mod directory cannot inspect a sibling import. */
	public function getPack(?folder:String):Dynamic {
		ensureAlive();
		if (folder != null && folder != '' && folder != currentDirectory) return null;
		var path = Path.join([ownerRoot, 'meta.json']);
		if (!files.exists(path)) return null;
		var text = files.getText(path);
		if (text == null || text == '') return null;
		try {
			#if json5hx
			return haxe.Json5.parse(text);
			#else
			return haxe.Json.parse(text);
			#end
		} catch (error:Dynamic) {
			trace('[nightmare-vision-mods-meta] Invalid owner meta.json: ' + Std.string(error));
			return null;
		}
	}

	public function parseList():Dynamic {
		ensureAlive();
		updateModList();
		var enabled:Array<String> = ownerEnabled && currentDirectory != null ? [currentDirectory] : [];
		var disabled:Array<String> = !ownerEnabled && currentDirectory != null ? [currentDirectory] : [];
		return {enabled:enabled, disabled:disabled, all:enabled.concat(disabled)};
	}

	public function getListAsArray(?top:String = ''):Array<Dynamic> {
		ensureAlive();
		var selected = top == null || top == '' ? currentDirectory : top;
		if (selected == null || selected == '') return [];
		if (selected != currentDirectory)
			throw '[nightmare-vision-mods-scope] Cannot enumerate source mod outside selected owner: ' + selected;
		return [{folder:selected, enabled:ownerEnabled}];
	}

	/** Rebuild the one-owner list snapshot without touching the source engine's
	 * shared modsList.txt or current-mod globals. */
	public function updateModList(?top:String = ''):Void {
		ensureAlive();
		if (top != null && top != '' && top != currentDirectory)
			throw '[nightmare-vision-mods-scope] Cannot reorder a mod outside selected owner: ' + top;
		ownerModOrder = currentDirectory == null ? [] : [currentDirectory];
	}

	public function loadTopMod():Void {
		ensureAlive();
		// The selected owner is already mounted; selecting it again is the only
		// valid operation in this owner-local context.
		applyModConfig();
	}

	/** Retain the selected owner's parsed config locally. Window, transition,
	 * Discord, and process-wide preference effects remain outside an import. */
	public function applyModConfig(?directory:String):Void {
		ensureAlive();
		if (directory != null && directory != '' && directory != currentDirectory)
			throw '[nightmare-vision-mods-scope] Cannot apply config outside selected owner: ' + directory;
		currentModConfig = getPack();
	}

	public function getModIcon(mod:String):String {
		ensureAlive();
		var pack = getPack(mod == null || mod == '' ? null : mod);
		var icon = field(pack, 'iconFile');
		return icon == null ? 'branding/icon/fallback' : Std.string(icon);
	}

	public function getModName(mod:String):String {
		ensureAlive();
		var folder = mod == null || mod == '' ? currentDirectory : mod;
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
		for (base in [ownerRoot, ownerRoot + '/' + CORE_SUBTREE])
			for (ext in ['ttf', 'otf']) {
				var candidate = files.resolve(Path.join([base, 'fonts/' + name + '.' + ext]));
				if (candidate != null && files.exists(candidate)) return candidate;
			}
		return files.resolve(Path.join([ownerRoot + '/' + CORE_SUBTREE, 'fonts/' + name]))
			?? (ownerRoot + '/' + CORE_SUBTREE + '/fonts/' + name);
	}

	/** Release this context when its imported owner is unmounted. */
	public function release():Void {
		if (released) return;
		released = true;
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
		var coreRoot = ownerRoot + '/' + CORE_SUBTREE;
		var selected:String;
		if (clean == ownerRoot || clean.startsWith(ownerRoot + '/')) selected = clean;
		else if (currentDirectory != null && (clean == 'content/' + currentDirectory
			|| clean.startsWith('content/' + currentDirectory + '/'))) {
			selected = ownerRoot + clean.substr(('content/' + currentDirectory).length);
		} else if (clean == 'assets') selected = coreRoot;
		else if (clean.startsWith('assets/')) selected = coreRoot + '/' + clean.substr('assets/'.length);
		else if (absolute) return null;
		else selected = coreRoot + '/' + clean;
		selected = Path.normalize(selected);
		if (selected != ownerRoot && !selected.startsWith(ownerRoot + '/')) return null;
		#if sys
		if (FileSystem.exists(ownerRoot)) {
			var ancestor = selected;
			while (!FileSystem.exists(ancestor) && ancestor != ownerRoot) {
				var parent = Path.directory(ancestor);
				if (parent == ancestor || parent == '') break;
				ancestor = parent;
			}
			if (FileSystem.exists(ancestor)) {
				var canonicalOwner = Path.normalize(FileSystem.fullPath(ownerRoot));
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
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (code < 32 || code == 127) return false;
		}
		return true;
	}

	static function normalizeOwner(value:String):String
		return StringTools.trim(StringTools.replace(value, '\\', '/'));
}
