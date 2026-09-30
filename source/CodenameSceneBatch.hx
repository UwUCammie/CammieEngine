package;

/** Normalize Codename scene add/insert values while retaining owner-side
	validation. Arrays are ordered batches; native FlxGroups remain one native
	FlxBasic instead of being flattened into their children. */
class CodenameSceneBatch {
	public static function collect<T>(value:Dynamic, resolve:Dynamic->Null<T>, invalid:Dynamic->Void):Array<Dynamic> {
		var values:Array<Dynamic> = Std.isOfType(value, Array) ? cast value : [value];
		var result:Array<Dynamic> = [];
		var seen:Array<T> = [];
		for (candidate in values) {
			var native = resolve == null ? null : resolve(candidate);
			if (native == null) {
				if (invalid != null) invalid(candidate);
				continue;
			}
			if (seen.indexOf(native) >= 0) continue;
			seen.push(native);
			result.push(candidate);
		}
		return result;
	}
}
