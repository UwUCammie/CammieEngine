package;

import sys.FileSystem as RawFileSystem;

/** FileSystem facade paired with ImportFile for staged importer I/O. */
class ImportFileSystem {
	public static function exists(path:String):Bool {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.exists(path) : context.exists(path);
	}

	public static function rename(path:String, newPath:String):Void {
		var context = ImportIO.current();
		if (context == null) RawFileSystem.rename(path, newPath) else context.rename(path, newPath);
	}

	public static function stat(path:String):sys.FileStat {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.stat(path) : context.stat(path);
	}

	public static function fullPath(path:String):String {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.fullPath(path) : context.fullPath(path);
	}

	public static function absolutePath(path:String):String {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.absolutePath(path) : context.absolutePath(path);
	}

	public static function isDirectory(path:String):Bool {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.isDirectory(path) : context.isDirectory(path);
	}

	public static function createDirectory(path:String):Void {
		var context = ImportIO.current();
		if (context == null) RawFileSystem.createDirectory(path) else context.createDirectory(path);
	}

	public static function deleteFile(path:String):Void {
		var context = ImportIO.current();
		if (context == null) RawFileSystem.deleteFile(path) else context.deleteFile(path);
	}

	public static function deleteDirectory(path:String):Void {
		var context = ImportIO.current();
		if (context == null) RawFileSystem.deleteDirectory(path) else context.deleteDirectory(path);
	}

	public static function readDirectory(path:String):Array<String> {
		var context = ImportIO.current();
		return context == null ? RawFileSystem.readDirectory(path) : context.readDirectory(path);
	}
}
