package;

#if sys
import flixel.FlxG;
import haxe.Json;
import haxe.io.Path;
import lime.app.Application;
import sys.io.File;
import sys.thread.Lock;
import sys.thread.Mutex;
import sys.thread.Thread;
import ImportWorkflow.ImportScanResult;
import ModuleFunctions.SongImportBatchResult;

/** Generated private fixtures only: actual workers, publication, rows and launch. */
@:access(FreeplayState)
@:access(RuntimeSmokeHarness)
class RuntimeImportAvailabilityProbe {
	static var phase:Int = 0;
	static var began:Float = 0;
	static var workerMutex:Mutex = new Mutex();
	static var workerDone:Bool = false;
	static var workerError:String = '';
	static var blocked:Bool = false;
	static var releaseWorker:Lock = new Lock();
	static var a:String;
	static var b:String;
	static var songA:String;
	static var songB:String;
	static var ownerB:String;
	static var captureKind:String;
	static var captureFrames:Int = 0;
	static var gameplayAt:Float = 0;
	static var captureAt:Float = 0;

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_IMPORT_AVAILABILITY_SMOKE') == '1';
	static function check(value:Bool, message:String):Void if (!value) throw message;

	static function convert(source:String, scan:ImportScanResult, names:Map<String,String>):SongImportBatchResult {
		var spec:Dynamic = Json.parse(ImportFile.getContent(Path.join([source, 'probe.json'])));
		var song:String = spec.song;
		var manifest = CompatScriptManifest.create(source, ImportEngine.PSYCH);
		var root = manifest.selectedRoot;
		ImportFile.saveContent(root + '/meta.json', Json.stringify({name:spec.title}));
		ImportFile.saveContent('assets/data/' + song + '/' + song + '.json',
			ImportFile.getContent(Path.join([source, 'assets/data', song, song + '.json'])));
		ImportFile.saveContent('assets/data/' + song + '/compatScripts.json', Json.stringify(manifest));
		ImportFile.saveContent('assets/data/' + song + '/importProvenance.json',
			Json.stringify({version:1, sourceOwner:root, sourceFolder:song, modName:spec.title}));
		ImportFile.copy(Path.join([source, 'assets/songs', song, 'Inst.ogg']), 'assets/songs/' + song + '/Inst.ogg');
		var path = FreeplayRegistry.getPath();
		var registry:Array<Dynamic> = cast CoolUtil.parseJson(ImportFile.getContent(path));
		var imported:Dynamic = null;
		for (category in registry) if (category.name == 'Imported') imported = category;
		if (imported == null) { imported = {name:'Imported', songs:[]}; registry.push(imported); }
		(cast imported.songs:Array<Dynamic>).push({name:song, display:spec.title, character:'dad', week:-1});
		ImportFile.saveContent(path, Json.stringify(registry));
		return {found:1, imported:1, importedSongs:[song], skipped:0, failed:0,
			copiedAssets:1, skippedAssets:0, errors:[]};
	}

	static function startWorker(source:String, hold:Bool):Void {
		workerMutex.acquire(); workerDone = false; workerError = ''; blocked = false; workerMutex.release();
		Thread.create(function() {
			try {
				var scan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(scan != null && scan.songsFound == 1, 'Generated donor scan must find one song');
				ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan, new Map(),
					function(retained, plan, labels) {
						if (hold) {
							workerMutex.acquire(); blocked = true; workerMutex.release();
							check(releaseWorker.wait(45), 'Private worker latch timed out');
						}
						return convert(retained, plan, labels);
					}, function() return false, function(_) {});
			} catch (error:Dynamic) {
				workerMutex.acquire(); workerError = Std.string(error); workerMutex.release();
			}
			workerMutex.acquire(); workerDone = true; workerMutex.release();
		});
	}

	static function indexFor(ui:FreeplayState, name:String, provisional:Bool):Int {
		for (i in 0...ui.songs.length) {
			var song = ui.songs[i];
			if (provisional ? song.isProvisional && song.sourceFolder == name : !song.isProvisional && song.songName == name)
				return i;
		}
		return -1;
	}

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Private muted save scope required');
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
				var expectedRate = OptionsHandler.options.unlimitedFPS ? 0 : 60;
				check(Application.current.window.frameRate == expectedRate && FlxG.drawFramerate == expectedRate
					&& FlxG.updateFramerate == 60 && !FlxG.fixedTimestep, 'Native rate mode does not match private request');
				a = Sys.getEnv('CAMMIE_IMPORT_AVAILABILITY_A'); b = Sys.getEnv('CAMMIE_IMPORT_AVAILABILITY_B');
				check(a != null && b != null && a != b && Sys.getCwd().length < 60, 'Short private install and donors required');
				songA = Json.parse(File.getContent(a + '/probe.json')).song;
				songB = Json.parse(File.getContent(b + '/probe.json')).song;
				ownerB = CompatScriptManifest.destinationRoot(b, ImportEngine.PSYCH);
				FreeplayState.curCategory = 'Imported';
				began = Sys.time(); phase = 1; startWorker(a, false); return;
			}
			check(Sys.time() - began < 55, 'Native availability timed out');
			workerMutex.acquire(); var done = workerDone; var error = workerError; var waiting = blocked; workerMutex.release();
			check(error == '', 'Private importer worker failed: ' + error);
			if (phase == 1 && done) {
				if (ImportRefreshManager.browseTick().busy) return;
				phase = 2; startWorker(b, true); return;
			}
			if (phase == 2 && waiting && Std.isOfType(FlxG.state, FreeplayState)) {
				var ui:FreeplayState = cast FlxG.state;
				ui.refreshImportAvailability(true);
				var ready = indexFor(ui, songA, false), pending = indexFor(ui, songB, true);
				if (ready < 0 || pending < 0) return;
				var difficulty = DifficultyManager.getValidDiff(1, songA);
				check(ui.availabilityAllowsLaunch(ready, difficulty), 'Ready A was blocked by B');
				check(!ui.availabilityAllowsLaunch(pending, difficulty), 'Pending B was playable');
				FreeplayState.curSelected = pending; ui.changeSelection(0, true); ui.rebuildVisibleRows();
				check(ui.songRows[pending] != null, 'Pending row not materialized');
				for (glyph in ui.songRows[pending].members) if (glyph != null) check(glyph.color == 0xFF858585, 'Pending row not gray');
				RuntimeSmokeHarness.emit('import_availability_pending', {ready:songA, pending:songB,
					category:FreeplayState.curCategory, revision:ImportRefreshManager.availabilityRevision()});
				phase = 3; requestCapture('pending'); return;
			}
			if (phase == 4 && Std.isOfType(FlxG.state, PlayState)) {
				var view = ImportRefreshManager.availabilitySnapshot();
				check(!FreeplaySongAvailability.ownerReadiness(view, ownerB).ready, 'B unlocked before publication');
				if (gameplayAt == 0) gameplayAt = Sys.time();
				if (Sys.time() - gameplayAt < 1 || Conductor.songPosition <= 0) return;
				RuntimeSmokeHarness.emit('import_availability_gameplay', {song:Song.storageFolder(PlayState.SONG), songPosition:Conductor.songPosition});
				releaseWorker.release(); phase = 5;
				FreeplayState.currentSongList = [];
				LoadingState.loadAndSwitchState(new FreeplayState()); return;
			}
			if (phase == 5 && done && Std.isOfType(FlxG.state, FreeplayState)) {
				var ui:FreeplayState = cast FlxG.state;
				var ready = indexFor(ui, songB, false);
				if (ready < 0) return;
				check(indexFor(ui, songB, true) < 0, 'Committed B still has a provisional duplicate');
				check(FreeplayState.curCategory == 'Imported' && ui.availabilityAllowsLaunch(ready,
					DifficultyManager.getValidDiff(1, songB)), 'B handoff did not replace pending state');
				FreeplayState.curSelected = ready; ui.changeSelection(0, true);
				phase = 6; requestCapture('complete');
			}
		} catch (error:Dynamic) { releaseWorker.release(); RuntimeSmokeHarness.fail('import-availability', Std.string(error)); }
	}

	static function requestCapture(kind:String):Void {
		captureKind = kind; captureFrames = 0;
		captureAt = Sys.time();
		Application.current.window.onRender.add(onRendered, false, -1000);
	}
	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (RuntimeSmokeHarness.finished || ++captureFrames < 3 || Sys.time() - captureAt < 0.5) return;
		Application.current.window.onRender.remove(onRendered);
		try {
			if (captureKind == 'pending') {
				var ui:FreeplayState = cast FlxG.state;
				for (member in ui.members) if (Std.isOfType(member, ImportRefreshProgressBar)) {
					var card:ImportRefreshProgressBar = cast member;
					check(card.visible && card.panel.x + card.panel.width * card.panel.scale.x <= ui.scoreText.x - 10,
						'Import card obscures the score column');
				}
			}
			var pixels = Application.current.window.readPixels(); check(pixels != null, 'Missing native availability framebuffer');
			var path = Sys.getEnv('CAMMIE_IMPORT_AVAILABILITY_CAPTURE') + '-' + captureKind + '.png';
			File.saveBytes(path, pixels.encode());
			RuntimeSmokeHarness.emit('import_availability_capture', {kind:captureKind, path:path});
			if (captureKind == 'pending') {
				var ui:FreeplayState = cast FlxG.state;
				FreeplayState.curSelected = indexFor(ui, songA, false);
				FreeplayState.curDifficulty = DifficultyManager.getValidDiff(1, songA);
				ui.changeSelection(0, true); OptionsHandler.options.skipModifierMenu = true;
				check(ui.hxcLaunchCurrentSelection(), 'Ready A confirmation did not launch'); phase = 4;
			} else { RuntimeSmokeHarness.emit('import_availability_verified', {elapsedSeconds:Sys.time() - began}); RuntimeSmokeHarness.succeed(); }
		} catch (error:Dynamic) { releaseWorker.release(); RuntimeSmokeHarness.fail('import-availability-render', Std.string(error)); }
	}
}
#end
