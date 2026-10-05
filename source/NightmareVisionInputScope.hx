package;

import flixel.FlxG;
import flixel.input.gamepad.FlxGamepad;
import nightmarevision.input.NightmareVisionInputEnums.Action;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;

/** Scene-owned device hooks; source class views retain only an owner key. */
@:keep
class NightmareVisionInputScope {
	static var actionLists:Map<String, Array<Action>> = new Map();
	public var ownerRoot(default, null):String;
	public var controls(get, set):NightmareVisionControls;
	var _controls:NightmareVisionControls;
	public var input(get, set):NightmareVisionInputSystem;
	var _input:NightmareVisionInputSystem;
	public var onInputChanged:NightmareVisionInputSystem->NightmareVisionInputSystem->Void;
	public var actionList(get, set):Array<Action>;
	var prefs:Dynamic;
	var systems:Array<NightmareVisionInputSystem> = [];
	var ownedControls:Array<NightmareVisionControls> = [];
	var released:Bool = false;
	var connected:Bool = false;
	var attachDevices:Bool;

	public function new(ownerRoot:String, prefs:Dynamic, attachDevices:Bool = true, createDefaultInput:Bool = true) {
		this.ownerRoot = ownerRoot;
		this.prefs = prefs;
		this.attachDevices = attachDevices;
		if (!actionLists.exists(ownerRoot)) actionLists.set(ownerRoot,
			['note_left', 'note_down', 'note_up', 'note_right']);
		resetControls();
		if (createDefaultInput) input = createInput(controls);
		#if FLX_GAMEPAD
		if (attachDevices && FlxG.gamepads != null) {
			FlxG.gamepads.deviceConnected.add(gamepadConnected);
			FlxG.gamepads.deviceDisconnected.add(gamepadDisconnected);
			connected = true;
		}
		#end
	}
	function get_controls():NightmareVisionControls return _controls;
	function get_input():NightmareVisionInputSystem return _input;
	function set_controls(value:NightmareVisionControls):NightmareVisionControls {
		ensureAlive();
		if (value != null && ownedControls.indexOf(value) < 0) ownedControls.push(value);
		return _controls = value;
	}
	function set_input(value:NightmareVisionInputSystem):NightmareVisionInputSystem {
		ensureAlive();
		var old = input;
		if (value != null && systems.indexOf(value) < 0) systems.push(value);
		_input = value;
		if (onInputChanged != null && old != value) onInputChanged(old, value);
		return value;
	}

	function ensureAlive():Void if (released) throw '[nightmare-vision-input] Released owner';
	function get_actionList():Array<Action> {ensureAlive(); return actionLists.get(ownerRoot);}
	function set_actionList(value:Array<Action>):Array<Action> {
		ensureAlive(); actionLists.set(ownerRoot, value); return value;
	}
	public function createControls(name:String, scheme:KeyboardScheme = None):NightmareVisionControls {
		ensureAlive();
		var value = new NightmareVisionControls(name, scheme, prefs);
		ownedControls.push(value);
		return value;
	}
	public function resetControls():Void {
		ensureAlive();
		controls = createControls('player', Solo);
		#if FLX_GAMEPAD
		if (attachDevices && FlxG.gamepads != null) for (id in 0...FlxG.gamepads.numActiveGamepads)
			if (FlxG.gamepads.getByID(id) != null) controls.addDefaultGamepad(id);
		#end
		controls.customActions.clear();
		// ControlsSubState's group/UI reset belongs to the future imported-menu host.
	}
	public function createInput(?value:NightmareVisionControls):NightmareVisionInputSystem {
		ensureAlive();
		var system = new NightmareVisionInputSystem(value == null ? controls : value, attachDevices, actionList);
		systems.push(system);
		return system;
	}
	function gamepadConnected(gamepad:FlxGamepad):Void {
		if (!released && controls != null) controls.addDefaultGamepad(gamepad.id);
	}
	function gamepadDisconnected(gamepad:FlxGamepad):Void {
		if (!released && controls != null) controls.removeGamepad(gamepad.id);
	}
	public function destroy():Void {
		if (released) return;
		released = true;
		#if FLX_GAMEPAD
		if (connected) {
			FlxG.gamepads.deviceConnected.remove(gamepadConnected);
			FlxG.gamepads.deviceDisconnected.remove(gamepadDisconnected);
		}
		#end
		for (system in systems) system.releaseOwner();
		for (value in ownedControls) value.destroy();
		systems.resize(0); ownedControls.resize(0);
		onInputChanged = null;
		// Avoid setter admission after the lifetime has ended.
		_controls = null;
		_input = null;
		prefs = null;
	}
}
