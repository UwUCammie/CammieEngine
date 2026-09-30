package;

using StringTools;

/**
	Owner-local facade for the source `funkin.Mods` API.

	`currentModDirectory` reports the selected source package directory. Since
	assets are mounted once for that owner, switching it at runtime would make
	this label disagree with `Paths`; writes to another directory fail clearly.
	APIs that require Nightmare Vision's process-global mod loader are present for
	source compatibility and fail with a clear error.
*/
@:keep
class NightmareVisionModsContext {
	static var sourceIgnoreModFolders:Array<String> = [
		'characters', 'events', 'notetypes', 'data', 'songs', 'music', 'sounds',
		'shaders', 'videos', 'images', 'stages', 'weeks', 'fonts', 'scripts', 'noteskins'
	];

	public static function sourceApiMethods():Array<String> return [
		'pushGlobalMods', 'getModDirectories', 'mergeAllTextsNamed', 'directoriesWithFile',
		'getPack', 'parseList', 'getListAsArray', 'updateModList', 'loadTopMod',
		'applyModConfig', 'getModIcon', 'getModName', 'getModFont'
	];

	public static function unsupportedSourceApiMethods():Array<String> return sourceApiMethods().copy();

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

	public function new(ownerRoot:String, ?sourceDirectory:String) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[nightmare-vision-mods] Missing selected owner root';
		this.ownerRoot = normalizeOwner(ownerRoot);
		currentDirectory = sourceDirectory;
		ignoreModFolders = sourceIgnoreModFolders.copy();
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

	/** The source methods below depend on global content roots, modsList.txt,
		window state, or active-mod switching. This runtime has no corresponding
		global Nightmare Vision mod loader, so reject each call instead of pretending it
		worked. */
	function unsupported(name:String):Dynamic {
		ensureAlive();
		throw '[nightmare-vision-mods-unsupported] funkin.Mods.' + name
			+ ' requires Nightmare Vision global mod-loader state and is unavailable in this owner-local runtime';
		return null;
	}

	public function pushGlobalMods():Array<String> return cast unsupported('pushGlobalMods');
	public function getModDirectories():Array<String> return cast unsupported('getModDirectories');
	public function mergeAllTextsNamed(path:String, ?defaultDirectory:String, allowDuplicates:Bool = false):Array<String>
		return cast unsupported('mergeAllTextsNamed');
	public function directoriesWithFile(path:String, fileToFind:String, mods:Bool = true):Array<String>
		return cast unsupported('directoriesWithFile');
	public function getPack(?folder:String):Dynamic return unsupported('getPack');
	public function parseList():Dynamic return unsupported('parseList');
	public function getListAsArray(?top:String = ''):Array<Dynamic> return cast unsupported('getListAsArray');
	public function updateModList(?top:String = ''):Void unsupported('updateModList');
	public function loadTopMod():Void unsupported('loadTopMod');
	public function applyModConfig(?directory:String):Void unsupported('applyModConfig');
	public function getModIcon(mod:String):String return cast unsupported('getModIcon');
	public function getModName(mod:String):String return cast unsupported('getModName');
	public function getModFont(mod:String):String return cast unsupported('getModFont');

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

	static function fieldString(value:Dynamic, name:String):String {
		var field:Dynamic = Reflect.field(value, name);
		return field == null || !Std.isOfType(field, String) ? null : cast field;
	}

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
