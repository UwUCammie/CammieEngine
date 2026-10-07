package;

import flixel.FlxState;
import flixel.FlxG;
import ImportWorkflow.ImportImportJob;
import ImportWorkflow.ImportScanJob;

/**
	Native-only state for the opt-in full importer preparation command.

	The existing ImportWorkflow jobs own all filesystem writes and converter
	selection.  This state only starts them and polls immutable snapshots on the
	Flixel thread, exactly like ImportSettingsState, so no compatibility logic
	is duplicated in the smoke path.
*/
class RuntimeImportSmokeState extends FlxState {
	var scanJob:ImportScanJob;
	var importJob:ImportImportJob;
	var cancellationRequested:Bool = false;

	/** Keep the play-after-import smoke path in its preparation state while the
	 * manager defers publication to a safe main-thread handoff. Worker completion
	 * alone does not make the new registry revision safe to consume. */
	static function waitForSuccessfulImportHandoff(result:Dynamic, error:Dynamic, runtimeCommitted:Bool):Bool {
		return error == null && result != null && !runtimeCommitted;
	}

	override public function create():Void {
		super.create();
		// The automated importer window is not guaranteed to receive desktop
		// focus, but its worker snapshots and timeout still need to be polled.
		FlxG.autoPause = false;
		// Automated runs remain silent without writing the user's saved volume.
		FlxG.sound.muted = true;
		RuntimeImportSmokeHarness.start();
		var request = RuntimeImportSmokeHarness.config();
		if (request == null) {
			RuntimeImportSmokeHarness.fail('arguments', 'import smoke configuration was not parsed');
			return;
		}
		try {
			if (StringTools.trim(request.source) == '')
				throw 'missing --smoke-import-source';
			if (request.playAfterImport) {
				var playRequest = RuntimeSmokeHarness.config();
				if (request.scanOnly)
					throw '--smoke-import-play-after-complete cannot be combined with --smoke-import-scan-only';
				if (playRequest == null || RuntimeSmokeHarness.getConfigurationError() != '')
					throw 'play-after-import requires a valid RuntimeSmokeHarness chart request';
				if (playRequest.chartEditor)
					throw 'play-after-import cannot open the chart editor';
				if (playRequest.freeplay) {
					if (playRequest.freeplayAcceptSong == '')
						throw 'play-after-import Freeplay requires --smoke-freeplay-select';
				} else if (playRequest.songFolder == '' || playRequest.chart == '')
					throw 'play-after-import requires --smoke-song and --smoke-chart';
			}
			// Match TitleState's one-time setup before the worker reads registries
			// and initializes native compatibility services.
			PluginManager.init();
			DifficultyManager.init();
			ModifierState.init();
			PlayerSettings.init();
			scanJob = ImportWorkflow.beginScan(request.source, request.importType);
		} catch (error:Dynamic) {
			RuntimeImportSmokeHarness.fail('scan', Std.string(error));
		}
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (RuntimeImportSmokeHarness.expired() && !cancellationRequested) {
			cancellationRequested = true;
			RuntimeImportSmokeHarness.requestTimeoutCancellation();
			if (scanJob != null && !scanJob.isFinished())
				scanJob.cancel();
			if (importJob != null && !importJob.isFinished())
				importJob.cancel();
		}
		if (scanJob != null) {
			var snapshot = scanJob.snapshot();
			if (!snapshot.complete)
				return;
			if (cancellationRequested) {
				scanJob = null;
				RuntimeImportSmokeHarness.fail('timeout', 'scan cancellation completed');
				return;
			}
			var result:Dynamic = snapshot.result;
			if (result == null) {
				scanJob = null;
				RuntimeImportSmokeHarness.fail('scan', snapshot.error == null ? 'scan returned no result' : snapshot.error);
				return;
			}
			var request = RuntimeImportSmokeHarness.config();
			if (request != null && !request.scanOnly) {
				// Like Import Settings, keep the completed scan handle until startup
				// receipt inspection and queued handoffs are idle. ImportOnce rejects
				// while that coordinator work is active, so don't publish scan-ready
				// or import-start markers before it is safe to proceed. Scan-only is
				// intentionally independent of importer readiness.
				#if sys
				var coordinatorStatus = ImportRefreshManager.browseTick();
				if (coordinatorStatus != null && coordinatorStatus.busy)
					return;
				#end
			}
			scanJob = null;
			RuntimeImportSmokeHarness.markScanReady(result);
			if (request != null && request.scanOnly) {
				RuntimeImportSmokeHarness.finishScan(result);
				return;
			}
			var packageNames:Map<String, String> = null;
			var packageName = RuntimeImportSmokeHarness.config().packageName;
			if (RuntimeImportSmokeHarness.config().packageNameProvided) {
				var requests = ImportPackageNamePrompt.collectUnnamedRoots(cast result.songs);
				if (requests.length != 1 || !ImportPackageNamePrompt.validName(packageName)) {
					RuntimeImportSmokeHarness.fail('package-name',
						'--smoke-import-package-name requires exactly one unnamed selected package and a valid name');
					return;
				}
				packageNames = ImportPackageNamePrompt.createOverrides(requests, [packageName]);
			}
			RuntimeImportSmokeHarness.markImportStart();
			importJob = ImportWorkflow.beginImport(
				RuntimeImportSmokeHarness.config().source,
				result,
				RuntimeImportSmokeHarness.config().importType,
				packageNames
			);
			return;
		}
		if (importJob != null) {
			var snapshot = importJob.snapshot();
			if (!snapshot.complete)
				return;
			var result:Dynamic = snapshot.result;
			var error:Dynamic = snapshot.error;
			if (error != null || result == null) {
				importJob = null;
				RuntimeImportSmokeHarness.finish(result, error);
				return;
			}
			if (cancellationRequested) {
				importJob = null;
				RuntimeImportSmokeHarness.fail('timeout', 'import cancellation completed');
				return;
			}
			if (waitForSuccessfulImportHandoff(result, error, snapshot.runtimeCommitted))
				return;
			importJob = null;
			if (RuntimeImportSmokeHarness.finish(result, error)) {
				if (RuntimeSmokeHarness.config().freeplay)
					FlxG.switchState(new RuntimeSmokeFreeplayState());
				else
					FlxG.switchState(new RuntimeSmokeState());
			}
		}
	}
}
