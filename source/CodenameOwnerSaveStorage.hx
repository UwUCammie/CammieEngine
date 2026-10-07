package;

/** Private JSON namespace appended to the native save record. */
class CodenameOwnerSaveStorage {
	static inline var ROOT_FIELD:String = 'codenameImportedModData';

	/** Build a save backend for one caller policy. Writes keep the historical
		flush behavior by default; callers which batch persistence can opt out and
		use the explicit `flush` delegate at their source-defined save boundary. */
	public static function create(autoFlushWrites:Bool = true):Dynamic {
		return {
			read: function(owner:String, field:String):Dynamic return read(owner, field),
			write: function(owner:String, field:String, value:Dynamic):Void
				write(owner, field, value, autoFlushWrites),
			flush: function():Void {
				if (flixel.FlxG.save != null) flixel.FlxG.save.flush();
			}
		};
	}

	static function read(owner:String, field:String):Dynamic {
		var data = saveData();
		if (data == null) return null;
		var owners = objectField(data, ROOT_FIELD, false);
		if (owners == null) return null;
		var bucket = objectField(owners, owner, false);
		return bucket == null ? null : Reflect.field(bucket, field);
	}

	static function write(owner:String, field:String, value:Dynamic, autoFlushWrites:Bool):Void {
		var data = saveData();
		if (data == null) throw '[codename-save] Native save data is unavailable';
		var owners = objectField(data, ROOT_FIELD, true);
		var bucket = objectField(owners, owner, true);
		var snapshot:Dynamic;
		try snapshot = haxe.Json.parse(haxe.Json.stringify(value)) catch (error:Dynamic)
			throw '[codename-save] Owner values must be JSON-serializable: ' + Std.string(error);
		Reflect.setField(bucket, field, snapshot);
		Reflect.setField(data, ROOT_FIELD, owners);
		if (autoFlushWrites && flixel.FlxG.save != null) flixel.FlxG.save.flush();
	}

	static function saveData():Dynamic {
		return flixel.FlxG.save == null ? null : flixel.FlxG.save.data;
	}

	static function objectField(parent:Dynamic, field:String, create:Bool):Dynamic {
		var value:Dynamic = Reflect.field(parent, field);
		if (value == null && create) {
			value = {};
			Reflect.setField(parent, field, value);
		}
		if (value != null && Type.typeof(value) != TObject)
			throw '[codename-save] Refused to overwrite malformed save data at ' + field;
		return value;
	}
}
