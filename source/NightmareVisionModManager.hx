package;

import NightmareVisionCallbackTimeline.NightmareVisionCallbackErrorReporter;

/**
 * Shared per-PlayState callback timeline for Nightmare Vision scripts.
 * Modifier value/ease evaluation is a separate subsystem and is not faked by
 * this callback scheduler; calls to those APIs fail with an explicit message.
 */
class NightmareVisionModManager {
	public static inline var CALLBACK_EVENT_BINDING:String = 'CallbackEvent';

	/** Runtime class to bind as the donor-facing `CallbackEvent` type name. */
	public static function callbackEventClass():Dynamic return NightmareVisionCallbackEvent;

	/** Supplied ModManager surface that this callback-focused adapter does not implement. */
	public static function unimplementedModifierApis():Array<String> return [
		'get', 'getPercent', 'getValue', 'setPercent', 'setValue',
		'queueSet', 'queueSetP', 'queueEase', 'queueEaseP',
		'quickRegister', 'registerMod', 'registerEssentialModifiers',
		'registerDefaultModifiers', 'registerScriptedModifiers', 'update',
		'updateObject', 'getPos', 'getBaseX', 'getCenterX', 'getStrumX',
		'getBaseY', 'getBaseVisPosD', 'getVisPos'
	];

	public var lanes:Int = 2;
	public var keys:Int = 4;
	public var receptors:Array<Array<Dynamic>> = [];
	public var timeline(default, null):NightmareVisionCallbackTimeline;
	public var destroyed(default, null):Bool = false;

	public function new(?reportError:NightmareVisionCallbackErrorReporter) {
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
		if (!destroyed) timeline.update(currentStep);
	}

	/** Pending callbacks capture script interpreters; release them with the state. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		timeline.destroy();
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

	// These are present in the supplied source ModManager and retained D-Sides
	// scripts, but require the separate modifier registry/evaluation pipeline.
	// Explicit failures keep partial support visible instead of silently lying.
	public function setValue(name:Dynamic, value:Dynamic, player:Dynamic = -1):Dynamic return unsupportedModifierApi('setValue');
	public function setPercent(name:Dynamic, value:Dynamic, player:Dynamic = -1):Dynamic return unsupportedModifierApi('setPercent');
	public function queueSet(step:Dynamic, name:Dynamic, value:Dynamic, player:Dynamic = -1):Dynamic return unsupportedModifierApi('queueSet');
	public function queueSetP(step:Dynamic, name:Dynamic, value:Dynamic, player:Dynamic = -1):Dynamic return unsupportedModifierApi('queueSetP');
	public function queueEase(step:Dynamic, endStep:Dynamic, name:Dynamic, value:Dynamic,
		style:Dynamic = 'linear', player:Dynamic = -1, startValue:Dynamic = null):Dynamic
		return unsupportedModifierApi('queueEase');
	public function queueEaseP(step:Dynamic, endStep:Dynamic, name:Dynamic, value:Dynamic,
		style:Dynamic = 'linear', player:Dynamic = -1, startValue:Dynamic = null):Dynamic
		return unsupportedModifierApi('queueEaseP');
}
