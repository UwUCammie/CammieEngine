package;

import haxe.io.Path;

/**
	File types an imported mod can never use inside this engine: native programs
	and libraries, script launchers, Python runtimes and bytecode, and compiled
	language sources. Game folders often ship a bundled tool or runtime next to
	their art (one example carried a 550 MB program and a full Python install in
	its assets folder), and copying those into every imported namespace only
	fills the disk. Everything else is kept, because mod scripts can read any
	other file through the source engine's generic text and file APIs.
*/
class ImportRuntimeFileFilter {
	static final NEVER_LOADED:Map<String, Bool> = [
		for (extension in [
			'exe', 'dll', 'so', 'dylib', 'ndll', 'pdb', 'ilk', 'msi', 'scr', 'cpl', 'ocx', 'drv', 'efi',
			'bat', 'cmd', 'ps1', 'vbs',
			'py', 'pyc', 'pyo', 'pyd', 'pyw', 'pyi', 'whl', 'egg',
			'jar', 'class',
			'c', 'cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx', 'cs'
		]) extension => true
	];

	/** True when no part of the engine can load a file with this name. */
	public static function neverLoaded(path:String):Bool {
		if (path == null) return false;
		var name = Path.withoutDirectory(StringTools.replace(path, '\\', '/'));
		var dot = name.lastIndexOf('.');
		if (dot <= 0 || dot == name.length - 1) return false;
		return NEVER_LOADED.exists(name.substr(dot + 1).toLowerCase());
	}
}
