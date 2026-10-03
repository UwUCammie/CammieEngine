package;

import haxe.io.Bytes;
import sys.io.FileInput;
import sys.io.FileOutput;
import sys.io.File as RawFile;

/** File API facade which redirects active import writes into ImportIO staging. */
class ImportFile {
	public static function getContent(path:String):String {
		var context = ImportIO.current();
		return RawFile.getContent(context == null ? path : context.readPath(path));
	}

	public static function saveContent(path:String, content:String):Void {
		var context = ImportIO.current();
		RawFile.saveContent(context == null ? path : context.writePath(path), content);
	}

	public static function getBytes(path:String):Bytes {
		var context = ImportIO.current();
		return RawFile.getBytes(context == null ? path : context.readPath(path));
	}

	public static function saveBytes(path:String, bytes:Bytes):Void {
		var context = ImportIO.current();
		RawFile.saveBytes(context == null ? path : context.writePath(path), bytes);
	}

	public static function read(path:String, binary:Bool = true):FileInput {
		var context = ImportIO.current();
		return RawFile.read(context == null ? path : context.readPath(path), binary);
	}

	public static function write(path:String, binary:Bool = true):FileOutput {
		var context = ImportIO.current();
		return RawFile.write(context == null ? path : context.writePath(path), binary);
	}

	public static function append(path:String, binary:Bool = true):FileOutput {
		var context = ImportIO.current();
		return RawFile.append(context == null ? path : context.appendPath(path), binary);
	}

	public static function copy(source:String, destination:String):Void {
		var context = ImportIO.current();
		if (context == null) {
			RawFile.copy(source, destination);
			return;
		}
		context.copy(source, destination);
	}
}
