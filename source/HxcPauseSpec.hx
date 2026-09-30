package;

using StringTools;

/**
	Data-only pause overlay configuration extracted from a complete HXC helper.
	The native PauseSubState owns every display object, input action, and cleanup
	operation; this type never contains donor callbacks or object references.
*/
typedef HxcPauseSpecData = {
	var id:String;
	@:optional var artPrefix:String;
	@:optional var logo:String;
	@:optional var atlas:String;
	@:optional var logoAnimation:String;
	@:optional var titleFont:String;
	@:optional var menuFont:String;
	@:optional var titleLabel:String;
	@:optional var deathLabel:String;
	@:optional var practiceLabel:String;
	@:optional var hiddenLabels:Array<String>;
	@:optional var itemColor:Int;
	@:optional var selectedColor:Int;
	@:optional var fontSize:Int;
	@:optional var menuFontSize:Int;
	@:optional var requiredAssets:Array<String>;
}

/** Validation helpers shared by the analyzer and native pause host. */
class HxcPauseSpec {
	public static function fromDynamic(value:Dynamic):Null<HxcPauseSpecData> {
		if (value == null)
			return null;
		var id = stringField(value, 'id');
		if (id == '')
			return null;
		var result:HxcPauseSpecData = {id:id};
		for (name in ['artPrefix', 'logo', 'atlas', 'logoAnimation', 'titleFont', 'menuFont',
			'titleLabel', 'deathLabel', 'practiceLabel'])
			copyString(value, result, name);
		copyInt(value, result, 'itemColor');
		copyInt(value, result, 'selectedColor');
		copyInt(value, result, 'fontSize');
		copyInt(value, result, 'menuFontSize');
		var hidden:Dynamic = Reflect.field(value, 'hiddenLabels');
		if (Std.isOfType(hidden, Array)) {
			result.hiddenLabels = [];
			for (label in (cast hidden:Array<Dynamic>))
				if (label != null && StringTools.trim(Std.string(label)) != '')
					result.hiddenLabels.push(StringTools.trim(Std.string(label)));
		}
		var required:Dynamic = Reflect.field(value, 'requiredAssets');
		if (Std.isOfType(required, Array)) {
			result.requiredAssets = [];
			for (asset in (cast required:Array<Dynamic>))
				if (asset != null && StringTools.trim(Std.string(asset)) != '')
					result.requiredAssets.push(StringTools.replace(StringTools.trim(Std.string(asset)), '\\', '/'));
		}
		return result;
	}

	static function stringField(value:Dynamic, name:String):String {
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? '' : StringTools.trim(Std.string(field));
	}

	static function copyString(value:Dynamic, target:HxcPauseSpecData, name:String):Void {
		var field = stringField(value, name);
		if (field != '')
			Reflect.setField(target, name, field);
	}

	static function copyInt(value:Dynamic, target:HxcPauseSpecData, name:String):Void {
		var field:Dynamic = Reflect.field(value, name);
		if (field != null)
			Reflect.setField(target, name, Std.int(field));
	}
}
