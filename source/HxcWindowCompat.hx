package;

import openfl.Lib;
import lime.graphics.Image;

/**
	Small host-owned window bridge for imported HXC modules.

	The donor WindowUtil/Application APIs are process globals.  HXC adapters call
	this class only through the explicit `hxcSetWindow*` functions seeded by the
	native interpreters, so an imported script cannot reflect arbitrary window
	properties or read a foreign application object.
*/
class HxcWindowCompat {
	public static function setTitle(value:Dynamic):Void {
#if desktop
		try {
			if (Lib.application != null && Lib.application.window != null)
				Lib.application.window.title = value == null ? '' : Std.string(value);
		} catch (error:Dynamic) {
			trace('[hxc-window] unable to set title: ' + Std.string(error));
		}
#end
	}

	public static function setIcon(path:Dynamic, ?origin:String):Void {
#if desktop
		var value = path == null ? '' : Std.string(path);
		if (StringTools.trim(value) == '')
			return;
		try {
			if (!FNFAssets.exists(value)) {
				var source = origin == null || StringTools.trim(origin) == ''
					? 'HXC window icon request' : origin;
				var diagnostic = EngineCompat.planVisualFallback('window-icon', value, source,
					[value], 'the window keeps its current icon; chart gameplay continues',
					'unresolved-source-dependency');
				EngineCompat.reportVisualFallback(diagnostic);
				return;
			}
			if (Lib.application != null && Lib.application.window != null)
				Lib.application.window.setIcon(Image.fromBytes(FNFAssets.getBytes(value)));
		} catch (error:Dynamic) {
			trace('[hxc-window] unable to set icon ' + value + ': ' + Std.string(error));
		}
#end
	}
}
