package;

import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.BytesBuffer;
import haxe.io.Eof;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

/** Bounded read-only metadata snapshot shared by retained and installed audits.
 * Change detection is advisory; mutation still requires transaction reservations. */
class ImportMetadataInspection {
	public var root(default, null):String;
	var cancel:Void->Bool;
	var files:Map<String,{hash:String, size:Int}> = new Map();
	var directories:Map<String,String> = new Map();
	var absent:Map<String,Bool> = new Map();
	var bytes:Float = 0;
	var entries:Int = 0;
	public function new(root:String, ?cancel:Void->Bool) {
		this.root = ImportRefreshTransaction.canonicalDirectory(root, false); this.cancel = cancel;
	}
	public function check():Void ImportRefreshTransaction.checkpointWork(cancel);
	function checked(path:String, required:Bool):String {
		path = Path.normalize(FileSystem.absolutePath(path));
		ImportRefreshTransaction.assertInside(path, root);
		return ImportRefreshTransaction.safeChild(root, ImportRefreshTransaction.relativePathFrom(root, path), required);
	}
	public function exists(path:String):Bool {
		check(); path = checked(path, false);
		if (FileSystem.exists(path)) return true;
		absent.set(path, true); return false;
	}
	public function directory(path:String):Array<String> {
		check(); path = checked(path, true);
		if (!FileSystem.isDirectory(path)) throw 'Ownership metadata is not a directory: $path';
		var names = FileSystem.readDirectory(path); names.sort(Reflect.compare);
		entries += names.length;
		if (entries > 262144) throw 'Ownership metadata entry limit exceeded.';
		var encoded = Json.stringify(names);
		if (directories.exists(path) && directories.get(path) != encoded) throw 'Ownership inventory changed during inspection: $path';
		directories.set(path, encoded); return names;
	}
	public function optionalDirectory(path:String):Array<String> return exists(path) ? directory(path) : [];
	public function isDirectory(path:String):Bool { check(); return FileSystem.isDirectory(checked(path, true)); }
	public function metadata(path:String, maxBytes:Int = 134217728):Dynamic return Json.parse(text(path, maxBytes));
	public function text(path:String, maxBytes:Int = 134217728):String {
		check(); path = checked(path, true);
		var data = read(path, maxBytes);
		var hash = Sha256.make(data).toHex();
		var old = files.get(path);
		if (old != null && (old.hash != hash || old.size != data.length)) throw 'Ownership metadata changed during inspection: $path';
		files.set(path, {hash:hash, size:data.length}); return data.toString();
	}
	function read(path:String, maxBytes:Int):Bytes {
		if (!ImportRefreshTransaction.isRegularFile(path)) throw 'Ownership metadata is not a file: $path';
		var size = FileSystem.stat(path).size;
		if (maxBytes < 0 || maxBytes > 134217728 || size < 0 || size > maxBytes) throw 'Ownership metadata byte limit exceeded.';
		var input = File.read(path, true);
		var result = new BytesBuffer(); var buffer = Bytes.alloc(65536); var count = 0;
		try {
			while (true) {
				check();
				var amount:Int;
				try amount = input.readBytes(buffer, 0, buffer.length) catch (_:Eof) break;
				if (amount <= 0) break;
				count += amount; bytes += amount;
				if (count > maxBytes || bytes > 536870912) throw 'Ownership metadata byte limit exceeded.';
				result.addBytes(buffer, 0, amount);
			}
			input.close();
		} catch (error:Dynamic) { input.close(); throw error; }
		if (count != size) throw 'Ownership metadata changed while reading: $path';
		return result.getBytes();
	}
	public function digest(path:String):String {
		path = checked(path, true); var found = files.get(path);
		if (found == null) throw 'Metadata has not been inspected: $path';
		return found.hash;
	}
	public function verify():Void {
		for (path in files.keys()) {
			check(); checked(path, true); var expected = files.get(path);
			if (Sha256.make(read(path, expected.size)).toHex() != expected.hash) throw 'Ownership metadata changed during inspection: $path';
		}
		for (path in directories.keys()) {
			check(); checked(path, true);
			var names = FileSystem.readDirectory(path); names.sort(Reflect.compare);
			if (Json.stringify(names) != directories.get(path)) throw 'Ownership inventory changed during inspection: $path';
		}
		for (path in absent.keys()) { check(); if (FileSystem.exists(checked(path, false))) throw 'Ownership metadata appeared during inspection: $path'; }
		check();
	}
}
