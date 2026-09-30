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

	override public function create():Void {
		super.create();
		// The automated importer window is not guaranteed to receive desktop
		// focus, but its worker snapshots and timeout still need to be polled.
		FlxG.autoPause = false;
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
				if (playRequest.songFolder == '' || playRequest.chart == '')
					throw 'play-after-import requires --smoke-song and --smoke-chart';
				if (playRequest.chartEditor || playRequest.freeplay)
					throw 'play-after-import requires a direct PlayState request';
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
			var result:Dynamic = snapshot.result;
			scanJob = null;
			if (cancellationRequested) {
				RuntimeImportSmokeHarness.fail('timeout', 'scan cancellation completed');
				return;
			}
			if (result == null) {
				RuntimeImportSmokeHarness.fail('scan', snapshot.error == null ? 'scan returned no result' : snapshot.error);
				return;
			}
			RuntimeImportSmokeHarness.markScanReady(result);
			if (RuntimeImportSmokeHarness.config().scanOnly) {
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
			importJob = null;
			if (cancellationRequested) {
				RuntimeImportSmokeHarness.fail('timeout', 'import cancellation completed');
				return;
			}
			if (RuntimeImportSmokeHarness.finish(result, error))
				FlxG.switchState(new RuntimeSmokeState());
		}
	}
}
