package;

/** Lime's emitted manifest is data, never a class-instantiation request. */
class SourceCompiledAssetManifest {
	public static inline var MAX_BYTES:Int = 16 * 1024 * 1024;
	public static inline var MAX_ASSETS:Int = 262144;
	public static function parse(text:String):Dynamic {
		if (text == null || text.length > MAX_BYTES) throw 'Compiled manifest exceeds size limit';
		var data:Dynamic = haxe.Json.parse(text);
		if (data == null || Type.typeof(data) != TObject) throw 'Compiled manifest must be an object';
		var version:Dynamic = data.version;
		if (!Std.isOfType(version,Int) || version < 1 || version > 3) throw 'Unsupported compiled manifest version';
		var assets:Dynamic = data.assets;
		if (version <= 2) {
			if (!Std.isOfType(assets,String)) throw 'Serialized asset table required';
			var decoder = new SourceManifestUnserializer(assets);
			assets = decoder.unserialize();
			decoder.requireEnd();
		}
		if (!Std.isOfType(assets,Array) || (cast assets:Array<Dynamic>).length > MAX_ASSETS)
			throw 'Invalid compiled asset table';
		for (entry in (cast assets:Array<Dynamic>)) {
			if (entry == null || Type.typeof(entry) != TObject) throw 'Compiled asset record must be anonymous data';
			for (field in ['id','type']) if (!Std.isOfType(Reflect.field(entry,field),String)
				|| Reflect.field(entry,field) == '') throw 'Missing compiled asset '+field;
			for (field in ['path','className']) if (Reflect.field(entry,field) != null
				&& !Std.isOfType(Reflect.field(entry,field),String)) throw 'Invalid compiled asset '+field;
			if (entry.preload != null && !Std.isOfType(entry.preload,Bool)) throw 'Invalid compiled preload flag';
			if (entry.size != null && (!Std.isOfType(entry.size,Int) || entry.size < 0)) throw 'Invalid compiled size';
		}
		if (data.rootPath != null && !Std.isOfType(data.rootPath,String)) throw 'Invalid compiled root path';
		if (data.libraryType != null && !Std.isOfType(data.libraryType,String)) throw 'Invalid compiled library type';
		if (data.libraryArgs != null && !Std.isOfType(data.libraryArgs,Array)) throw 'Invalid compiled library arguments';
		data.assets = assets;
		return data;
	}
}

/** Bound recursion/work and prohibit Haxe class/custom deserialization hooks. */
@:access(haxe.Unserializer)
private class SourceManifestUnserializer extends haxe.Unserializer {
	var depth:Int = 0;
	var nodes:Int = 0;
	var inputLength:Int;
	public function new(text:String) {
		super(text); inputLength = text.length;
		setResolver({resolveClass:function(name:String):Class<Dynamic> return null,
			resolveEnum:function(name:String):Enum<Dynamic> return null});
	}
	override public function unserialize():Dynamic {
		if (++depth > 3 || ++nodes > 2097152) throw 'Compiled manifest serialization limit';
		var token = buf.charAt(pos);
		if (depth == 1) {
			if (token != 'a') throw 'Compiled assets must serialize an array';
			pos++;
			var values:Array<Dynamic> = [];
			while (buf.charAt(pos) != 'h') {
				if (values.length >= SourceCompiledAssetManifest.MAX_ASSETS || pos >= inputLength)
					throw 'Compiled asset array limit';
				values.push(unserialize());
			}
			pos++; depth--; return values;
		}
		if (depth == 2 && token != 'o') throw 'Compiled asset must serialize anonymous data';
		if (depth == 3 && ['n','t','f','i','z','d','y','R'].indexOf(token) < 0)
			throw 'Compiled asset fields must be scalar data';
		var value = super.unserialize();
		depth--; return value;
	}
	public function requireEnd():Void {
		if (pos != inputLength) throw 'Trailing compiled asset serialization';
	}
}
