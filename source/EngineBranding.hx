package;

/** Application presentation metadata. Foreign engine API versions are separate. */
class EngineBranding {
	public static inline var NAME:String = 'CammieEngine';
	public static inline var FALLBACK_VERSION:String = '0.0.1';
	public static function version():String {
		#if lime
		var app = lime.app.Application.current;
		if (app != null && app.meta != null) {
			var value = app.meta.get('version');
			if (value != null && StringTools.trim(value) != '') return value;
		}
		#end
		return FALLBACK_VERSION;
	}
}
