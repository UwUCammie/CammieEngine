package;

import flixel.FlxBasic;
import flixel.FlxG;

/** Hot reload controls bound to one selected source owner. */
@:keep
class NightmareVisionHotReloadPlugin extends FlxBasic {
	final prefs:Dynamic;
	final getControls:Void->Dynamic;
	final reset:Void->Void;
	final repopulate:Void->Void;
	final applyConfig:Void->Void;
	final clearOwnerCache:Void->Void;
	var cacheClearPending:Bool = false;
	var released:Bool = false;

	public function new(prefs:Dynamic, getControls:Void->Dynamic, reset:Void->Void,
		repopulate:Void->Void, applyConfig:Void->Void, clearOwnerCache:Void->Void) {
		super();
		if (getControls == null || reset == null || repopulate == null || applyConfig == null || clearOwnerCache == null)
			throw '[nmv-bootstrap-service] Hot reload requires controls and owner callbacks';
		this.prefs = prefs;
		this.getControls = getControls;
		this.reset = reset;
		this.repopulate = repopulate;
		this.applyConfig = applyConfig;
		this.clearOwnerCache = clearOwnerCache;
		visible = false;
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (released) return;
		#if !debug
		if (Reflect.field(prefs, 'inDevMode') != true) return;
		#end
		var controls = getControls();
		if (controls == null) throw '[nmv-bootstrap-service] Hot reload controls are unavailable';

		if (Reflect.getProperty(controls, 'SOFT_RELOAD') == true) {
			reset();
			applyConfig();
		}

		if (Reflect.getProperty(controls, 'HARD_RELOAD') == true) {
			FlxG.signals.preStateCreate.addOnce(clearBeforeStateCreate);
			cacheClearPending = true;
			repopulate();
			reset();
			applyConfig();
		}
	}

	function clearBeforeStateCreate(_):Void {
		cacheClearPending = false;
		if (!released) clearOwnerCache();
	}

	public function release():Void {
		if (released) return;
		released = true;
		if (cacheClearPending) FlxG.signals.preStateCreate.remove(clearBeforeStateCreate);
		cacheClearPending = false;
		FlxG.plugins.remove(this);
		destroy();
	}
}
