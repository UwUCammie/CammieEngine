package;

/** Compose source-visible field discovery over the same scoped class routes.
 * Each adapter supplies its source field list; reflection mechanics stay shared. */
class SourceClassFieldDiscovery {
	public static function install(scope:SourceNativeClassScope, type:Dynamic, names:Array<String>):Void {
		var sourceFields = names.copy();
		var append = function(fields:Array<String>):Array<String> {
			var result = fields == null ? [] : fields.copy();
			for (name in sourceFields) if (result.indexOf(name) < 0) result.push(name);
			return result;
		};
		var previousFields:Dynamic = scope.read(Reflect, 'fields');
		scope.bindStaticField(Reflect, 'fields', function() return function(value:Dynamic):Array<String> {
			var fields:Array<String> = cast Reflect.callMethod(null, previousFields, [value]);
			return value == type ? append(fields) : fields;
		});
		var previousHasField:Dynamic = scope.read(Reflect, 'hasField');
		scope.bindStaticField(Reflect, 'hasField', function() return function(value:Dynamic, field:String):Bool {
			if (value == type && sourceFields.indexOf(field) >= 0) return true;
			return Reflect.callMethod(null, previousHasField, [value, field]);
		});
		var previousClassFields:Dynamic = scope.read(Type, 'getClassFields');
		scope.bindStaticField(Type, 'getClassFields', function() return function(value:Class<Dynamic>):Array<String> {
			var fields:Array<String> = cast Reflect.callMethod(null, previousClassFields, [value]);
			return value == type ? append(fields) : fields;
		});
	}
}
