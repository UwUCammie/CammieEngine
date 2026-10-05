package;

import nightmarevision.input.NightmareVisionInputEnums.Action;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;

/** Each interpreter resolves live input only for its own selected import. */
@:keep
class NightmareVisionInputBindings {
	public static function install(interp:NightmareVisionScriptInterp, owner:String,
		resolve:String->NightmareVisionInputScope, ?resolveHost:String->Dynamic):Void {
		var find = function():NightmareVisionInputScope {
			var scope = resolve(owner);
			if (scope == null) throw '[nightmare-vision-input] No active input scene for owner: ' + owner;
			return scope;
		};
		var target:Void->Dynamic = resolveHost == null ? null : function() return resolveHost(owner);
		interp.bindLiveValue('controls', function() return find().controls, null, target);
		interp.bindLiveValue('input', function() return find().input, function(value) return find().input = value, target);
		var controls = new NightmareVisionControlsClassView(find);
		var system = new NightmareVisionInputSystemClassView(find);
		interp.variables.set('Controls', controls);
		interp.variables.set('InputSystem', system);
		interp.variables.set('InputEvent', NightmareVisionInputEvent);
		interp.bindImport('funkin.input.Controls', controls);
		interp.bindImport('funkin.input.InputSystem', system);
		interp.bindImport('funkin.input.InputEvent', NightmareVisionInputEvent);
		var enums:Map<String, Dynamic> = [
			'Control' => nightmarevision.input.NightmareVisionInputEnums.Control,
			'Device' => nightmarevision.input.NightmareVisionInputEnums.Device,
			'KeyboardScheme' => nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme
		];
		for (name => type in enums) {
			interp.variables.set(name, type);
			interp.bindImport('funkin.input.Controls.' + name, type);
		}
		// Action is an erased String abstract. Its runtime constants are strings.
		var actions:Dynamic = {};
		for (base in ['ui_up','ui_left','ui_right','ui_down','note_up','note_left','note_right','note_down','note_dodge']) {
			Reflect.setField(actions, base.toUpperCase(), base);
			Reflect.setField(actions, base.toUpperCase() + '_P', base + '-press');
			Reflect.setField(actions, base.toUpperCase() + '_R', base + '-release');
		}
		for (base in ['accept','back','pause','reset','fullscreen','switch_debug_display','soft_reload','hard_reload'])
			Reflect.setField(actions, base.toUpperCase(), base);
		interp.variables.set('Action', actions);
		interp.bindImport('funkin.input.Controls.Action', actions);
		interp.bindConstructorFactory(controls, function(args:Array<Dynamic>):Dynamic {
			var name:String = args != null && args.length > 0 ? args[0] : null;
			var scheme:KeyboardScheme = args != null && args.length > 1 && args[1] != null ? args[1] : None;
			return find().createControls(name, scheme);
		}, null);
		interp.bindConstructorFactory(system, function(args:Array<Dynamic>):Dynamic
			return find().createInput(args != null && args.length > 0 ? args[0] : null), null);
	}
}

@:keep
class NightmareVisionControlsClassView {
	var resolve:Void->NightmareVisionInputScope;
	public var instance(get, set):NightmareVisionControls;
	public function new(resolve:Void->NightmareVisionInputScope) this.resolve = resolve;
	function get_instance():NightmareVisionControls return resolve().controls;
	function set_instance(value:NightmareVisionControls):NightmareVisionControls return resolve().controls = value;
	public function init():Void resolve().resetControls();
}

@:keep
class NightmareVisionInputSystemClassView {
	var resolve:Void->NightmareVisionInputScope;
	public var ACTION_LIST(get, set):Array<Action>;
	public function new(resolve:Void->NightmareVisionInputScope) this.resolve = resolve;
	function get_ACTION_LIST():Array<Action> return resolve().actionList;
	function set_ACTION_LIST(value:Array<Action>):Array<Action> return resolve().actionList = value;
}
