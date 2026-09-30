package;

using StringTools;

/**
	One data-only item in an imported main-menu overlay.

	The compatibility pass copies this value into generated HScript as a plain
	object.  It is deliberately not a donor menu item: the native MainMenuState
	owns the actual FlxText/FlxSprite and input objects.
*/
typedef HxcMenuItemSpec = {
	var id:String;
	var label:String;
	var route:String;
	@:optional var target:String;
}

/**
	The bounded menu contract shared by HXC modules and imported menu states.

	`style` selects a generic native renderer (`button` or `text`).  Asset names
	are destination-relative and are resolved only below the caller's selected
	compatibility manifest root.  Route names are an allow-list, not class names.
*/
typedef HxcMenuSpecData = {
	var id:String;
	var style:String;
	var items:Array<HxcMenuItemSpec>;
	@:optional var background:String;
	@:optional var atlas:String;
	@:optional var font:String;
	@:optional var itemPrefix:String;
	@:optional var selectedPrefix:String;
	@:optional var foreground:String;
	@:optional var vignette:String;
	@:optional var fontSize:Int;
	@:optional var requiredAssets:Array<String>;
}

/** Pure helpers used by the read-only HXC analyzer and native host. */
class HxcMenuSpec {
	public static inline var STYLE_BUTTON:String = 'button';
	public static inline var STYLE_TEXT:String = 'text';
	public static inline var ROUTE_STORY:String = 'story';
	public static inline var ROUTE_FREEPLAY:String = 'freeplay';
	public static inline var ROUTE_OPTIONS:String = 'options';
	public static inline var ROUTE_CREDITS:String = 'credits';
	public static inline var ROUTE_COSTUMES:String = 'costumes';
	public static inline var ROUTE_IMPORTED:String = 'imported';
	public static inline var ROUTE_NOOP:String = 'noop';

	/** Return the stable route vocabulary for a visible menu label. */
	public static function routeForLabel(value:String):String {
		var key = normalize(value);
		return switch (key) {
			case 'story' | 'storymode' | 'storymenu': ROUTE_STORY;
			case 'freeplay' | 'freeplaymode': ROUTE_FREEPLAY;
			case 'options' | 'option' | 'settings': ROUTE_OPTIONS;
			case 'credits' | 'credit': ROUTE_CREDITS;
			case 'costumes' | 'costume': ROUTE_COSTUMES;
			// A visible menu item which has no native semantic is retained as a
			// selectable no-op so it can never silently launch donor content.
			default: ROUTE_NOOP;
		};
	}

	public static function normalize(value:String):String {
		if (value == null)
			return '';
		var output = new StringBuf();
		for (index in 0...value.length) {
			var character = value.charAt(index).toLowerCase();
			var code = character.charCodeAt(0);
			if ((code >= 97 && code <= 122) || (code >= 48 && code <= 57))
				output.add(character);
		}
		return output.toString();
	}

	/** Validate a dynamic HScript object before it reaches the native host. */
	public static function fromDynamic(value:Dynamic):Null<HxcMenuSpecData> {
		if (value == null)
			return null;
		var id = stringField(value, 'id');
		var style = stringField(value, 'style');
		var rawItems:Dynamic = Reflect.field(value, 'items');
		if (id == '' || (style != STYLE_BUTTON && style != STYLE_TEXT)
			|| !Std.isOfType(rawItems, Array))
			return null;
		var items:Array<HxcMenuItemSpec> = [];
		for (raw in (cast rawItems:Array<Dynamic>)) {
			if (raw == null)
				continue;
			var label = stringField(raw, 'label');
			var itemId = stringField(raw, 'id');
			var route = stringField(raw, 'route');
			var target = stringField(raw, 'target');
			if (itemId == '')
				itemId = normalize(label);
			if (label == '' || itemId == '' || !isRoute(route))
				return null;
			items.push({id:itemId, label:label, route:route, target:target});
		}
		if (items.length == 0)
			return null;
		var result:HxcMenuSpecData = {
			id:id,
			style:style,
			items:items
		};
		copyOptionalString(value, result, 'background');
		copyOptionalString(value, result, 'atlas');
		copyOptionalString(value, result, 'font');
		copyOptionalString(value, result, 'itemPrefix');
		copyOptionalString(value, result, 'selectedPrefix');
		copyOptionalString(value, result, 'foreground');
		copyOptionalString(value, result, 'vignette');
		var fontSize:Dynamic = Reflect.field(value, 'fontSize');
		if (fontSize != null)
			result.fontSize = Std.int(fontSize);
		var required:Dynamic = Reflect.field(value, 'requiredAssets');
		if (Std.isOfType(required, Array)) {
			result.requiredAssets = [];
			for (asset in (cast required:Array<Dynamic>))
				if (asset != null && StringTools.trim(Std.string(asset)) != '')
					result.requiredAssets.push(StringTools.replace(StringTools.trim(Std.string(asset)), '\\', '/'));
		}
		return result;
	}

	public static function isRoute(value:String):Bool {
		return value == ROUTE_STORY || value == ROUTE_FREEPLAY || value == ROUTE_OPTIONS
			|| value == ROUTE_CREDITS || value == ROUTE_COSTUMES || value == ROUTE_IMPORTED
			|| value == ROUTE_NOOP;
	}

	public static function stringField(value:Dynamic, name:String):String {
		if (value == null || name == null)
			return '';
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? '' : StringTools.trim(Std.string(field));
	}

	static function copyOptionalString(value:Dynamic, target:HxcMenuSpecData, name:String):Void {
		var field = stringField(value, name);
		if (field != '')
			Reflect.setField(target, name, field);
	}
}
