package;

/** Bounded, opt-in breadcrumbs for owner-scoped Codename state transitions. */
typedef CodenameStateSmokeField = {var name:String; var value:Dynamic;}

class CodenameStateSmokeTrace {
	static var checked:Bool = false;
	static var active:Bool = false;

	/** Trace ordinary menu routes without selecting the chart smoke entry state. */
	public static function enabled():Bool {
		#if sys
		if (!checked) {
			checked = true;
			active = Sys.args().indexOf('--codename-state-trace') >= 0;
		}
		return active;
		#else
		return false;
		#end
	}

	public static function field(name:String, value:Dynamic):CodenameStateSmokeField
		return {name:name, value:value};

	public static function mark(event:String, ownerRoot:String, scriptPath:String,
		?fields:Array<CodenameStateSmokeField>):Void {
		if (!enabled()) return;
		var marker = 'codename-' + token(event) + ':owner=' + token(ownerRoot)
			+ ':script=' + token(scriptPath);
		if (fields != null) for (field in fields)
			if (field != null) marker += ':' + token(field.name) + '=' + token(field.value);
		#if sys
		Sys.println('CODENAME_STATE_TRACE|' + marker);
		#end
	}

	/** A FlxState instance remains an instance inside FlxG's NextState abstract. */
	public static function stateName(value:Dynamic):String {
		if (value == null) return 'null';
		var type = Type.getClass(value);
		if (type != null) {
			var name = Type.getClassName(type);
			if (name != null && name != '') return name;
		}
		return Std.string(Type.typeof(value));
	}

	static function token(value:Dynamic):String {
		var result = value == null ? 'null' : Std.string(value);
		for (unsafe in ['\r', '\n', '|', ':', '='])
			result = StringTools.replace(result, unsafe, '_');
		return result;
	}
}
