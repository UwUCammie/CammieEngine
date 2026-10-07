package;

/** Live source option metadata. Script callbacks stay in memory, never in a save. */
@:keep
class NightmareVisionSourceModOption {
	public var idx:Int = -1;
	public var key:String;
	public var type:String;
	public var value:Dynamic;
	public var defaultValue:Dynamic;
	public var settings:Dynamic;

	public function new(key:String, type:String, value:Dynamic, ?settings:Dynamic) {
		this.key = key;
		this.type = type.toLowerCase();
		this.value = this.defaultValue = value;
		this.settings = settings == null ? {} : settings;
		validateSettings();
	}

	public function validateSettings():Void {
		for (entry in [
			{name:'description', value:cast 'No description provided.'},
			{name:'onChange', value:null}, {name:'callback', value:null},
			{name:'options', value:cast ['Option 1', 'Option 2']},
			{name:'displayFormat', value:cast '%v'}, {name:'stepSize', value:cast 1},
			{name:'minValue', value:null}, {name:'maxValue', value:null},
			{name:'decimals', value:cast 1}
		]) if (Reflect.field(settings, entry.name) == null) Reflect.setField(settings, entry.name, entry.value);
	}

	public function toString():String
		return '(key: $key, type: $type, value: $value, idx: $idx)';

	public function destroy():Void {
		key = ''; value = null; defaultValue = null; type = ''; idx = -1; settings = null;
	}
}
