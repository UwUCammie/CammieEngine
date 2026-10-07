package;

import flixel.FlxBasic;
import flixel.FlxG;

/** Fullscreen action and owner-save write from the donor plugin. */
@:keep
class NightmareVisionFullScreenPlugin extends FlxBasic {
	final getControls:Void->Dynamic;
	final writeOwnerSave:String->Dynamic->Void;
	var restoreFullscreen:Bool;
	var lastSourceFullscreen:Bool;
	var hasSourceFullscreen:Bool = false;
	var released:Bool = false;

	public function new(getControls:Void->Dynamic, writeOwnerSave:String->Dynamic->Void) {
		super();
		if (getControls == null || writeOwnerSave == null)
			throw '[nmv-bootstrap-service] Fullscreen requires owner controls and save writer';
		this.getControls = getControls;
		this.writeOwnerSave = writeOwnerSave;
		restoreFullscreen = FlxG.fullscreen;
		lastSourceFullscreen = restoreFullscreen;
		visible = false;
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (released) return;
		var controls = getControls();
		if (controls == null) throw '[nmv-bootstrap-service] Fullscreen controls are unavailable';
		if (Reflect.getProperty(controls, 'FULLSCREEN') == true) {
			if (!hasSourceFullscreen) restoreFullscreen = FlxG.fullscreen;
			FlxG.fullscreen = !FlxG.fullscreen;
			lastSourceFullscreen = FlxG.fullscreen;
			hasSourceFullscreen = true;
		} else if (FlxG.fullscreen != lastSourceFullscreen) {
			// A native or unrelated owner changed this while the plugin was idle.
			restoreFullscreen = FlxG.fullscreen;
			lastSourceFullscreen = FlxG.fullscreen;
			hasSourceFullscreen = false;
		}
		writeOwnerSave('fullscreen', FlxG.fullscreen);
	}

	public function release():Void {
		if (released) return;
		released = true;
		if (hasSourceFullscreen && FlxG.fullscreen == lastSourceFullscreen)
			FlxG.fullscreen = restoreFullscreen;
		FlxG.plugins.remove(this);
		destroy();
	}
}
