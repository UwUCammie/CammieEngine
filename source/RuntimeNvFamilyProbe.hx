package;

#if sys
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.graphics.FlxGraphic;
import crowplexus.hscript.Parser;
import lime.app.Application;
import sys.io.File;

/** Opt-in native check of source selection, asset identity and borrowed lifetime. */
@:access(RuntimeSmokeHarness)
class RuntimeNvFamilyProbe {
	static var visits:Int = 0;
	static var pending:Bool = false;
	static var renderedFrames:Int = 0;
	static var mods:NightmareVisionModsContext;
	static var paths:NightmareVisionPaths;
	static var assets:NightmareVisionFunkinAssets;
	static var interp:NightmareVisionScriptInterp;
	static var oldGraphic:FlxGraphic;
	static var newGraphic:FlxGraphic;
	static var display:Array<flixel.FlxBasic> = [];

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_NV_FAMILY_SMOKE') == '1';

	static function check(value:Bool, message:String):Void if (!value) throw message;

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished || pending || !Std.isOfType(FlxG.state, FreeplayState)) return;
		try {
			check(FlxG.sound.muted, 'Native family checks must be muted');
			var expectedRate = OptionsHandler.options.unlimitedFPS ? 0 : 60;
			check(Application.current.window.frameRate == expectedRate && FlxG.drawFramerate == expectedRate
				&& FlxG.updateFramerate == 60 && !FlxG.fixedTimestep, 'Native render-rate mode does not match request');
			check(Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Isolated save root required');
			var a = Sys.getEnv('CAMMIE_NV_FAMILY_ALPHA');
			var b = Sys.getEnv('CAMMIE_NV_FAMILY_BETA');
			check(a != null && b != null && a != b, 'Private family fixture roots required');
			var session = new NightmareVisionModFamilySession('alpha', a, [{directory:'alpha', root:a}, {directory:'beta', root:b}]);
			mods = new NightmareVisionModsContext(a, 'alpha', session);
			paths = new NightmareVisionPaths(a, null, {gpuCaching:false}, 'alpha');
			paths.bindModFamily(mods);
			new NightmareVisionModConfigRuntime(mods, paths);
			mods.applyModConfig();
			check(Application.current.window.title == 'Fixture alpha', 'Initial native source title failed');
			assets = new NightmareVisionFunkinAssets(paths);
			interp = new NightmareVisionScriptInterp();
			interp.bindImport('funkin.Mods', mods);
			interp.variables.set('Paths', paths);
			interp.variables.set('FunkinAssets', assets);
			NightmareVisionSourceBindings.bindOwner(interp, a, 'alpha', null, mods.optionSession);
			NightmareVisionModConfigBindings.install(interp, cast mods.nativeConfig, MusicBeatState);
			var graphics:Dynamic = {borrowed:null, selected:null, callbackRan:false};
			interp.variables.set('graphics', graphics);
			interp.execute(new Parser().parseString(
				'import funkin.Mods; graphics.borrowed = Paths.image("marker");'
				+ ' import funkin.data.ModOptions; import funkin.data.FunkinTransitionState; import funkin.backend.MusicBeatState;'
				+ ' newOption("native-fixture-option", "bool", true); ModOptions.setValue("native-fixture-option", false);'
				+ ' Mods.currentModDirectory = "beta"; Mods.updateModList("alpha"); Mods.loadTopMod();'
				+ ' if (Mods.currentModDirectory != "beta") throw "source list selection";'
				+ ' if (ModOptions.getValue("native-fixture-option") == false) throw "source options owner isolation";'
				+ ' ModOptions.add("beta", "native-callback", "bool", true, {callback: function() {graphics.callbackRan = true;}});'
				+ ' ModOptions.get("native-callback").settings.callback = function() {graphics.callbackRan = true;};'
				+ ' ModOptions.get("native-callback").settings.callback();'
				+ ' if (MusicBeatState.transitionInState != FunkinTransitionState.FADE) throw "source transition identity";'
				+ ' if (Paths.getTextFromFile("data/shared.txt") != "beta") throw "selected IO";'
				+ ' graphics.selected = Paths.image("marker");'));
			check(graphics.callbackRan == true, 'Native live option callback did not run');
			check(Application.current.window.title == 'Fixture beta' && paths.UI_PREFIX == 'fixture-ui/', 'Selected native config effects failed');
			check(paths.DEFAULT_FONT == b + '/fonts/vcr.ttf', 'Selected native source font failed');
			check((cast mods.nativeConfig:NightmareVisionModConfigRuntime).configuredIcon != null, 'Native source icon did not decode');
			oldGraphic = cast Reflect.field(graphics, 'borrowed');
			newGraphic = cast Reflect.field(graphics, 'selected');
			check(paths.getModFolder(sys.FileSystem.absolutePath(b + '/images/marker.png')) == 'beta', 'Absolute source discovery label failed');
			check(paths.root == a && oldGraphic != null && newGraphic != null && oldGraphic != newGraphic,
				'Lease anchor or same-name graphic identity failed');
			check(!oldGraphic.isDestroyed && !newGraphic.isDestroyed, 'Borrowed graphic was destroyed during selection');
			check(assets.getContent(a + '/data/shared.txt') == 'alpha', 'Old provider must remain readable');
			var rejected = false;
			try mods.currentModDirectory = 'unrelated' catch (_:Dynamic) rejected = true;
			check(rejected && mods.currentModDirectory == 'beta', 'Foreign selection changed the source provider');
			check(paths.scopeAssetPath('assets/imported_mods/unrelated/data/shared.txt') == null, 'Foreign root was exposed');
			var panel = new FlxSprite(100, 120).makeGraphic(800, 270, 0xFF101018);
			var title = new FlxText(120, 130, 750, 'Authorized family selection, visit ' + (visits + 1) + '\nOld borrowed provider (red) | New selected provider (blue)', 20);
			title.setFormat(paths.DEFAULT_FONT, 20, 0xFFFFFFFF);
			var left = new FlxSprite(160, 230).loadGraphic(oldGraphic);
			var right = new FlxSprite(500, 230).loadGraphic(newGraphic);
			display = [panel, title, left, right];
			for (object in display) FlxG.state.add(object);
			renderedFrames = 0;
			pending = true;
			Application.current.window.onRender.add(onRendered, false, -1000);
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('nv-family', Std.string(error));
	}

	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (!pending || RuntimeSmokeHarness.finished) return;
		// The probe is added after Flixel has queued the current frame.
		if (++renderedFrames < 3) return;
		Application.current.window.onRender.remove(onRendered);
		try {
			var image = Application.current.window.readPixels();
			check(image != null, 'Missing family framebuffer');
			var stem = Sys.getEnv('CAMMIE_NV_FAMILY_CAPTURE');
			check(stem != null && stem != '', 'Capture stem required');
			File.saveBytes(stem + '-visit-' + (visits + 1) + '.png', image.encode());
			for (object in display) {FlxG.state.remove(object, true); object.destroy();}
			display = [];
			interp.release();
			(cast mods.nativeConfig:NightmareVisionModConfigRuntime).release();
			paths.releaseOwnerAssets();
			check(oldGraphic.isDestroyed && newGraphic.isDestroyed, 'Family graphics survived their owner cache release');
			mods.release();
			var rejected = false;
			try paths.getPath('data/shared.txt', null, true) catch (_:Dynamic) rejected = true;
			check(rejected, 'Released family can resolve more IO');
			visits++;
			RuntimeSmokeHarness.emit('nv_family_verified', {visit:visits, capped:!OptionsHandler.options.unlimitedFPS,
				oldProviderRetained:true, foreignRejected:true, released:true, configApplied:true, optionsIsolated:true, liveCallback:true,
				backendFrameRate:Application.current.window.frameRate,
				updateFramerate:FlxG.updateFramerate, drawFramerate:FlxG.drawFramerate});
			pending = false;
			if (visits >= 2) RuntimeSmokeHarness.succeed();
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('nv-family-render', Std.string(error));
	}
}
#end
