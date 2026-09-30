package;

import flixel.FlxBasic;

/** Import surface and owner binding helpers for HL17's missing native UI kit. */
@:keep
class CodenameHL17UICompat {
	public static inline var VERTICAL:String = 'vertical';
	public static inline var HORIZONTAL:String = 'horizontal';

	public static function addBindings(bindings:Map<String, Dynamic>):Void {
		if (bindings == null) return;
		bind(bindings, 'HLUIComponent', HLUIComponent);
		bind(bindings, 'HLUILabel', HLUILabel);
		bind(bindings, 'HLUIBox', HLUIBox);
		bind(bindings, 'HLUIButton', HLUIButton);
		bind(bindings, 'HLUITable', HLUITable);
		bind(bindings, 'HLUITab', HLUITab);
		bind(bindings, 'HLUITabBox', HLUITabBox);
		bind(bindings, 'HLUICheckbox', HLUICheckbox);
		bind(bindings, 'HLUINumberStepper', HLUINumberStepper);
		bind(bindings, 'HLUIWindow', HLUIWindow);
		var layout = {VERTICAL:VERTICAL, HORIZONTAL:HORIZONTAL};
		bindings.set('Layout', layout);
		bindings.set('funkin.hl.ui.Layout', layout);
	}

	static function bind(bindings:Map<String, Dynamic>, shortName:String, type:Dynamic):Void {
		bindings.set(shortName, type);
		bindings.set('funkin.hl.ui.' + shortName, type);
	}

	public static function bindValue(value:Dynamic, paths:CodenamePaths,
		claim:FlxBasic->Void):Void {
		if (value == null) return;
		if (Std.isOfType(value, HLUIComponent)) {
			(cast value:HLUIComponent).bindOwner(paths, claim);
			return;
		}
		// HScript-ex represents a script subclass as a proxy whose actual native
		// superclass is held in `superClass`. Bind that native UI object as well.
		var parent = Reflect.field(value, 'superClass');
		if (parent != null && Std.isOfType(parent, HLUIComponent))
			(cast parent:HLUIComponent).bindOwner(paths, claim);
	}
}
