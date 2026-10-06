package;

import NightmareVisionEventTimeline.NightmareVisionTimelineCallbackErrorReporter;
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartEase;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import NightmareVisionModifier.ModifierType;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartVector;

/** Shared source modifier values and event timelines for one PlayState. */
class NightmareVisionModManager {
	public static inline var CALLBACK_EVENT_BINDING:String = 'CallbackEvent';

	/** Runtime class to bind as the donor-facing `CallbackEvent` type name. */
	public static function callbackEventClass():Dynamic return NightmareVisionCallbackEvent;

	public static function unimplementedModifierApis():Array<String> return [];

	public var lanes:Int = 2;
	public var keys:Int = 4;
	public var registry(default, null):NightmareVisionModifierRegistry;
	/** Compatibility alias to the same authoritative source timeline. */
	public var modifierTimeline(get, never):NightmareVisionEventTimeline;
	function get_modifierTimeline():NightmareVisionEventTimeline return timeline;
	public var receptors:Array<Array<Dynamic>> = [];
	public var timeline:NightmareVisionEventTimeline;
	var ownedTimeline:NightmareVisionEventTimeline;
	public var destroyed(default, null):Bool = false;

	public var register:Map<String, NightmareVisionModifier> = [];
	public var notemodRegister:Map<String, NightmareVisionModifier> = [];
	public var miscmodRegister:Map<String, NightmareVisionModifier> = [];
	public var modArray:Array<NightmareVisionModifier> = [];
	public var activeMods:Array<Array<String>> = [[], []];
	public var sourceRenderer:NightmareVisionModchartRenderer;
	public var renderContext:Void->NightmareVisionModchartContext;
	public var chartKeys:Void->Int;
	var formulaEvaluator:nightmarevision.modchart.NightmareVisionModchartTransform;
	public var loadModifierScript:NightmareVisionModifier->String->NightmareVisionScriptModule;
	public var discoverModifierScripts:Void->Array<String>;
	public var reportModifierError:String->String->Dynamic->Void;
	var executions:haxe.ds.ObjectMap<NightmareVisionModifier, NightmareVisionModifierExecution> = new haxe.ds.ObjectMap();
	var ownedScripts:Array<NightmareVisionScriptedModifier> = [];
	var materialized:Map<String, Bool> = [];

	public function new(?reportError:NightmareVisionTimelineCallbackErrorReporter, keys:Int = 4, lanes:Int = 2, registerBuiltins:Bool = true) {
		this.keys = keys;
		this.lanes = lanes;
		registry = new NightmareVisionModifierRegistry(keys, lanes, false);
		timeline = new NightmareVisionEventTimeline(reportError == null ? reportCallbackError : reportError);
		ownedTimeline = timeline;
		registry.executionNames = function(player) return activeMods[player] == null ? [] : activeMods[player];
		registry.executionEntry = executionEntry;
		registry.hasNameBridge = function(name) return register.exists(name);
		registry.valueBridge = getValue;
		registry.setValueBridge = setValue;
		registry.subValueBridge = function(name, sub, player) return get(name).getSubmodValue(sub, player);
		registry.setSubValueBridge = function(name, sub, value, player) get(name).setSubmodValue(sub, value, player);
		if (registerBuiltins) { registerEssentialModifiers(); registerDefaultModifiers(); }

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
			timeline.update(currentStep);
		}
	}

	/** Pending callbacks capture script interpreters; release them with the state. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		if (timeline != null) timeline.destroy();
		if (ownedTimeline != null && ownedTimeline != timeline) ownedTimeline.destroy();
		ownedTimeline = null;
		receptors = [];
		// A rejected duplicate can still own an interpreter. Release each object once.
		var firstError:Dynamic = null;
		var disposed = new haxe.ds.ObjectMap<NightmareVisionModifier, Bool>();
		for (mod in modArray.concat(cast ownedScripts)) if (mod != null && !disposed.exists(mod)) {
			disposed.set(mod, true);
			try mod.destroy() catch (error:Dynamic) {
				if (firstError == null) firstError = error;
				try diagnostic(mod.getName(), 'destroy', error) catch (_:Dynamic) {}
			}
		}
		modArray = []; ownedScripts = []; register.clear(); notemodRegister.clear(); miscmodRegister.clear();
		activeMods = []; executions.clear(); loadModifierScript = null; discoverModifierScripts = null;
		registry.executionNames = null; registry.executionEntry = null;
		registry.hasNameBridge = null; registry.valueBridge = null; registry.setValueBridge = null;
		registry.subValueBridge = null; registry.setSubValueBridge = null; reportModifierError = null;
		materialized.clear();
		if (sourceRenderer != null) sourceRenderer.destroy();
		sourceRenderer = null; renderContext = null; chartKeys = null; formulaEvaluator = null;
		if (firstError != null) throw firstError;
	}

	function ensureAlive():Void {
		if (destroyed)
			throw 'Nightmare Vision ModManager has been destroyed';
	}

	function ensureCallback(callback:Dynamic):Void {
		if (callback == null || !Reflect.isFunction(callback))
			throw 'Nightmare Vision ModManager callback queue requires a function';
	}

	public function get(name:String):NightmareVisionModifier return register.get(name);
	public function getValue(name:String, player:Int):Float return get(name).getValue(player);
	public function getPercent(name:String, player:Int):Float return get(name).getPercent(player);
	public function setPercent(name:String, value:Float, player:Int = -1):Void setValue(name, value / 100, player);
	public function setValue(modName:String, val:Float, player:Int = -1)
	{
		ensureAlive();
		if (player == -1)
		{
			for (pN in 0...lanes)
				setValue(modName, val, pN);
		}
		else
		{
			var daMod = register.get(modName);
			if (daMod == null)
			{
				diagnostic(modName, 'value', 'mod [$modName] is not real or was not registered');
				// idk add a error u tried using a not real mod
				return;
			}

			var mod = daMod.parent == null ? daMod : daMod.parent;
			var name = mod.getName();
			// optimization shit!! :)
			// thanks 4mbr0s3 for giving an alternative way to do all of this cus andromeda has smth similar in Flexy but like
			// this is a better way to do it
			// (ofc its not EXACTLY what 4mbr0s3 did but.. y'know, it's close to it)

			// so this actually has an issue
			// this doesnt take into account any other submods
			// so if you turn a submod off
			// it turns the parent mod off, too, when it shouldnt
			// so what I need to do is like, check other submods before removing the parent

			if (activeMods[player] == null) activeMods[player] = [];

			register.get(modName).setValue(val, player);

			if (!activeMods[player].contains(name) && mod.shouldExecute(player, val))
			{
				if (daMod.getName() != name) activeMods[player].push(daMod.getName());
				activeMods[player].push(name);
			}
			else if (!mod.shouldExecute(player, val))
			{
				// there is prob a better way to do this
				// i just dont know it
				var modParent = daMod.parent;
				if (modParent == null)
				{
					for (name => mod in daMod.submods)
					{
						modParent = daMod; // because if this gets called at all, there's atleast 1 submod!!
						break;
					}
				}
				if (daMod != modParent) activeMods[player].remove(daMod.getName());
				if (modParent != null)
				{
					if (modParent.shouldExecute(player, modParent.getValue(player)))
					{
						activeMods[player].sort((a, b) -> Std.int(register.get(a).getOrder() - register.get(b).getOrder()));
						return;
					}
					for (subname => submod in modParent.submods)
					{
						if (submod.shouldExecute(player, submod.getValue(player)))
						{
							activeMods[player].sort((a, b) -> Std.int(register.get(a).getOrder() - register.get(b).getOrder()));
							return;
						}
					}
					activeMods[player].remove(modParent.getName());
				}
				else activeMods[player].remove(daMod.getName());
			}

			activeMods[player].sort((a, b) -> Std.int(register.get(a).getOrder() - register.get(b).getOrder()));
		}
	}


	public function diagnostic(name:String, phase:String, error:Dynamic):Void {
		if (reportModifierError != null) reportModifierError(name, phase, error);
		else trace('[nightmare-vision-modifier-error] ' + name + '#' + phase + ': ' + Std.string(error));
	}
	public function ownScript(mod:NightmareVisionScriptedModifier):Void { ensureAlive(); ownedScripts.push(mod); }
	public function configureDimensions(keys:Int, lanes:Int):Void {
		ensureAlive(); this.keys = keys; this.lanes = lanes; registry.configureDimensions(keys, lanes);
		for (mod in modArray) while (mod.percents.length < lanes) mod.percents.push(0);
		while (activeMods.length < lanes) activeMods.push([]);
	}
	public function quickRegister(mod:NightmareVisionModifier):Void registerMod(mod.getName(), mod);
	public function registerMod(name:String, mod:NightmareVisionModifier, registerSubmods:Bool = true):Void {
		ensureAlive();
		var map = mod.getModType() == NOTE_MOD ? notemodRegister : miscmodRegister;
		if (map.exists(name)) { diagnostic(name, 'register', 'Modifier is already registered'); return; }
		map.set(name, mod); register.set(name, mod); timeline.addMod(name); modArray.push(mod);
		if (registerSubmods) for (sub in mod.submods) quickRegister(sub);
		setValue(name, 0);
		modArray.sort((a, b) -> Std.int(a.getOrder() - b.getOrder()));
	}
	public function registerEssentialModifiers():Void {
		registry.registerEssentialModifiers(); materializeBuiltins();
	}
	public function registerDefaultModifiers():Void {
		registry.registerDefaultModifiers(); materializeBuiltins();
		setValue('noteSpawnTime', 2000); setValue('xmod', 1);
		for (i in 0...keys) setValue('xmod' + i, 1);
	}
	function materializeBuiltins():Void {
		for (def in registry.definitions) if (def.parent == null && !materialized.exists(def.name)) {
			materialized.set(def.name, true);
			quickRegister(createBuiltin(def.name));
		}
	}
	function createBuiltin(name:String):NightmareVisionModifier {
		return switch(name) {
			case 'reverse': new NightmareVisionReverseModifier(this);
			case 'confusion': new NightmareVisionConfusionModifier(this);
			case 'perspectiveDONTUSE': new NightmareVisionPerspectiveModifier(this);
			case 'opponentSwap': new NightmareVisionOpponentModifier(this);
			case 'flip': new NightmareVisionFlipModifier(this);
			case 'invert': new NightmareVisionInvertModifier(this);
			case 'drunk': new NightmareVisionDrunkModifier(this);
			case 'beat': new NightmareVisionBeatModifier(this);
			case 'stealth': new NightmareVisionAlphaModifier(this);
			case 'receptorScroll': new NightmareVisionReceptorScrollModifier(this);
			case 'mini': new NightmareVisionScaleModifier(this);
			case 'transformX': new NightmareVisionTransformModifier(this);
			case 'infinite': new NightmareVisionInfinitePathModifier(this);
			case 'boost': new NightmareVisionAccelModifier(this);
			case 'xmod': new NightmareVisionXModifier(this);
			case 'rotateX': new NightmareVisionRotateModifier(this);
			case 'centerrotateX': new NightmareVisionRotateModifier(this, 'center',
				NightmareVisionModchartVector.get(formulaContext().width*.5, formulaContext().height*.5));
			case 'localrotateX': new NightmareVisionLocalRotateModifier(this, 'local');
			case 'noteSpawnTime': new NightmareVisionSubModifier(name, this);
			default: throw '[nightmare-vision-modifier] Unknown builtin: ' + name;
		};
	}
	public function registerScriptedModifiers():Void {
		ensureAlive();
		if (discoverModifierScripts == null) return;
		for (name in discoverModifierScripts()) quickRegister(new NightmareVisionScriptedModifier(this, name));
	}
	public function update(elapsed:Float):Void {
		if (destroyed) return;
		for (mod in modArray) if (mod.active && mod.doesUpdate()) mod.update(elapsed);
	}
	function executionEntry(name:String):Null<NightmareVisionModifierExecution> {
		var mod = notemodRegister.get(name);
		if (mod == null) return null;
		var entry = executions.get(mod);
		if (entry == null) {
			entry = {builtin:null,
				getPosition:mod.getPos,
				value:mod.getValue, subValue:mod.getSubmodValue,
				updateObject:function(beat, obj, pos, player, kind):Void {
					switch (kind) {
						case 'note': mod.updateNote(beat, obj, pos, player);
						case 'receptor': mod.updateReceptor(beat, obj, pos, player);
						case 'noteSplash': mod.updateNoteSplash(beat, obj, pos, player);
						case 'sustainSplash': mod.updateSustainSplash(beat, obj, pos, player);
					}
				}};
			executions.set(mod, entry);
		}
		return entry;
	}
	public function sourceKeyCount():Int return chartKeys == null ? keys : chartKeys();
	/** Renderer-free managers use the existing standalone evaluator defaults. */
	public function formulaContext():NightmareVisionModchartContext {
		ensureAlive();
		return renderContext == null ? new NightmareVisionModchartContext(1280,720,keys,112) : renderContext();
	}
	public function instancePosition(entry:NightmareVisionModifierExecution,obj:Dynamic,pos:NightmareVisionModchartVector,
		time:Float,diff:Float,tDiff:Float,beat:Float,data:Int,player:Int):NightmareVisionModchartVector {
		if(sourceRenderer==null) throw '[nightmare-vision-modifier] No active owner renderer';
		return sourceRenderer.applyInstancePosition(formulaContext(),entry,obj,objectKind(obj),pos,time,diff,tDiff,beat,data,player);
	}
	public function instanceObject(entry:NightmareVisionModifierExecution,obj:Dynamic,kind:String,pos:NightmareVisionModchartVector,beat:Float,player:Int):Void {
		if(sourceRenderer==null) throw '[nightmare-vision-modifier] No active owner renderer';
		sourceRenderer.applyInstanceObject(formulaContext(),entry,obj,kind,pos,beat,player);
	}
	function leafEvaluator():nightmarevision.modchart.NightmareVisionModchartTransform {
		ensureAlive();
		if (sourceRenderer != null) return sourceRenderer.transform;
		if (formulaEvaluator == null) formulaEvaluator = new nightmarevision.modchart.NightmareVisionModchartTransform(registry);
		return formulaEvaluator;
	}
	public function instanceReverseValue(entry:NightmareVisionModifierExecution,data:Int,player:Int,scrolling:Bool=false):Float
		return leafEvaluator().instanceReverseValue(formulaContext(),entry,data,player,scrolling);
	public function alphaBoundary(entry:NightmareVisionModifierExecution,name:String,player:Int):Float
		return leafEvaluator().alphaBoundary(formulaContext(),entry,name,player);
	public function instancePerspectiveVector(entry:NightmareVisionModifierExecution,z:Float,pos:NightmareVisionModchartVector):NightmareVisionModchartVector
		return leafEvaluator().instancePerspectiveVector(formulaContext(),entry,z,pos);
	function context():NightmareVisionModchartContext {
		ensureAlive();
		if (renderContext == null) throw '[nightmare-vision-modifier] No active owner render context';
		return renderContext();
	}
	public function getBaseX(direction:Int, player:Int):Float {
		var c = context();
		return nightmarevision.modchart.NightmareVisionModchartTransform.baseX(c, direction, player);
	}
	public static function getCenterX(player:Int, keys:Int):Float {
		var width:Float = #if flixel flixel.FlxG.width #else 1280 #end;
		var noteWidth:Float = #if flixel Note.swagWidth #else 112 #end;
		return switch (player) { case 0: width - noteWidth * (keys / 2) - 103; case 1: noteWidth * (keys / 2) + 97; default: width * .5 - 3; };
	}
	public static function getStrumX(direction:Int, keys:Int):Float {
		var noteWidth:Float = #if flixel Note.swagWidth #else 112 #end;
		return noteWidth * (direction - keys / 2 + .5);
	}
	public static function getBaseY():Float {
		var noteWidth:Float = #if flixel Note.swagWidth #else 112 #end;
		return noteWidth * .5 + 50;
	}
	public function getBaseVisPosD(diff:Float, songSpeed:Float = 1):Float return .45 * diff * songSpeed;
	public function getVisPos(songPos:Float = 0, strumTime:Float = 0, songSpeed:Float = 1):Float return -getBaseVisPosD(songPos - strumTime, songSpeed);
	function objectKind(obj:Dynamic):String {
		if (Reflect.hasField(obj, 'isSustainNote')) return 'note';
		#if flixel
		if (Std.isOfType(obj, NoteSplash) || Std.isOfType(obj, NightmareVisionNoteSplash)) return 'noteSplash';
		if (Std.isOfType(obj, NoteHoldCover) || Std.isOfType(obj, NightmareVisionSustainSplash)) return 'sustainSplash';
		#end
		return 'receptor';
	}
	public function getPos(time:Float, diff:Float, tDiff:Float, beat:Float, data:Int, player:Int,
		obj:Dynamic, ?exclusions:Array<String>, ?pos:NightmareVisionModchartVector):NightmareVisionModchartVector {
		if (pos == null) pos = NightmareVisionModchartVector.get();
		if (sourceRenderer == null) throw '[nightmare-vision-modifier] No active owner renderer';
		return sourceRenderer.evaluatePosition(context(), obj, objectKind(obj), data, player, time, diff, tDiff, beat, exclusions, pos);
	}
	public function updateObject(beat:Float, obj:Dynamic, pos:NightmareVisionModchartVector, player:Int):Void {
		if (sourceRenderer == null) throw '[nightmare-vision-modifier] No active owner renderer';
		sourceRenderer.applyObject(context(), obj, objectKind(obj), player, beat, pos);
	}
	public function queueSet(step:Float, name:String, value:Float, player:Int = -1):Void {
		ensureAlive();
		if (player == -1) for (p in 0...lanes) queueSet(step, name, value, p);
		else timeline.addEvent(new NightmareVisionSetEvent(step, name, value, player, this));
	}
	public function queueSetP(step:Float, name:String, value:Float, player:Int = -1):Void
		queueSet(step, name, value * 0.01, player);
	public function queueEase(step:Float, endStep:Float, name:String, value:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startValue:Float):Void {
		ensureAlive();
		if (player == -1) for (p in 0...lanes) queueEase(step, endStep, name, value, style, p, startValue);
		else {
			var easeFunc = NightmareVisionModchartEase.resolve(style);
			// The source accepts startVal here but omits it from EaseEvent construction.
			timeline.addEvent(new NightmareVisionEaseEvent(step, endStep, name, value, easeFunc, player, this));
		}
	}
	public function queueEaseP(step:Float, endStep:Float, name:String, value:Float,
		style:Dynamic = 'linear', player:Int = -1, ?startValue:Float):Void
		queueEase(step, endStep, name, value * 0.01, style, player, startValue == null ? null : startValue * 0.01);
	static function reportCallbackError(event:NightmareVisionCallbackEvent, error:Dynamic):Void
		trace('[nightmare-vision-mod-callback-error] step=' + event.executionStep + ': ' + Std.string(error));

}
