package;

#if sys
import flixel.FlxG;
import flixel.ui.FlxBar;
import lime.app.Application;
import sys.FileSystem;
import sys.io.File;

/** Opt-in native verification of the actual importer and its read-only worker. */
@:access(ImportSettingsState)
@:access(RuntimeSmokeHarness)
class RuntimeImportUiProbe {
	static var opened:Bool = false;
	static var scanStarted:Bool = false;
	static var activeCaptured:Bool = false;
	static var idleCaptured:Bool = false;
	static var capturePending:String = null;
	static var began:Float = 0;
	static var ui:ImportSettingsState;

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_IMPORT_UI_SMOKE') == '1';

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			if (!opened) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'An isolated smoke save root is required';
				var source = Sys.getEnv('CAMMIE_IMPORT_UI_SOURCE');
				if (source == null || !FileSystem.isDirectory(source)) throw 'A real read-only source folder is required';
				ImportSettings.setSourcePath(source);
				ImportSettings.setSelectedType(ImportEngine.AUTO);
				var size = Sys.getEnv('CAMMIE_IMPORT_UI_SIZE');
				if (size != null && size != '') {
					var dimensions = size.toLowerCase().split('x');
					var width = Std.parseInt(dimensions[0]);
					var height = dimensions.length > 1 ? Std.parseInt(dimensions[1]) : null;
					if (width == null || height == null || width < 800 || height < 540) throw 'Invalid importer probe viewport';
					Application.current.window.resize(width, height);
					FlxG.resizeGame(width, height);
				}
				opened = true;
				began = Sys.time();
				Application.current.window.onRender.add(onRendered, false, -1000);
				FlxG.switchState(function() return new ImportSettingsState());
				return;
			}
			if (Sys.time() - began > 150) throw 'Importer UI scan timed out';
			if (!Std.isOfType(FlxG.state, ImportSettingsState)) return;
			ui = cast FlxG.state;
			if (!FlxG.sound.muted) throw 'Importer smoke must be muted';
			if (!scanStarted) {
				if (ImportRefreshManager.browseTick().busy) return;
				ui.startScan();
				if (ui.scanJob == null) throw 'The actual importer did not start its read-only scan';
				scanStarted = true;
				RuntimeSmokeHarness.emit('import_ui_scan_started', {source:ImportSettings.getSourcePath()});
			}
			var card = ui.progressPresentation;
			if (card == null) throw 'Importer has no shared progress presentation';
			var cards = 0;
			for (member in ui.members) {
				if (Std.isOfType(member, ImportRefreshProgressBar)) cards++;
				if (Std.isOfType(member, FlxBar) && member.visible) throw 'A second standalone progress bar is visible';
			}
			if (cards != 1) throw 'Importer must have exactly one shared progress presentation';
			if (card.visible && !activeCaptured && capturePending == null) {
				if (card.panel.x < 0 || card.panel.x + card.panel.width > FlxG.width
					|| card.panel.y + card.panel.height > ui.detailPanel.y) throw 'Progress presentation overlaps or leaves the viewport';
				if (card.panel.y < ui.scanButton.y + ui.scanButton.height + 8) throw 'Progress presentation overlaps the action row';
				capturePending = 'active';
			}
			if (ui.scanJob == null && scanStarted && activeCaptured && capturePending == null && !idleCaptured) {
				if (ui.scanResult == null) throw 'Read-only scan failed: ' + ui.importStatus.text;
				if (card.visible) return;
				capturePending = 'idle';
			}
		} catch (error:Dynamic) {
			Application.current.window.onRender.remove(onRendered);
			RuntimeSmokeHarness.fail('import-ui', Std.string(error));
		}
	}

	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (capturePending == null || RuntimeSmokeHarness.finished || ui == null) return;
		try {
			var kind = capturePending;
			var stem = Sys.getEnv('CAMMIE_IMPORT_UI_CAPTURE');
			if (stem == null || stem == '') throw 'Importer probe needs a capture path';
			var image = Application.current.window.readPixels();
			if (image == null || image.width <= 0 || image.height <= 0) throw 'Empty native importer framebuffer';
			var path = stem + '-' + kind + '.png';
			RuntimeSmokeHarness.ensureParent(path);
			File.saveBytes(path, image.encode());
			var card = ui.progressPresentation;
			RuntimeSmokeHarness.emit('import_ui_capture', {kind:kind,path:path,width:image.width,height:image.height,
				viewportWidth:FlxG.width,viewportHeight:FlxG.height,progressCards:1,
				headline:card.statusText.text,phase:card.phaseText.text,activity:card.activityText.text,timing:card.timingText.text});
			capturePending = null;
			if (kind == 'active') activeCaptured = true;
			else {
				idleCaptured = true;
				Application.current.window.onRender.remove(onRendered);
				RuntimeSmokeHarness.emit('import_ui_verified', {elapsedSeconds:Sys.time()-began,songs:ui.scanResult.songsFound});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) {
			Application.current.window.onRender.remove(onRendered);
			RuntimeSmokeHarness.fail('import-ui-render', Std.string(error));
		}
	}
}
#end
