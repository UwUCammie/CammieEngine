package;
#if sys
import flixel.FlxG;
import haxe.Json;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;

/** Explicit opt-in UI probe, restricted to a generated private installation. */
@:access(RuntimeSmokeHarness)
@:access(ImportRefreshTransaction)
@:access(FreeplayState)
@:access(LibraryMenuSubState)
@:access(LibraryRemovalSubState)
class RuntimeLibraryRemovalProbe {
	static var phase:Int = 0;
	static var started:Float = 0;
	static var at:Float = 0;
	static var held:Int = 0;
	static var request:Dynamic;
	static var mutex:Mutex = new Mutex();
	static var done:Bool = false;
	static var failure:String = '';
	static var folder:String;
	static var owner:String;
	static var key:String;
	static var category:String;
	static var menu:FreeplayState;
	static var generation:Int;
	static var cancelledGeneration:Int;
	static var capture:String = '';
	static var readback:Bool = false;
	public static function enabled():Bool return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_LIBRARY_REMOVAL_SMOKE') == '1';
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function press(code:Int):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(openfl.events.KeyboardEvent.KEY_DOWN,true,false,0,code)); held = code;
	}
	static function popup():LibraryMenuSubState {
		var state = menu.subState;
		while (state != null && state.subState != null) state = state.subState;
		return cast state;
	}
	static function openRemoval():Void {
		var actions:LibraryMenuSubState = cast popup();
		check(Std.isOfType(actions,LibraryActionsSubState),'Missing library actions');
		var index = -1;
		for (i in 0...actions.actions.length) if (StringTools.startsWith(actions.actions[i].label,'Remove installed mod')) index = i;
		check(index >= 0,'Selected imported package has no removal action');
		actions.actions[index].run();
	}
	static function ui():LibraryRemovalSubState {
		check(Std.isOfType(popup(),LibraryRemovalSubState),'Missing removal confirmation'); return cast popup();
	}
	public static function tick():Void {
		if (RuntimeSmokeHarness.finished) return;
		FlxG.sound.muted = true;
		if (held != 0) { FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(openfl.events.KeyboardEvent.KEY_UP,true,false,0,held)); held = 0; }
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state,FreeplayState) || ImportRemovalManager.poll().busy || ImportRefreshManager.browseTick().busy) return;
				var availability = ImportRefreshManager.availabilitySnapshot();
				if (availability.inspectionPending || availability.refreshInProgress) return;
				check(Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null,'Requires isolated smoke saves');
				request = Json.parse(File.getContent('tmp/library-removal-request.json'));
				check(request.kind == 'generated-library-removal' && ImportRefreshTransaction.samePath(ImportRefreshTransaction.canonicalDirectory(request.install,false),ImportRefreshTransaction.canonicalDirectory(Sys.getCwd(),false)), 'Requires generated private runtime');
				check(Sys.getCwd().indexOf('v34-removal-smoke') >= 0,'Private runtime boundary missing');
				menu = cast FlxG.state; FreeplayState.curCategory = 'All'; started = Sys.time();
				readback = Sys.getEnv('CAMMIE_LIBRARY_REMOVAL_READBACK_SMOKE') == '1';
				if (readback) {
					var context:Dynamic = Json.parse(File.getContent('tmp/library-removal-restart.json'));
					owner = context.owner; key = context.key; folder = context.folder; category = context.category;
					for (song in menu.songs) check(song.songName.toLowerCase() != folder.toLowerCase(),'Fresh process lists removed chart');
					check(UserLibrary.data().isFavorite(key) && UserLibrary.data().lastDifficulty(key) == 'hard' && UserLibrary.data().hasMod(category,owner),'Fresh process lost preserved history');
					phase = 7; inspectRestart(); return;
				}
				phase = 1; launch(); return;
			}
			check(Sys.time() - started < 150,'Removal UI probe deadline');
			check(FlxG.state == menu,'Removal replaced Freeplay state');
			if (Sys.time() - at < .2) return;
			var state = ImportRemovalManager.poll();
			if (capture != '') {
				var image = lime.app.Application.current.window.readPixels(); check(image != null,'Missing confirmation framebuffer');
				File.saveBytes(RuntimeSmokeHarness.config().logPath + '.' + capture + '.png',image.encode()); capture = '';
			}
			switch (phase) {
				case 1:
					mutex.acquire(); var ready = done; var error = failure; mutex.release();
					if (error != '') throw error;
					if (!ready || ImportRefreshManager.browseTick().busy) return;
					if (menu.importRefreshGeneration != ImportRefreshManager.generation) return;
					var index = -1; for (i in 0...menu.songs.length) if (menu.songs[i].songName.toLowerCase() == folder.toLowerCase()) index = i;
					check(index >= 0,'Published generated chart missing from native library');
					FreeplayState.curSelected = index; menu.changeSelection(0,false); key = menu.libraryChartKey(index);
					owner = menu.libraryOwner(index); generation = ImportRefreshManager.generation;
					check(UserLibrary.change(function(data) { data.setFavorite(key,true); data.setLastDifficulty(key,'hard'); category = data.createCategory('Removal saved history'); data.setMembership(category,owner,true); }), 'History fixture save failed');
					menu.openLibraryActions(); phase = 10;
				case 10:
					if (popup() == null) return; openRemoval(); phase = 2;
				case 12:
					if (menu.subState != null) return; menu.openLibraryActions(); phase = 11;
				case 11:
					if (popup() == null) return; openRemoval(); phase = 4;
				case 2:
					if (state.busy) return;
					check(state.phase == 'preview','Real receipt preview blocked: ' + state.label);
					check(ui().selected == 0 && ui().actions[0].label.indexOf('Cancel') == 0,'Removal default is destructive');
					check(state.plan.candidateFiles.length > 0 && ui().detail.text.indexOf('preserved') >= 0,'Missing concrete managed preview');
					var confirmationImage = lime.app.Application.current.window.readPixels(); check(confirmationImage != null,'Missing confirmation framebuffer');
					File.saveBytes(RuntimeSmokeHarness.config().logPath + '.confirmation.png',confirmationImage.encode());
					press(13); phase = 3;
				case 3:
					check(Std.isOfType(popup(),LibraryActionsSubState),'Default Cancel did not return');
					check(ImportRefreshManager.generation == generation && UserLibrary.data().isFavorite(key),'Preview cancellation mutated installed data');
					menu.closeSubState(); phase = 12;
				case 4:
					if (state.busy) return;
					check(state.phase == 'preview','Second preview failed');
					ui().selected = 1; ui().render(); press(13); phase = 5;
				case 5:
					if (state.busy) { check(!state.published,'Busy operation advertised published success'); return; }
					check(state.phase == 'complete' && state.published,'Removal failed: ' + state.label);
					check(ImportRefreshManager.generation > generation,'No main thread publication generation');
					if (menu.importRefreshGeneration != ImportRefreshManager.generation) return;
					for (song in menu.songs) check(song.songName.toLowerCase() != folder.toLowerCase(),'Removed chart retained by native menu');
					check(UserLibrary.data().isFavorite(key) && UserLibrary.data().lastDifficulty(key) == 'hard' && UserLibrary.data().hasMod(category,owner),'Removal lost saved history');
					RuntimeSmokeHarness.emit('library_removal_ui_verified',{defaultCancel:true,managedFiles:state.plan.candidateFiles.length,sharedPreserved:state.plan.sharedFiles.length,mainThreadPublished:true,historyPreserved:true,sameFreeplay:true});
					if (Sys.getEnv('CAMMIE_LIBRARY_REMOVAL_RESTART_SMOKE') == '1') {
						File.saveContent('tmp/library-removal-restart.json',Json.stringify({owner:owner,key:key,folder:folder,category:category}));
						RuntimeSmokeHarness.emit('library_removal_restart_pending',{owner:owner,folder:folder}); RuntimeSmokeHarness.succeed(); return;
					}
					phase = 6; launch();
				case 7:
					mutex.acquire(); var ready = done; var error = failure; mutex.release();
					if (error != '') throw error; if (!ready) return;
					RuntimeSmokeHarness.emit('library_removal_restart_verified',{packageAbsent:true,receiptAbsent:true,historyPreserved:true,archivePreserved:true});
					var absentImage = lime.app.Application.current.window.readPixels(); check(absentImage != null,'Missing restarted framebuffer');
					File.saveBytes(RuntimeSmokeHarness.config().logPath + '.absence.png',absentImage.encode());
					phase = 6; launch();
				case 6:
					mutex.acquire(); var ready = done; var error = failure; mutex.release();
					if (error != '') throw error;
					if (!ready || ImportRefreshManager.browseTick().busy) return;
					if (menu.importRefreshGeneration != ImportRefreshManager.generation) return;
					var restored = LibraryChartIdentity.read(folder);
					check(restored != null && restored.ownerRoot == owner,'Reinstall lost archived owner');
					var restoredKey = UserLibraryData.resolvedChartKey(owner,folder,restored.sourceFolder,restored.hasReceipt);
					check(restoredKey == key && UserLibrary.data().isFavorite(key) && UserLibrary.data().hasMod(category,owner),'Reinstall lost library identity');
					RuntimeSmokeHarness.emit('library_removal_reinstall_verified',{ownerPreserved:true,chartPreserved:true,historyPreserved:true}); RuntimeSmokeHarness.succeed();
			}
			at = Sys.time();
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('library-removal-ui',Std.string(error));
	}
	static function inspectRestart():Void {
		mutex.acquire(); done = false; failure = ''; mutex.release();
		Thread.create(function() {
			var error = '';
			try {
				var manifests = ImportRefreshTransaction.inspectRetainedManifests(Sys.getCwd(),'import-cache/state','import-cache/records');
				for (manifest in manifests) check(ImportRemovalPlan.manifestRoots(manifest).indexOf(owner) < 0,'Fresh process retained removed ownership receipt');
				check(!sys.FileSystem.exists(owner) && !sys.FileSystem.exists('assets/data/' + folder),'Fresh process retained removed managed package/chart');
				var archive = LibraryIdentityArchive.load(Sys.getCwd()); var found = false;
				for (record in archive.records) if (record.ownerRoot == owner && record.folder == folder) found = true;
				check(found,'Fresh process lost archived reinstall identity');
			} catch (e:Dynamic) error = Std.string(e);
			mutex.acquire(); failure = error; done = true; mutex.release();
		});
	}
	static function launch():Void {
		mutex.acquire(); done = false; failure = ''; mutex.release();
		Thread.create(function() {
			var error = ''; var importedFolder:String = null;
			ModuleFunctions.setImportBackgroundMode(true);
			try {
				var scan = ImportWorkflow.scanNow(request.source,ImportEngine.PSYCH);
				check(scan.errors.length == 0 && scan.songsFound == 1,'Generated scan failed: ' + scan.errors.join('; '));
				var names:Map<String,String> = new Map(); for (root in scan.detectedRoots) names.set(ImportPackageNamePrompt.rootKey(root.root),'Removal Fixture');
				var contexts:Array<ImportRefreshManager.ImportSourceBuildContext> = [for (root in scan.detectedRoots) {sourceRoot:root.root,engine:ImportEngine.PSYCH,build:{target:'windows',command:'',flags:[],values:[],flagsComplete:true}}];
				var result = ImportRefreshManager.importOnce(request.source,ImportEngine.PSYCH,scan,names,ImportWorkflow.convertRetainedSource,function() return false,function(_:Dynamic) {},contexts);
				check(result.failed == 0 && result.importedSongs.length == 1,'Generated import failed'); importedFolder = result.importedSongs[0];
			} catch (e:Dynamic) error = Std.string(e);
			ModuleFunctions.setImportBackgroundMode(false);
			mutex.acquire(); failure = error; folder = importedFolder; done = true; mutex.release();
		});
	}
}
#end
