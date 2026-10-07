package;

#if sys
import haxe.io.Path;
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

/** Shared staged writer for generated metadata. Return true only for a new
 * output; never replace an existing file without the transaction's mask. */
class ImportGeneratedOutput {
	public static function write(path:String, content:String, strictExisting:Bool = false):Bool {
		#if sys
		if (path == null || content == null) throw 'Generated import output needs a path and content.';
		if (FileSystem.exists(path)) {
			if (strictExisting && (FileSystem.isDirectory(path) || File.getContent(path) != content))
				throw 'Conflicting generated import output preserved: ' + path;
			return false;
		}
		FileSystem.createDirectory(Path.directory(path));
		File.saveContent(path, content);
		return true;
		#else
		throw 'Generated import output requires a filesystem.';
		#end
	}
}
