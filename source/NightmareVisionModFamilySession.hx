package;

import haxe.io.Path;
using StringTools;

/** Shared selection and private list state for one retained package family. */
@:keep
class NightmareVisionModFamilySession {
	static inline var ROOT_PREFIX:String = 'assets/imported_mods/';

	final leaseRoot:String;
	final members:Array<NightmareVisionModFamilyMember> = [];
	final rootsByDirectory:Map<String, String> = new Map();
	var selectedDirectoryValue:Null<String>;
	var readListCallback:Void->Null<String>;
	var writeListCallback:String->Void;
	var listLoaded:Bool = false;
	var listValue:String = '';
	var listDirty:Bool = false;
	var references:Int = 0;
	var released:Bool = false;

	public function new(selectedDirectory:String, selectedRoot:String,
		members:Array<NightmareVisionModFamilyMember>, ?readList:Void->Null<String>,
		?writeList:String->Void) {
		leaseRoot = checkedRoot(selectedRoot);
		if (!validDirectoryLabel(selectedDirectory))
			throw '[nightmare-vision-mod-family] Invalid selected source directory';
		selectedDirectoryValue = selectedDirectory;
		readListCallback = readList;
		writeListCallback = writeList;

		if (members != null) for (member in members) {
			if (member == null || !validDirectoryLabel(member.directory))
				throw '[nightmare-vision-mod-family] Invalid family directory';
			var cleanRoot = checkedRoot(member.root);
			var existing = rootsByDirectory.get(member.directory);
			if (existing != null) {
				if (existing != cleanRoot)
					throw '[nightmare-vision-mod-family] Conflicting roots for source directory: ' + member.directory;
				continue;
			}
			for (prior in this.members)
				if (prior.directory != member.directory && prior.root == cleanRoot)
					throw '[nightmare-vision-mod-family] One installed root cannot have multiple source labels';
			// The input catalog is trusted for membership, but validate its values
			// again before retaining them in a script-visible resolver.
			rootsByDirectory.set(member.directory, cleanRoot);
			this.members.push({directory:member.directory, root:cleanRoot});
		}

		var selected = rootsByDirectory.get(selectedDirectory);
		if (selected == null) {
			for (member in this.members) if (member.root == leaseRoot)
				throw '[nightmare-vision-mod-family] Lease root is registered under a different source label';
			rootsByDirectory.set(selectedDirectory, leaseRoot);
			this.members.unshift({directory:selectedDirectory, root:leaseRoot});
		} else if (selected != leaseRoot) {
			throw '[nightmare-vision-mod-family] Selected directory does not map to its lease root';
		}
	}

	public function selectedRoot():Null<String> {
		ensureAlive();
		return selectedDirectoryValue == null || selectedDirectoryValue == ''
			? null : rootsByDirectory.get(selectedDirectoryValue);
	}

	public function selectedDirectory():Null<String> {
		ensureAlive();
		return selectedDirectoryValue;
	}

	public function rootForDirectory(directory:String):Null<String> {
		ensureAlive();
		if (!validDirectoryLabel(directory)) return null;
		return rootsByDirectory.get(directory);
	}

	public function familyDirectories():Array<String> {
		ensureAlive();
		var result:Array<String> = [];
		for (member in members) result.push(member.directory);
		return result;
	}

	public function authorizedRoots():Array<String> {
		ensureAlive();
		var result:Array<String> = [];
		for (member in members) if (!result.contains(member.root)) result.push(member.root);
		return result;
	}

	public function ownsRoot(root:String):Bool {
		ensureAlive();
		var clean:String;
		try clean = checkedRoot(root) catch (_:Dynamic) return false;
		return authorizedRoots().contains(clean);
	}

	public function selectDirectory(directory:Null<String>):Null<String> {
		ensureAlive();
		if (directory != null && directory != '' && rootForDirectory(directory) == null)
			throw '[nightmare-vision-mod-family-scope] Cannot select an unrelated source directory: ' + directory;
		selectedDirectoryValue = directory;
		return selectedDirectoryValue;
	}

	/** Contexts share this session only while they are deliberately attached. */
	public function attach():Void {
		ensureAlive();
		references++;
	}

	public function detach():Void {
		if (released) return;
		if (references > 0) references--;
		if (references == 0) release();
	}

	public function getModListText():String {
		ensureAlive();
		if (!listLoaded) {
			var loaded:Null<String> = readListCallback == null ? null : readListCallback();
			listValue = loaded == null ? '' : loaded;
			listLoaded = true;
		}
		return listValue;
	}

	/** Update the private snapshot before persisting so a failed write keeps the
		 same observable partial state as the source's in-memory list mutation. */
	public function setModListText(value:String):Void {
		ensureAlive();
		if (value == null) value = '';
		var previous = getModListText();
		if (value == previous && !listDirty) return;
		listValue = value;
		listLoaded = true;
		if (writeListCallback == null) {
			listDirty = false;
			return;
		}
		listDirty = true;
		writeListCallback(value);
		listDirty = false;
	}

	public function release():Void {
		if (released) return;
		released = true;
		references = 0;
		selectedDirectoryValue = null;
		members.resize(0);
		rootsByDirectory.clear();
		readListCallback = null;
		writeListCallback = null;
		listValue = '';
		listLoaded = false;
		listDirty = false;
	}

	function ensureAlive():Void {
		if (released)
			throw '[nightmare-vision-mod-family] This family session has been released';
	}

	static function validDirectoryLabel(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..'
			|| value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.indexOf('\x00') >= 0
			|| value.indexOf(':') >= 0 || value.indexOf('|') >= 0 || value.indexOf('?') >= 0
			|| value.indexOf('*') >= 0 || value.indexOf('<') >= 0 || value.indexOf('>') >= 0
			|| value.indexOf('"') >= 0)
			return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (code < 32 || code == 127) return false;
		}
		return true;
	}

	static function checkedRoot(value:String):String {
		if (value == null) throw '[nightmare-vision-mod-family] Missing installed root';
		var clean = StringTools.replace(value, '\\', '/');
		if (!clean.startsWith(ROOT_PREFIX) || clean.indexOf(':') >= 0 || clean.indexOf('\x00') >= 0)
			throw '[nightmare-vision-mod-family] Invalid installed root: ' + value;
		for (part in clean.split('/')) if (part == '' || part == '.' || part == '..')
			throw '[nightmare-vision-mod-family] Invalid installed root: ' + value;
		return Path.normalize(clean);
	}
}
