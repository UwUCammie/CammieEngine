package;

import haxe.ds.ObjectMap;
#if flixel
import flixel.input.keyboard.FlxKey;
#end

private typedef CompatScriptInputBinding = {
	var nativeFlxG:Dynamic;
	var nativeKeys:Dynamic;
	var snapshot:CompatScriptInputSnapshot;
	var views:Array<NightmareVisionFlxGView>;
}

/** FlxG adapter that forwards native static/instance fields except `save`,
	which is replaced with the selected owner's save facade. The native delegate
	stays in a host-side identity table and is removed with its save lifetime. */
class NightmareVisionFlxGView {
	static var nativeDelegates:ObjectMap<NightmareVisionFlxGView, Dynamic> = new ObjectMap();
	static var viewsBySave:ObjectMap<NightmareVisionSaveFacade, Array<NightmareVisionFlxGView>> = new ObjectMap();
	static var viewsByClock:ObjectMap<CompatScriptClock, Array<NightmareVisionFlxGView>> = new ObjectMap();
	static var inputsByClock:ObjectMap<CompatScriptClock, Array<CompatScriptInputBinding>> = new ObjectMap();
	public final save:NightmareVisionSaveFacade;
	final inputKeyCodes:Map<String, Int>;
	var scriptClock:CompatScriptClock;
	var inputBinding:CompatScriptInputBinding;
	var sourceTickActive:Bool = false;
	var sourceElapsed:Float = 0;
	var sourceKeys:Dynamic;

	public function new(nativeFlxG:Dynamic, save:NightmareVisionSaveFacade,
		?clock:CompatScriptClock, ?keyCodes:Map<String, Int>) {
		if (nativeFlxG == null || save == null)
			throw '[nightmare-vision-save] FlxG view requires the native API and owner save facade';
		this.save = save;
		inputKeyCodes = keyCodes == null ? flixelKeyCodes() : keyCodes;
		nativeDelegates.set(this, nativeFlxG);
		var views = viewsBySave.get(save);
		if (views == null) {
			views = [];
			viewsBySave.set(save, views);
		}
		views.push(this);
		if (clock != null) bindSourceClock(clock);
	}

	public function getField(name:String):Dynamic {
		if (name == null || name == '') return null;
		if (name == 'save') return save;
		if (sourceTickActive) {
			if (name == 'elapsed') return sourceElapsed;
			if (name == 'keys') return sourceKeys;
		}
		return Reflect.getProperty(getNativeDelegate(), name);
	}

	public function setField(name:String, value:Dynamic):Dynamic {
		if (name == 'save')
			throw '[nightmare-vision-save] Refused to replace the owner-scoped FlxG.save view';
		if (name == null || name == '')
			throw '[nightmare-vision-save] Refused an invalid FlxG field';
		Reflect.setProperty(getNativeDelegate(), name, value);
		return value;
	}

	/** Bind this per-interpreter view to the PlayState-owned shared source clock. */
	public function bindSourceClock(clock:CompatScriptClock):Void {
		if (clock == null) throw '[compat-script-clock] FlxG view requires a source clock';
		if (scriptClock == clock) return;
		removeFromClock();
		scriptClock = clock;
		var views = viewsByClock.get(clock);
		if (views == null) {
			views = [];
			viewsByClock.set(clock, views);
		}
		views.push(this);
		var bindings = inputsByClock.get(clock);
		if (bindings == null) {
			bindings = [];
			inputsByClock.set(clock, bindings);
		}
		var nativeFlxG = getNativeDelegate();
		for (binding in bindings) {
			if (binding.nativeFlxG == nativeFlxG) {
				inputBinding = binding;
				break;
			}
		}
		if (inputBinding == null) {
			inputBinding = {
				nativeFlxG:nativeFlxG,
				nativeKeys:Reflect.getProperty(nativeFlxG, 'keys'),
				snapshot:new CompatScriptInputSnapshot(inputKeyCodes),
				views:[]
			};
			bindings.push(inputBinding);
		}
		inputBinding.views.push(this);
	}

	/** Sample native key edges at every render/update frame, even when the 60 Hz
	 * script clock has not accumulated a complete tick yet. */
	public static function captureSourceFrame(clock:CompatScriptClock):Void {
		for (binding in inputsForClock(clock)) {
			binding.nativeKeys = Reflect.getProperty(binding.nativeFlxG, 'keys');
			binding.snapshot.sample(binding.nativeKeys);
		}
	}

	/** Run one matching onUpdate or onUpdatePost callback against a fixed source
	 * elapsed value and stable key snapshot. Call again with the same tick index
	 * for the paired post callback; buffered edges remain until batch completion. */
	public static function runSourceTick(clock:CompatScriptClock, tickIndex:Int,
		tickCount:Int, callback:Void->Void):Void {
		var views = viewsForClock(clock);
		for (view in views) view.beginSourceTick(tickIndex, tickCount);
		var failed = false;
		var failure:Dynamic = null;
		try callback() catch (error:Dynamic) {
			failed = true;
			failure = error;
		}
		for (view in views) view.endSourceTick();
		if (failed) throw failure;
	}

	/** Drop latched edges after both phases of a batch have completed. */
	public static function finishSourceBatch(clock:CompatScriptClock, tickCount:Int):Void {
		if (tickCount <= 0) return;
		for (binding in inputsForClock(clock)) binding.snapshot.finishSourceBatch();
	}

	/** Remove host-side native references when the owner save facade is released. */
	public static function releaseForSave(save:NightmareVisionSaveFacade):Void {
		var views = viewsBySave.get(save);
		if (views == null) return;
		for (view in views.copy()) view.release();
		viewsBySave.remove(save);
	}

	public function release():Void {
		nativeDelegates.remove(this);
		removeFromClock();
		var views = viewsBySave.get(save);
		if (views != null) {
			views.remove(this);
			if (views.length == 0) viewsBySave.remove(save);
		}
	}

	function beginSourceTick(tickIndex:Int, tickCount:Int):Void {
		if (inputBinding == null)
			throw '[compat-script-clock] FlxG view is not bound to a shared input snapshot';
		sourceElapsed = scriptClock.tickElapsed;
		sourceKeys = inputBinding.snapshot.view(inputBinding.nativeKeys, tickIndex, tickCount);
		sourceTickActive = true;
	}

	function endSourceTick():Void {
		sourceTickActive = false;
		sourceKeys = null;
	}

	function removeFromClock():Void {
		if (scriptClock == null) return;
		var views = viewsByClock.get(scriptClock);
		if (views != null) {
			views.remove(this);
			if (views.length == 0) viewsByClock.remove(scriptClock);
		}
		var bindings = inputsByClock.get(scriptClock);
		if (inputBinding != null) {
			inputBinding.views.remove(this);
			if (inputBinding.views.length == 0 && bindings != null) {
				bindings.remove(inputBinding);
				if (bindings.length == 0) inputsByClock.remove(scriptClock);
			}
		}
		inputBinding = null;
		scriptClock = null;
		sourceTickActive = false;
		sourceKeys = null;
	}

	static function viewsForClock(clock:CompatScriptClock):Array<NightmareVisionFlxGView> {
		var views = clock == null ? null : viewsByClock.get(clock);
		return views == null ? [] : views.copy();
	}

	static function inputsForClock(clock:CompatScriptClock):Array<CompatScriptInputBinding> {
		var bindings = clock == null ? null : inputsByClock.get(clock);
		return bindings == null ? [] : bindings.copy();
	}

	static function flixelKeyCodes():Map<String, Int> {
		var result:Map<String, Int> = new Map();
		#if flixel
		for (name in FlxKey.fromStringMap.keys())
			result.set(name, cast FlxKey.fromStringMap.get(name));
		#end
		return result;
	}

	function getNativeDelegate():Dynamic {
		var nativeFlxG = nativeDelegates.get(this);
		if (nativeFlxG == null)
			throw '[nightmare-vision-save] FlxG view has been released';
		return nativeFlxG;
	}
}
