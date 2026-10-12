package;
#if sys
import flixel.FlxG;
import haxe.Json;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;
/** Actual converter checks using externally generated, isolated source packages. */
@:access(RuntimeSmokeHarness)
class RuntimeLibraryLifecycleProbe {
	static var phase:Int = 0;
	static var started:Float;
	static var request:Dynamic;
	static var mutex = new Mutex();
	static var done:Bool = false;
	static var error:String = '';
	static var result:Array<String>;
	static var firstKey:String;
	static var firstOwner:String;
	static var firstFolder:String;
	static var category:String;
	public static function enabled():Bool return RuntimeSmokeHarness.enabled()
		&& Sys.getEnv('CAMMIE_LIBRARY_LIFECYCLE_SMOKE') == '1';
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	public static function tick():Void {
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Requires muted isolated saves');
				request = Json.parse(File.getContent('tmp/library-lifecycle-request.json'));
				check(request.kind == 'generated-library-lifecycle', 'Requires generated fixture');
				started = Sys.time(); phase = 1; launch(request.first); return;
			}
			check(Sys.time() - started < 100, 'Library lifecycle deadline');
			mutex.acquire(); var ready = done; var failure = error; var folders = result; mutex.release();
			if (failure != '') throw failure;
			if (!ready || ImportRefreshManager.browseTick().busy) return;
			check(folders != null && folders.length == 1, 'Expected one converted chart folder');
			var record = LibraryChartIdentity.read(folders[0]);
			check(record != null && record.hasReceipt && record.ownerRoot != '', 'Missing published owner receipt');
			var key = UserLibraryData.resolvedChartKey(record.ownerRoot, folders[0], record.sourceFolder, record.hasReceipt);
			RuntimeSmokeHarness.emit('library_lifecycle_import', {phase:phase, folder:folders[0], owner:record.ownerRoot, key:key});
			if (phase == 1) {
				firstKey = key; firstOwner = record.ownerRoot; firstFolder = folders[0];
				check(UserLibrary.change(function(data) {
					data.setFavorite(key, true); data.setLastDifficulty(key, 'hard');
					category = data.createCategory('Lifecycle'); data.setMembership(category, firstOwner, true);
				}), 'Could not save generated library metadata: ' + UserLibrary.error);
				phase = 2; launch(request.moved); return;
			}
			if (phase == 2 || phase == 3) {
				check(key == firstKey && record.ownerRoot == firstOwner && folders[0] == firstFolder,
					'Reimport changed chart identity after source move');
				var data = UserLibraryData.decode(UserLibrary.data().encode());
				check(data.isFavorite(key) && data.lastDifficulty(key) == 'hard' && data.hasMod(category, record.ownerRoot),
					'Library metadata did not survive reimport');
				if (phase == 2) { phase = 3; launch(request.moved); return; }
				phase = 4; launch(request.distinct); return;
			}
			check(key != firstKey && record.ownerRoot != firstOwner && folders[0] != firstFolder,
				'Different same-named package merged with original');
			check(!UserLibrary.data().isFavorite(key) && !UserLibrary.data().hasMod(category, record.ownerRoot),
				'Different package inherited library metadata');
			var manifests = ImportRefreshTransaction.inspectRetainedManifests(Sys.getCwd(),
				'import-cache/state', 'import-cache/records');
			var installed = ImportInstalledOwnership.inspect(Sys.getCwd(), manifests, []);
			check(installed.complete && installed.charts.length == 2, 'Installed ownership audit failed: ' + installed.blockers.join('; '));
			RuntimeSmokeHarness.emit('library_installed_ownership_verified', {charts:installed.charts.length, owners:installed.owners.length});
			var encodedBefore = Json.stringify(manifests);
			var removal = ImportRemovalPlan.assess([firstOwner], manifests, true, []);
			check(removal.inventoryComplete && removal.blockers.length == 0
				&& removal.transactionOwners.length == 1 && removal.affectedOwners.length == 1
				&& removal.candidateFiles.length > 0 && removal.registryPaths.length > 0,
				'Real receipt removal inventory failed: ' + removal.blockers.join('; '));
			var blocked = ImportRemovalPlan.assess([firstOwner], manifests, true, [firstOwner]);
			check(blocked.blockers.length > 0, 'Active package did not block removal assessment');
			check(encodedBefore == Json.stringify(manifests) && UserLibrary.data().isFavorite(firstKey),
				'Removal assessment changed ownership or saved metadata');
			RuntimeSmokeHarness.emit('library_removal_plan_verified', {files:removal.candidateFiles.length,
				registries:removal.registryPaths.length, activeBlocked:true, readOnly:true});
			RuntimeSmokeHarness.emit('library_lifecycle_verified', {moved:true, repeated:true, isolated:true});
			RuntimeSmokeHarness.succeed();
		} catch (failure:Dynamic) RuntimeSmokeHarness.fail('library-lifecycle', Std.string(failure));
	}
	static function launch(source:String):Void {
		mutex.acquire(); done = false; error = ''; result = null; mutex.release();
		Thread.create(function() {
			var failure = ''; var folders:Array<String> = null;
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(_:Dynamic) {});
			ModuleFunctions.setImportCancelCallback(function() return false);
			try {
				var scan = ImportWorkflow.scanNow(source, ImportEngine.PSYCH);
				check(scan.errors.length == 0 && scan.songsFound == 1, 'Generated scan failed: ' + scan.errors.join('; '));
				var contexts:Array<ImportRefreshManager.ImportSourceBuildContext> = [for (root in scan.detectedRoots)
					{sourceRoot:root.root, engine:ImportEngine.PSYCH,
						build:{target:'windows', command:'', flags:[], values:[], flagsComplete:true}}];
				var imported = ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan, new Map(),
					ImportWorkflow.convertRetainedSource, function() return false, function(_:Dynamic) {}, contexts);
				check(imported != null && imported.failed == 0, 'Generated conversion failed');
				folders = imported.importedSongs;
			} catch (e:Dynamic) failure = Std.string(e);
			ModuleFunctions.setImportProgressCallback(null); ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			mutex.acquire(); error = failure; result = folders; done = true; mutex.release();
		});
	}
}
#end
