package;

#if sys
import flixel.FlxG;
import lime.app.Application;
import sys.io.File;

private typedef StyleStep = {
	var wait:Float;
	@:optional var shot:String;
	@:optional var run:Void->Void;
	@:optional var until:Void->Bool;
}

/**
	Opt-in native capture of the menus that share the Freeplay look
	(`--verify-menu-style --menu-style-capture <path stem>`,
	run together with `--smoke-freeplay`).

	It starts on the real Freeplay screen, then opens the options sections, an
	options section, the save slots, the main menu, the importer and its
	package-name prompt with real key events and the real states, and saves a
	framebuffer read of each from the hidden window as `<stem>-<name>.png`.
	`--menu-style-only a,b` keeps only the named captures. Nothing is changed in
	any setting: the probe only moves the cursor and opens screens.
*/
@:access(RuntimeSmokeHarness)
class RuntimeMenuStyleProbe {
	static var steps:Array<StyleStep> = null;
	static var index:Int = 0;
	static var stepStarted:Float = 0;
	static var began:Float = 0;
	static var capturePending:String = null;
	static var captureHooked:Bool = false;
	static var only:Array<String> = null;

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.args().indexOf('--verify-menu-style') >= 0;

	static function argument(name:String):String {
		var args = Sys.args();
		var at = args.indexOf(name);
		return at < 0 || at + 1 >= args.length ? null : args[at + 1];
	}

	static function key(name:String):StyleStep return {wait: 0.7, run: function() RuntimeSmokeHarness.simulateKey(name)};

	static function inState(kind:Class<Dynamic>):Void->Bool return function() return Std.isOfType(FlxG.state, kind);

	static function plan():Array<StyleStep> {
		var list:Array<StyleStep> = [
			{wait: 3.0, until: inState(FreeplayState), shot: 'freeplay'},
			{wait: 2.0, shot: 'options-sections', until: inState(SaveDataState), run: function() {
				SaveDataState.prevPath = 'title';
				LoadingState.loadAndSwitchState(new SaveDataState());
			}},
			key('down'),
			{wait: 0.9, shot: 'options-sections-moved'},
			key('enter'),
			{wait: 1.2, shot: 'options-rows'},
			key('down'), key('down'),
			{wait: 0.9, shot: 'options-rows-moved'},
			key('escape'),
			key('left'),
			{wait: 1.2, shot: 'options-saves'},
			key('enter'),
			{wait: 0.9, shot: 'options-saves-selected'},
			key('escape'),
			{wait: 2.5, shot: 'main-menu', until: inState(MainMenuState), run: function() {
				LoadingState.loadAndSwitchState(new MainMenuState());
			}},
			key('down'),
			{wait: 0.9, shot: 'main-menu-freeplay'},
			key('down'),
			{wait: 0.9, shot: 'main-menu-options'},
			key('down'),
			{wait: 0.9, shot: 'main-menu-import'},
			{wait: 2.0, shot: 'import', until: inState(ImportSettingsState), run: function() {
				LoadingState.loadAndSwitchState(new ImportSettingsState());
			}},
			{wait: 1.2, shot: 'import-name', run: function() {
				FlxG.state.openSubState(new ImportPackageNameSubState(
					[{root: 'C:/Sample Mods/Example Package', suggestedName: 'Example Package'}], function(names) {}));
			}},
		];
		if (only == null) return list;
		// A capture that is not wanted still runs, so the later screens are reached.
		for (step in list) if (step.shot != null && only.indexOf(step.shot) < 0) Reflect.deleteField(step, 'shot');
		return list;
	}

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			var now = haxe.Timer.stamp();
			if (began == 0) {
				began = now;
				var names = argument('--menu-style-only');
				if (names != null) only = names.split(',');
				steps = plan();
			}
			if (now - began > 240) throw 'Menu style probe timed out at step ' + index;
			if (capturePending != null) return;
			FlxG.sound.muted = true;
			if (index >= steps.length) {
				Application.current.window.onRender.remove(onRendered);
				RuntimeSmokeHarness.emit('menu_style_verified', {steps: steps.length});
				RuntimeSmokeHarness.succeed();
				return;
			}
			var step = steps[index];
			if (stepStarted == 0) {
				if (step.until != null && !step.until() && step.run == null) return;
				RuntimeSmokeHarness.emit('menu_style_step', {step: index, shot: step.shot, state: Type.getClassName(Type.getClass(FlxG.state))});
				if (step.run != null) step.run();
				stepStarted = now;
			}
			if (step.until != null && !step.until()) {
				if (now - stepStarted > 40) throw 'Menu style probe waited too long at step ' + index;
				return;
			}
			if (now - stepStarted < step.wait) return;
			if (step.shot != null) {
				hookCapture();
				capturePending = step.shot;
				return;
			}
			index++;
			stepStarted = 0;
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('menu-style', Std.string(error));
		}
	}

	static function hookCapture():Void {
		if (captureHooked) return;
		captureHooked = true;
		Application.current.window.onRender.add(onRendered, false, -1000);
	}

	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (capturePending == null || RuntimeSmokeHarness.finished) return;
		try {
			var kind = capturePending;
			var stem = argument('--menu-style-capture');
			if (stem == null) throw 'Menu style probe needs --menu-style-capture <path stem>';
			var image = Application.current.window.readPixels();
			if (image == null || image.width <= 0 || image.height <= 0) throw 'Empty native menu framebuffer';
			var path = stem + '-' + kind + '.png';
			RuntimeSmokeHarness.ensureParent(path);
			File.saveBytes(path, image.encode());
			RuntimeSmokeHarness.emit('menu_style_capture', {kind: kind, path: path, width: image.width, height: image.height,
				state: Type.getClassName(Type.getClass(FlxG.state)), viewportWidth: FlxG.width, viewportHeight: FlxG.height});
			capturePending = null;
			index++;
			stepStarted = 0;
		} catch (error:Dynamic) {
			Application.current.window.onRender.remove(onRendered);
			RuntimeSmokeHarness.fail('menu-style-render', Std.string(error));
		}
	}
}
#end
