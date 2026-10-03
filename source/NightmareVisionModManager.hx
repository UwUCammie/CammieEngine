package;

import NightmareVisionCallbackTimeline.NightmareVisionCallbackErrorReporter;
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartTimeline;

/** Shared source modifier values and event timelines for one PlayState. */
class NightmareVisionModManager {
	public static inline var CALLBACK_EVENT_BINDING:String = 'CallbackEvent';

	/** Runtime class to bind as the donor-facing `CallbackEvent` type name. */
	public static function callbackEventClass():Dynamic return NightmareVisionCallbackEvent;

	/** Supplied ModManager surface that this callback-focused adapter does not implement. */
	public static function unimplementedModifierApis():Array<String> return [
		'quickRegister', 'registerMod', 'registerScriptedModifiers'
	];

	public var lanes(default, null):Int = 2;
	public var keys(default, null):Int = 4;
	public var registry(default, null):NightmareVisionModifierRegistry;
	public var modifierTimeline(default, null):NightmareVisionModchartTimeline;
	public var receptors:Array<Array<Dynamic>> = [];
	public var timeline(default, null):NightmareVisionCallbackTimeline;
	public var destroyed(default, null):Bool = false;

	public function new(?reportError:NightmareVisionCallbackErrorReporter, keys:Int = 4, lanes:Int = 2) {
		this.keys = keys;
		this.lanes = lanes;
		registry = new NightmareVisionModifierRegistry(keys, lanes);
		modifierTimeline = new NightmareVisionModchartTimeline(registry);
		timeline = new NightmareVisionCallbackTimeline(reportError);
	}

	public function queueFuncOnce(step:Float, callback:Dynamic):Void {
		ensureAlive();
		ensureCallback(callback);
		timeline.addEvent(new NightmareVisionCallbackEvent(step, callback, this));
	}

	public function queueFunc(step:Float, endStep:Float, callback:Dynamic):Void {
		ensureAlive();
		ensureCallback(callback);
		timeline.addEvent(new NightmareVisionStepCallbackEvent(step, endStep, callback, this));
	}

	/** Called from the owning PlayState once per update with its decimal song step. */
	public function updateTimeline(currentStep:Float):Void {
		if (!destroyed) {
			modifierTimeline.update(currentStep);
			timeline.update(currentStep);
		}
	}

	/** Pending callbacks capture script interpreters; release them with the state. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		timeline.destroy();
		modifierTimeline.destroy();
		receptors = [];
	}

	function ensureAlive():Void {
		if (destroyed)
			throw 'Nightmare Vision ModManager has been destroyed';
	}

	function ensureCallback(callback:Dynamic):Void {
		if (callback == null || !Reflect.isFunction(callback))
			throw 'Nightmare Vision ModManager callback queue requires a function';
	}

	function unsupportedModifierApi(name:String):Dynamic {
		throw 'Nightmare Vision ModManager.' + name
			+ ' is not implemented by the shared runtime; the request was rejected, not ignored.';
		return null;
	}

	public function getValue(name:String, player:Int):Float return registry.value(name, player);
	public function getPercent(name:String, player:Int):Float return registry.percent(name, player);
	public function get(name:String):Dynamic {
		if (!registry.isRegistered(name)) return null;
		return {
			getName:function():String return name,
			getValue:function(player:Int):Float return registry.value(name, player),
			getPercent:function(player:Int):Float return registry.percent(name, player),
			getSubmodValue:function(sub:String, player:Int):Float return registry.getSubmodValue(name, sub, player),
			setValue:function(value:Float, player:Int):Void registry.setValue(name, value, player),
			setPercent:function(value:Float, player:Int):Void registry.setPercent(name, value, player)
		};
	}
	public function setValue(name:String, value:Float, player:Int = -1):Void {
		ensureAlive(); registry.setValue(name, value, player);
	}
	public function setPercent(name:String, value:Float, player:Int = -1):Void {
		ensureAlive(); registry.setPercent(name, value, player);
	}
	public function queueSet(step:Float, name:String, value:Float, player:Int = -1):Void {
		ensureAlive(); modifierTimeline.queueSet(step, name, value, player);
	}
	public function queueSetP(step:Float, name:String, value:Float, player:Int = -1):Void {
		ensureAlive(); modifierTimeline.queueSetP(step, name, value, player);
	}
	public function queueEase(step:Float, endStep:Float, name:String, value:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startValue:Float):Void {
		ensureAlive(); modifierTimeline.queueEase(step, endStep, name, value, style, player, startValue);
	}
	public function queueEaseP(step:Float, endStep:Float, name:String, value:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startValue:Float):Void {
		ensureAlive(); modifierTimeline.queueEaseP(step, endStep, name, value, style, player, startValue);
	}
}
