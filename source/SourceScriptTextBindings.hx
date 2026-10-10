package;

/** Shared text callbacks; lookup, fonts and colors stay owned by the source adapter. */
class SourceScriptTextBindings {
	final legacy:Bool;
	final resolve:String->Dynamic;
	final font:String->String;
	final color:String->Dynamic;
	final borderStyle:(Dynamic,String)->Void;
	final missing:String->Void;
	public function new(legacy:Bool, resolve:String->Dynamic, font:String->String, color:String->Dynamic,
		borderStyle:(Dynamic,String)->Void, missing:String->Void) {
		this.legacy = legacy;this.resolve = resolve;this.font = font;this.color = color;
		this.borderStyle = borderStyle;this.missing = missing;
	}
	function result(ok:Bool, method:String, tag:String):Dynamic {
		if (legacy) return null;
		if (!ok) missing(method + ': Object ' + tag + " doesn't exist!");
		return ok;
	}
	function write(tag:String, field:String, value:Dynamic, method:String):Dynamic {
		var text = resolve(tag);
		if (text != null) Reflect.setProperty(text, field, value);
		return result(text != null, method, tag);
	}
	function read(tag:String, field:String, fallback:Dynamic, method:String):Dynamic {
		var text = resolve(tag);
		if (text != null) {
			var value = Reflect.getProperty(text, field);
			if (legacy || field != 'text' || value != null) return value;
		}
		result(false, method, tag);
		return fallback;
	}
	public function install(variables:Map<String,Dynamic>):Void {
		variables.set('setTextString', function(tag:String, value:String):Dynamic return write(tag, 'text', value, 'setTextString'));
		variables.set('setTextSize', function(tag:String, value:Int):Dynamic return write(tag, 'size', value, 'setTextSize'));
		variables.set('setTextWidth', function(tag:String, value:Float):Dynamic return write(tag, 'fieldWidth', value, 'setTextWidth'));
		variables.set('setTextItalic', function(tag:String, value:Bool):Dynamic return write(tag, 'italic', value, 'setTextItalic'));
		if (!legacy) {
			variables.set('setTextHeight', function(tag:String, value:Float):Dynamic return write(tag, 'fieldHeight', value, 'setTextHeight'));
			variables.set('setTextAutoSize', function(tag:String, value:Bool):Dynamic return write(tag, 'autoSize', value, 'setTextAutoSize'));
		}
		variables.set('setTextFont', function(tag:String, value:String):Dynamic {
			var text = resolve(tag);
			if (text != null) Reflect.setProperty(text, 'font', font(value));
			return result(text != null, 'setTextFont', tag);
		});
		variables.set('setTextColor', function(tag:String, value:String):Dynamic {
			var text = resolve(tag);
			if (text != null) Reflect.setProperty(text, 'color', color(value));
			return result(text != null, 'setTextColor', tag);
		});
		variables.set('setTextAlignment', function(tag:String, value:String = 'left'):Dynamic {
			var text = resolve(tag);
			if (text != null) {
				Reflect.setProperty(text, 'alignment', 'left');
				switch (StringTools.trim(value).toLowerCase()) {
					case 'right': Reflect.setProperty(text, 'alignment', 'right');
					case 'center': Reflect.setProperty(text, 'alignment', 'center');
					case 'justify': if (!legacy) Reflect.setProperty(text, 'alignment', 'justify');
					default:
				}
			}
			return result(text != null, 'setTextAlignment', tag);
		});
		if (legacy) variables.set('setTextBorder', function(tag:String, size:Int, value:String):Dynamic {
			var text = resolve(tag);
			if (text != null) {
				var parsed = color(value);
				Reflect.setProperty(text, 'borderSize', size);
				Reflect.setProperty(text, 'borderColor', parsed);
			}
			return null;
		});
		else variables.set('setTextBorder', function(tag:String, size:Float, value:String, style:String = 'outline'):Dynamic {
			var text = resolve(tag);
			if (text != null) {
				borderStyle(text, size > 0 ? style : 'none');
				if (size > 0) Reflect.setProperty(text, 'borderSize', size);
				Reflect.setProperty(text, 'borderColor', color(value));
			}
			return result(text != null, 'setTextBorder', tag);
		});
		variables.set('getTextString', function(tag:String):Dynamic return read(tag, 'text', null, 'getTextString'));
		variables.set('getTextSize', function(tag:String):Dynamic return read(tag, 'size', -1, 'getTextSize'));
		variables.set('getTextFont', function(tag:String):Dynamic return read(tag, 'font', null, 'getTextFont'));
		variables.set('getTextWidth', function(tag:String):Dynamic return read(tag, 'fieldWidth', 0, 'getTextWidth'));
	}
}
