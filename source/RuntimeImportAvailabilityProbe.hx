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
@:access(ImportRefreshManager)
@:access(RuntimeSmokeHarness)
class RuntimeImportAvailabilityProbe {
	static var phase:Int = 0;
	static var began:Float = 0;
	static var workerMutex:Mutex = new Mutex();
	static var workerDone:Bool = false;
	static var workerError:String = '';
	static var blocked:Bool = false;
	static var releaseWorker:Lock = new Lock();
	static var releaseDirectWorker:Lock = new Lock();
	static var a:String;
	static var b:String;
	static var songA:String;
	static var songB:String;
	static var ownerB:String;
	static var captureKind:String;
	static var captureFrames:Int = 0;
	static var gameplayAt:Float = 0;
	static var resumeRequestedAt:Float = 0;
	static var directGameplayAt:Float = 0;
	static var directReturnFreeplay:Dynamic;
	static var directReturnSelection:String = '';
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
			Json.stringify({version:1, sourceOwner:root, sourceFolder:song, modName:'content',
				nameSource:'inferred', destinationFolder:song, sourceEngine:ImportEngine.PSYCH,
				sourceModDirectory:ImportIO.current().sourceLabel(source)}));
		ImportFile.copy(Path.join([source, 'assets/songs', song, 'Inst.ogg']), 'assets/songs/' + song + '/Inst.ogg');
		var path = FreeplayRegistry.getPath();
		var registry:Array<Dynamic> = cast CoolUtil.parseJson(ImportFile.getContent(path));
		var imported:Dynamic = null;
		for (category in registry) if (category.name == 'Imported') imported = category;
		if (imported == null) { imported = {name:'Imported', songs:[]}; registry.push(imported); }
		var alreadyPresent = false;
		for (entry in (cast imported.songs:Array<Dynamic>))
			if (entry != null && Reflect.field(entry, 'name') == song) alreadyPresent = true;
		if (!alreadyPresent) (cast imported.songs:Array<Dynamic>).push({name:song,
			display:spec.title + ' · content · Psych Engine', sourceLabel:'content · Psych Engine',
			character:'dad', week:-1});
		ImportFile.saveContent(path, Json.stringify(registry));
		return {found:1, imported:1, importedSongs:[song], skipped:0, failed:0,
			copiedAssets:1, skippedAssets:0, errors:[]};
	}

	static function startWorker(source:String, hold:Bool, directReturn:Bool = false):Void {
		workerMutex.acquire(); workerDone = false; workerError = ''; blocked = false; workerMutex.release();
		Thread.create(function() {
			try {
				var scan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(scan != null && scan.songsFound == 1, 'Generated donor scan must find one song');
				ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan, new Map(),
					function(retained, plan, labels) {
						if (hold) {
							workerMutex.acquire(); blocked = true; workerMutex.release();
							var released = directReturn ? releaseDirectWorker.wait(45) : releaseWorker.wait(45);
							check(released, 'Private worker latch timed out');
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

	/** Finish a package reservation between redraw and a fresh launch check.
	 * The manager generation deliberately stays unchanged, like a receipt recheck.
	 */
	static function verifyInteractionRevision(ui:FreeplayState, index:Int):Void {
		var token = 'private-availability-interaction';
		var owner = ui.songs[index].ownerRoot;
		var generation = ImportRefreshManager.generation;
		var selected = FreeplayState.curSelected;
		ImportRefreshManager.mutex.acquire();
		ImportRefreshManager.reserveLocked(token, 'private-availability', [owner], null, false);
		ImportRefreshManager.mutex.release();
		ui.refreshImportAvailability();
		check(!ui.availabilityAllowsSelection(index), 'Reserved row must be unavailable');
		check(ui.songRows[index] != null, 'Race row must be materialized');
		for (glyph in ui.songRows[index].members) if (glyph != null)
			check(glyph.color == 0xFF858585, 'Reserved race row must be gray');
		ImportRefreshManager.mutex.acquire();
		ImportRefreshManager.releaseReservationLocked(token);
		ImportRefreshManager.mutex.release();
		ui.refreshAvailabilityForInteraction();
		check(ui.availabilityAllowsSelection(index), 'Fresh launch check must see the completed package');
		check(ui.refreshImportAvailability(), 'Fresh launch check must not consume the pending redraw');
		for (glyph in ui.songRows[index].members) if (glyph != null)
			check(glyph.color == 0xFFFFFFFF, 'Completed race row remained gray');
		check(FreeplayState.curSelected == selected && ImportRefreshManager.generation == generation,
			'Receipt readiness redraw must preserve selection and the current Freeplay state');
		RuntimeSmokeHarness.emit('import_availability_interaction_redraw', {ready:true, generation:generation});
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
				releaseWorker.release(); resumeRequestedAt = Sys.time(); phase = 45;
				return;
			}
			if (phase == 45 && Std.isOfType(FlxG.state, PlayState)) {
				if (Sys.time() - resumeRequestedAt < 0.25) return;
				workerMutex.acquire(); var completedDuringGameplay = workerDone; workerMutex.release();
				check(ImportWorkScheduler.gameplayActive(), 'Gameplay did not acquire the import work lease');
				check(!completedDuringGameplay, 'Background import committed during protected gameplay');
				RuntimeSmokeHarness.emit('import_availability_gameplay_pause', {paused:true});
				phase = 46;
				LoadingState.loadAndSwitchState(new MainMenuState()); return;
			}
			if (phase == 46 && done && Std.isOfType(FlxG.state, MainMenuState)) {
				if (ImportRefreshManager.browseTick().busy) return;
				check(FreeplayState.currentSongList.length > 0
					&& FreeplayState.currentSongListGeneration != ImportRefreshManager.generation,
					'Native fixture did not retain a stale non-empty Freeplay list');
				RuntimeSmokeHarness.emit('import_availability_menu_handoff',
					{generation:ImportRefreshManager.generation});
				phase = 5;
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
				verifyInteractionRevision(ui, ready);
				check(ui.songs[ready].sourceLabel == Path.withoutDirectory(b) + ' · Psych Engine'
					&& ui.songs[ready].displayTitle == 'Availability Pending',
					'Legacy generic subtitle was not repaired from its validated owner receipt');
				RuntimeSmokeHarness.emit('import_availability_source_label',
					{source:ui.songs[ready].sourceLabel, title:ui.songs[ready].displayTitle});
				phase = 6; requestCapture('complete');
			}
			if (phase == 7 && waiting && Std.isOfType(FlxG.state, FreeplayState)) {
				var ui:FreeplayState = cast FlxG.state;
				ui.refreshImportAvailability(true);
				var pending = indexFor(ui, songB, false);
				var ready = indexFor(ui, songA, false);
				if (pending < 0 || ready < 0) return;
				check(!ui.availabilityAllowsLaunch(pending, DifficultyManager.getValidDiff(1, songB)),
					'Refreshing B should remain unavailable before gameplay');
				check(ui.songRows[pending] != null, 'Direct-return race row was not materialized');
				for (glyph in ui.songRows[pending].members) if (glyph != null)
					check(glyph.color == 0xFF858585, 'Refreshing B should be gray before gameplay');
				check(ui.availabilityAllowsLaunch(ready, DifficultyManager.getValidDiff(1, songA)),
					'Ready A was blocked by B refresh');
				FreeplayState.curSelected = ready;
				FreeplayState.curDifficulty = DifficultyManager.getValidDiff(1, songA);
				directReturnSelection = ui.songs[ready].songName;
				ui.changeSelection(0, true);
				OptionsHandler.options.skipModifierMenu = true;
				check(ui.hxcLaunchCurrentSelection(), 'Direct-return fixture did not launch ready A');
				directGameplayAt = 0;
				phase = 8;
				return;
			}
			if (phase == 8 && Std.isOfType(FlxG.state, PlayState)) {
				workerMutex.acquire(); var directDone = workerDone; workerMutex.release();
				check(!directDone && ImportWorkScheduler.gameplayActive(),
					'Direct-return worker must still be pending during gameplay');
				if (directGameplayAt == 0) directGameplayAt = Sys.time();
				if (Sys.time() - directGameplayAt < 0.3 || Conductor.songPosition <= 0) return;
				LoadingState.loadAndSwitchState(new FreeplayState());
				phase = 9;
				return;
			}
			if (phase == 9 && Std.isOfType(FlxG.state, FreeplayState)) {
				workerMutex.acquire(); var directDone = workerDone; var stillWaiting = blocked; workerMutex.release();
				check(!directDone && stillWaiting,
					'Direct return must reach Freeplay while its import worker is still held');
				var ui:FreeplayState = cast FlxG.state;
				ui.refreshImportAvailability(true);
				var pending = indexFor(ui, songB, false);
				if (pending < 0) return;
				check(!ui.availabilityAllowsLaunch(pending, DifficultyManager.getValidDiff(1, songB)),
					'B became playable before its direct-return refresh completed');
				check(ui.songRows[pending] != null, 'Direct-return row was not materialized');
				for (glyph in ui.songRows[pending].members) if (glyph != null)
					check(glyph.color == 0xFF858585, 'B should remain gray before worker release');
				check(FreeplayState.curSelected >= 0 && FreeplayState.curSelected < ui.songs.length
					&& ui.songs[FreeplayState.curSelected].songName == directReturnSelection,
					'Direct return changed selection before the refresh completed');
				directReturnFreeplay = ui;
				RuntimeSmokeHarness.emit('import_availability_direct_return_pending',
					{song:songB, selection:directReturnSelection, sameState:true});
				releaseDirectWorker.release();
				phase = 10;
				return;
			}
			if (phase == 10 && Std.isOfType(FlxG.state, FreeplayState)) {
				workerMutex.acquire(); var directDone = workerDone; var directError = workerError; workerMutex.release();
				check(directError == '', 'Direct-return importer worker failed: ' + directError);
				if (!directDone) return;
				var ui:FreeplayState = cast FlxG.state;
				if (ui == directReturnFreeplay || ImportRefreshManager.browseTick().busy) return;
				var ready = indexFor(ui, songB, false);
				if (ready < 0) return;
				check(indexFor(ui, songB, true) < 0, 'Direct-return refresh left a provisional duplicate');
				check(ui.availabilityAllowsLaunch(ready, DifficultyManager.getValidDiff(1, songB)),
					'Direct-return refresh completed but B remained unavailable');
				check(ui.songRows[ready] != null, 'Direct-return ready row was not materialized');
				for (glyph in ui.songRows[ready].members) if (glyph != null)
					check(glyph.color == 0xFFFFFFFF, 'Direct-return ready row remained gray after handoff');
				var count = 0;
				for (song in ui.songs) if (!song.isProvisional && song.songName == songB) count++;
				check(count == 1 && ImportRefreshManager.generation == FreeplayState.currentSongListGeneration,
					'Direct-return refresh duplicated B or left a stale song-list generation');
				RuntimeSmokeHarness.emit('import_availability_direct_return_complete',
					{song:songB, ready:true, stateRecreated:true, selection:FreeplayState.curSelected});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) { releaseWorker.release(); releaseDirectWorker.release(); RuntimeSmokeHarness.fail('import-availability', Std.string(error)); }
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
			} else {
				RuntimeSmokeHarness.emit('import_availability_verified', {elapsedSeconds:Sys.time() - began});
				startWorker(b, true, true);
				phase = 7;
			}
		} catch (error:Dynamic) { releaseWorker.release(); releaseDirectWorker.release(); RuntimeSmokeHarness.fail('import-availability-render', Std.string(error)); }
	}
}
#end
