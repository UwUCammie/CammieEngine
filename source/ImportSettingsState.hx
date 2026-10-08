package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import flixel.addons.ui.FlxUIButton;
import lime.ui.FileDialog;
import lime.ui.FileDialogType;
import ImportWorkflow.ImportScanResult;
import ImportWorkflow.ImportScanJob;
import ImportWorkflow.ImportImportJob;
import ImportWorkflow.ImportWorkflowProgress;
#if sys
import sys.FileSystem;
#end

/** Import configuration submenu shown from SaveDataState.
 *
 * Importing is deliberately a two-step operation. Scan is read-only and
 * produces the plan/report; Import then consumes that exact plan. Both jobs
 * run behind ImportWorkflow handles, so this state only polls snapshots from
 * update() and remains drawable while a large source tree is being inspected
 * or copied.
 */
class ImportSettingsState extends MusicBeatState {
	static inline var ACTION_CHOOSE:Int = 0;
	static inline var ACTION_SCAN:Int = 1;
	static inline var ACTION_IMPORT:Int = 2;
	static inline var SUMMARY_FONT_SIZE:Int = 15;
	static inline var DETAIL_FONT_SIZE:Int = 18;
	static inline var DETAIL_LINE_HEIGHT:Int = 24;
	static inline var SUMMARY_HEIGHT:Int = 78;

	var importTypeSelector:FlxText;
	var importTypes:Array<String>;
	var importTypeIndex:Int = 0;
	var sourcePathSelector:FlxText;
	var importStatus:FlxText;
	var scanSummary:FlxText;
	var detailText:FlxText;
	var detailPageText:FlxText;
	var helpText:FlxText;
	var chooseSourceButton:FlxUIButton;
	var scanButton:FlxUIButton;
	var importSourceButton:FlxUIButton;
	var cancelButton:FlxUIButton;
	public var progressPresentation(default, null):ImportRefreshProgressBar;
	var detailPanel:FlxSprite;

	var actionIndex:Int = ACTION_CHOOSE;
	var detailPage:Int = 0;
	var detailLines:Array<String> = [];
	var refreshDiagnosticCount:Int = -1;
	var sourcePathAtScan:String = '';
	var importTypeAtScan:String = '';
	var scanResult:ImportScanResult = null;
	var scanJob:ImportScanJob = null;
	var importJob:ImportImportJob = null;
	var packageNamePromptOpen:Bool = false;
	var backRequested:Bool = false;
	var stateAlive:Bool = false;
	var coordinatorWasBusy:Bool = false;

	override function create() {
		stateAlive = true;
		FlxG.mouse.visible = true;

		var margin = Std.int(Math.max(24, FlxG.width * 0.055));
		var contentWidth = Std.int(Math.max(420, FlxG.width - margin * 2));
		var menuBG = new FlxSprite().loadGraphic("assets/images/menuDesat.png");
		menuBG.color = 0xFF7194FC;
		menuBG.setGraphicSize(Std.int(menuBG.width * 1.1));
		menuBG.updateHitbox();
		menuBG.screenCenter();
		add(menuBG);

		var title = new FlxText(0, 28, FlxG.width, "Import Settings", 48);
		title.setFormat("assets/fonts/vcr.ttf", 48, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(title);

		var typeY = 94;
		var typeLabel = new FlxText(margin, typeY, 190, "Import Type", 26);
		typeLabel.setFormat("assets/fonts/vcr.ttf", 26, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		add(typeLabel);

		importTypes = ImportSettings.getTypes();
		importTypeIndex = importTypes.indexOf(ImportSettings.getSelectedType());
		if (importTypeIndex < 0)
			importTypeIndex = 0;
		importTypeSelector = new FlxText(margin + 205, typeY, contentWidth - 205, "", 26);
		importTypeSelector.setFormat("assets/fonts/vcr.ttf", 26, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		add(importTypeSelector);
		refreshImportType();

		var sourceY = 138;
		var sourceLabel = new FlxText(margin, sourceY, 190, "Source Folder", 24);
		sourceLabel.setFormat("assets/fonts/vcr.ttf", 24, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		add(sourceLabel);

		sourcePathSelector = new FlxText(margin + 205, sourceY, contentWidth - 205, "", 18);
		sourcePathSelector.setFormat("assets/fonts/vcr.ttf", 18, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		add(sourcePathSelector);
		refreshSourcePath();

		var buttonY = 184;
		chooseSourceButton = new FlxUIButton(margin, buttonY, "Choose Folder", function():Void {
			chooseSourceFolder();
		});
		add(chooseSourceButton);

		scanButton = new FlxUIButton(margin + 178, buttonY, "Scan", function():Void {
			startScan();
		});
		add(scanButton);

		importSourceButton = new FlxUIButton(margin + 296, buttonY, "Import Songs", function():Void {
			startImport();
		});
		add(importSourceButton);

		cancelButton = new FlxUIButton(margin + 470, buttonY, "Cancel", function():Void {
			cancelActiveJob();
		});
		cancelButton.visible = false;
		cancelButton.active = false;
		add(cancelButton);
		layoutActionButtons(margin, buttonY, contentWidth);

		importStatus = new FlxText(margin, 282, contentWidth, "Choose a source folder, then scan it before importing.", 19);
		importStatus.setFormat("assets/fonts/vcr.ttf", 19, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(importStatus);

		scanSummary = new FlxText(margin, 316, contentWidth, "No scan has been run.", SUMMARY_FONT_SIZE);
		scanSummary.setFormat("assets/fonts/vcr.ttf", SUMMARY_FONT_SIZE, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		// Keep the count summary in a reserved area. Root paths and diagnostics
		// belong in the paged detail panel; putting every detected root in this
		// field makes a completed scan grow into the panel below it.
		scanSummary.autoSize = false;
		scanSummary.wordWrap = true;
		scanSummary.fieldHeight = SUMMARY_HEIGHT;
		add(scanSummary);

		var progressBottom = 396;
		var detailBottomLimit = FlxG.height - 66;
		var detailY = Std.int(Math.max(progressBottom + 10, Math.min(402, detailBottomLimit - 150)));
		var detailHeight = Std.int(Math.max(90, detailBottomLimit - detailY));
		detailPanel = new FlxSprite(margin, detailY).makeGraphic(contentWidth, detailHeight, 0xB9000000);
		add(detailPanel);

		detailText = new FlxText(margin + 12, detailY + 8, contentWidth - 24, "Scan details will appear here.", DETAIL_FONT_SIZE);
		detailText.setFormat("assets/fonts/vcr.ttf", DETAIL_FONT_SIZE, FlxColor.WHITE, LEFT, OUTLINE, FlxColor.BLACK);
		detailText.autoSize = false;
		// Detail rows are wrapped into bounded strings by refreshDetails(). Keep
		// wordWrap disabled so FlxText does not add uncounted visual rows and
		// let the page run past the panel's lower edge.
		detailText.wordWrap = false;
		detailText.fieldHeight = detailHeight - 16;
		add(detailText);

		detailPageText = new FlxText(margin, detailY + detailHeight + 4, contentWidth, "", 15);
		detailPageText.setFormat("assets/fonts/vcr.ttf", 15, FlxColor.WHITE, RIGHT, OUTLINE, FlxColor.BLACK);
		add(detailPageText);

		helpText = new FlxText(margin, FlxG.height - 38, contentWidth, "Mouse: choose/scan/import   Up/Down: action   Page Up/Down or wheel: details   Back: return", 15);
		helpText.setFormat("assets/fonts/vcr.ttf", 15, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(helpText);

		refreshActionFocus();
		refreshButtons();
		refreshDetails();
		#if sys
		progressPresentation = new ImportRefreshProgressBar(this, progressPresentationStatus, true);
		add(progressPresentation);
		#end
		super.create();
	}

	override function update(elapsed:Float) {
		var coordinatorBusy = false;
		var coordinatorSnapshotKnown = false;
		#if sys
		if (!hasJobHandle()) {
			var coordinatorStatus = ImportRefreshManager.browseTick();
			coordinatorBusy = coordinatorStatus != null && coordinatorStatus.busy;
			coordinatorSnapshotKnown = true;
		}
		if (coordinatorBusy)
			coordinatorWasBusy = true;
		else if (coordinatorWasBusy)
			coordinatorWasBusy = false;
		// Synchronize controls before FlxState updates its children. A parent can
		// resume after a substate while a background worker changed its state.
		// This prevents one stale frame with an enabled navigation or Cancel button.
		refreshButtons(coordinatorSnapshotKnown ? coordinatorBusy : null);
		#end
		super.update(elapsed);
		#if sys
		var diagnosticCount = ImportRefreshManager.diagnosticCount();
		if (diagnosticCount != refreshDiagnosticCount) {
			refreshDiagnosticCount = diagnosticCount;
			refreshDetails();
		}
		#end

		// A worker can finish between frames.  At that point hasActiveJob()
		// becomes false, but the completed handle still needs one main-thread
		// poll so its result can be transferred into scanResult/importStatus.
		// Without this distinction the UI skipped the completed snapshot and
		// remained on "scan-complete" with "No completed scan." forever.
		if (hasJobHandle()) {
			var backPressed = controls.BACK || FlxG.keys.justPressed.ESCAPE
				|| FlxG.keys.justPressed.BACKSPACE;
			if (backPressed && importJob != null) {
				// Back only hides the manual import UI. ImportRefreshManager owns
				// the reservation, report, and main-thread publication lifecycle.
				detachImportAndLeave();
				return;
			}
			if (backPressed && scanJob != null)
				cancelActiveJob();
			pollJobs();
			// Keep input disabled while a handle is still active.  If pollJobs()
			// consumed a completed handle, allow the normal UI path to continue
			// on the next frame (or cancel a still-running scan when Back is held).
			if (hasJobHandle())
				return;
			if (backRequested)
				return;
			if (backPressed)
				cancelActiveJob();
			return;
		}
		if (backRequested) {
			leaveState();
			return;
		}

		if (controls.BACK || FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE) {
			leaveState();
			return;
		}

		if (FlxG.keys.justPressed.PAGEUP)
			changeDetailPage(-1);
		else if (FlxG.keys.justPressed.PAGEDOWN)
			changeDetailPage(1);
		else if (detailPanel != null && FlxG.mouse.overlaps(detailPanel) && FlxG.mouse.wheel != 0)
			changeDetailPage(FlxG.mouse.wheel > 0 ? -1 : 1);

		if (controls.UP_MENU)
			changeAction(-1);
		else if (controls.DOWN_MENU)
			changeAction(1);
		else if (controls.ACCEPT)
			acceptAction();
		else if (controls.LEFT_MENU)
			changeImportType(-1);
		else if (controls.RIGHT_MENU)
			changeImportType(1);
	}

	override function destroy():Void {
		stateAlive = false;
		// Do not tear down the state while a native worker can still be writing.
		// The normal Back path waits for completion; this is a final safety net
		// for global resets or application shutdown.
		if (scanJob != null && !scanJob.isFinished())
			scanJob.cancel();
		if (importJob != null && !importJob.isFinished())
			importJob.cancel();
		super.destroy();
	}

	function hasActiveJob():Bool {
		return packageNamePromptOpen || (scanJob != null && !scanJob.isFinished())
			|| (importJob != null && !importJob.isFinished());
	}

	/** True while a job handle still needs to be polled, including the short
	 * handoff window after its worker has set done=true. */
	function hasJobHandle():Bool {
		return scanJob != null || importJob != null;
	}

	function hasCancelableWorker():Bool {
		return !packageNamePromptOpen && ((scanJob != null && !scanJob.isFinished())
			|| (importJob != null && !importJob.isFinished()));
	}

	function coordinatorWorkBusy():Bool {
		#if sys
		return !hasJobHandle() && ImportRefreshManager.browseTick().busy;
		#else
		return false;
		#end
	}

	function layoutActionButtons(margin:Int, y:Int, availableWidth:Int):Void {
		var buttons:Array<FlxUIButton> = [chooseSourceButton, scanButton, importSourceButton, cancelButton];
		var widths = 0.0;
		for (button in buttons) widths += button.width;
		var gap:Float = 12;
		if (widths + gap * (buttons.length - 1) > availableWidth)
			gap = Math.max(2, (availableWidth - widths) / (buttons.length - 1));
		var x:Float = margin;
		for (button in buttons) {
			button.setPosition(x, y);
			x += button.width + gap;
		}
	}

	#if sys
	function progressPresentationStatus():Dynamic {
		if (packageNamePromptOpen) return null;
		var snapshot:ImportWorkflowProgress = null;
		var label = "";
		if (scanJob != null) {
			snapshot = scanJob.snapshot();
			label = "Scanning as " + importTypeAtScan;
		} else if (importJob != null) {
			snapshot = importJob.snapshot();
			label = "Importing as " + importTypeAtScan;
		}
		if (snapshot == null || snapshot.complete) return null;
		if (backRequested) label = "Stopping the active job safely...";
		return {
			busy: true,
			label: label,
			phase: snapshot.phase == null ? "working" : snapshot.phase,
			current: snapshot.current == null ? "" : snapshot.current,
			completed: Std.int(Math.max(0, snapshot.completed)),
			total: Std.int(Math.max(0, snapshot.total)),
			fraction: snapshot.progress,
			complete: false,
			changed: false,
			blocked: false
		};
	}
	#end

	function acceptAction():Void {
		switch (actionIndex) {
			case ACTION_CHOOSE:
				chooseSourceFolder();
			case ACTION_SCAN:
				startScan();
			case ACTION_IMPORT:
				startImport();
		}
	}

	function changeAction(change:Int):Void {
		var next = actionIndex;
		for (_ in 0...3) {
			next += change < 0 ? -1 : 1;
			if (next < ACTION_CHOOSE)
				next = ACTION_IMPORT;
			if (next > ACTION_IMPORT)
				next = ACTION_CHOOSE;
			if (actionEnabled(next)) {
				actionIndex = next;
				break;
			}
		}
		refreshActionFocus();
	}

	function actionEnabled(index:Int):Bool {
		if (hasActiveJob())
			return false;
		return switch (index) {
			case ACTION_CHOOSE: true;
			case ACTION_SCAN: sourcePathIsValid();
			case ACTION_IMPORT: canImport();
			default: false;
		};
	}

	function refreshActionFocus():Void {
		if (chooseSourceButton != null)
			chooseSourceButton.alpha = actionIndex == ACTION_CHOOSE && actionEnabled(ACTION_CHOOSE) ? 1.0 : 0.65;
		if (scanButton != null)
			scanButton.alpha = actionIndex == ACTION_SCAN && actionEnabled(ACTION_SCAN) ? 1.0 : 0.65;
		if (importSourceButton != null)
			importSourceButton.alpha = actionIndex == ACTION_IMPORT && actionEnabled(ACTION_IMPORT) ? 1.0 : 0.65;
	}

	function refreshButtons(?knownCoordinatorBusy:Null<Bool>):Void {
		var manualBusy = hasActiveJob() || hasJobHandle();
		var coordinatorBusy = false;
		#if sys
		if (!hasJobHandle()) {
			coordinatorBusy = knownCoordinatorBusy == null
				? ImportRefreshManager.browseTick().busy : knownCoordinatorBusy;
			if (coordinatorBusy) coordinatorWasBusy = true;
		}
		#end
		var busy = manualBusy || coordinatorBusy;
		var canCancel = hasCancelableWorker();
		var sourceValid = sourcePathIsValid();
		if (chooseSourceButton != null) {
			chooseSourceButton.active = !busy;
			chooseSourceButton.alpha = !busy && actionIndex == ACTION_CHOOSE ? 1.0 : (!busy ? 0.65 : 0.35);
		}
		if (scanButton != null) {
			scanButton.active = !busy && sourceValid;
			scanButton.alpha = !busy && sourceValid && actionIndex == ACTION_SCAN ? 1.0 : (!busy && sourceValid ? 0.65 : 0.35);
		}
		if (importSourceButton != null) {
			importSourceButton.active = !busy && canImport();
			importSourceButton.alpha = !busy && canImport() && actionIndex == ACTION_IMPORT ? 1.0 : (!busy && canImport() ? 0.65 : 0.35);
		}
		if (cancelButton != null) {
			cancelButton.visible = canCancel;
			cancelButton.active = canCancel;
			cancelButton.alpha = canCancel ? 1.0 : 0.0;
		}
		if (importStatus != null) importStatus.visible = !busy;
		if (scanSummary != null) scanSummary.visible = !busy;
		if (helpText != null) {
			helpText.text = canCancel && importJob != null
				? "Import running. Back hides this screen; Cancel requests a safe stop."
				: canCancel
				? "Scan running. Back/Cancel requests a safe stop; the screen closes after this step."
				: coordinatorBusy
					? "Automatic refresh continues in background. Ready songs remain playable; import actions are paused."
					: manualBusy
						? "Finishing import. Back hides this screen while package handoff completes."
					: "Mouse: choose/scan/import   Up/Down: action   Page Up/Down or wheel: details   Back: return";
		}
	}

	function changeImportType(change:Int):Void {
		if (hasActiveJob() || coordinatorWorkBusy() || importTypes == null || importTypes.length == 0)
			return;
		importTypeIndex += change < 0 ? -1 : 1;
		if (importTypeIndex < 0)
			importTypeIndex = importTypes.length - 1;
		if (importTypeIndex >= importTypes.length)
			importTypeIndex = 0;
		ImportSettings.setSelectedType(importTypes[importTypeIndex]);
		clearScan("Importer changed. Scan the source again.");
		refreshImportType();
		refreshButtons();
	}

	function refreshImportType():Void {
		if (importTypeSelector == null)
			return;
		if (importTypes == null || importTypes.length == 0)
			importTypeSelector.text = "None";
		else
			importTypeSelector.text = "< " + importTypes[importTypeIndex] + " >";
	}

	function sourcePathIsValid():Bool {
		#if sys
		var sourcePath = ImportSettings.getSourcePath();
		return sourcePath != null && StringTools.trim(sourcePath) != '' && FileSystem.isDirectory(sourcePath)
			&& ModuleFunctions.isSafeImportSource(sourcePath);
		#else
		return false;
		#end
	}

	function currentSourcePath():String {
		return ImportSettings.normalizeSourcePath(ImportSettings.getSourcePath());
	}

	function canImport():Bool {
		return scanJob == null && importJob == null && scanResult != null && sourcePathIsValid()
			&& ImportSettings.normalizeSourcePath(sourcePathAtScan) == currentSourcePath()
			&& ImportSettings.normalizeType(importTypeAtScan) == currentImportType()
			// A duplicate-safe pass can still repair registries/dependencies and copy
			// newly discovered shared assets.  Do not strand that work merely because
			// every chart itself is already present.
			&& (scanResult.songsFound > 0 || scanResult.assetsToImport > 0
				|| (scanResult.globalPacksToImport != null && scanResult.globalPacksToImport > 0)
				|| (scanResult.overlayPlanned != null && scanResult.overlayPlanned > 0));
	}

	function currentImportType():String {
		return ImportSettings.normalizeType(importTypes == null || importTypes.length == 0
			? ImportSettings.getSelectedType()
			: importTypes[importTypeIndex]);
	}

	function refreshSourcePath():Void {
		if (sourcePathSelector == null)
			return;
		var sourcePath = ImportSettings.getSourcePath();
		sourcePathSelector.text = sourcePath == '' ? "Not selected (choose a folder)" : shortenPath(sourcePath, 88);
	}

	function chooseSourceFolder():Void {
		if (hasActiveJob() || coordinatorWorkBusy()) {
			refreshButtons();
			return;
		}
		#if sys
		var dialog = new FileDialog();
		dialog.onSelect.add(function(path:String):Void {
			if (!stateAlive)
				return;
			var normalized = ImportSettings.normalizeSourcePath(path);
			if (normalized == '' || !FileSystem.isDirectory(normalized)) {
				importStatus.text = "That folder could not be opened.";
				return;
			}
			if (!ModuleFunctions.isSafeImportSource(normalized)) {
				importStatus.text = "The current game's assets cannot be selected as a source.";
				return;
			}
			ImportSettings.setSourcePath(normalized);
			clearScan("Source folder changed. Press Scan to inspect it.");
			refreshSourcePath();
			refreshButtons();
		});
		if (!dialog.browse(FileDialogType.OPEN_DIRECTORY, null, ImportSettings.getSourcePath(), ImportSettings.sourceDialogTitle(currentImportType())))
			importStatus.text = "Folder selection is unavailable on this target.";
		#end
	}

	function clearScan(message:String):Void {
		if (hasActiveJob())
			return;
		scanResult = null;
		sourcePathAtScan = '';
		importTypeAtScan = '';
		detailPage = 0;
		detailLines = [];
		if (importStatus != null)
			importStatus.text = message;
		if (scanSummary != null)
			scanSummary.text = "No completed scan.";
		refreshDetails();
	}

	function startScan():Void {
		#if sys
		if (hasActiveJob() || coordinatorWorkBusy()) {
			refreshButtons();
			return;
		}
		var sourcePath = currentSourcePath();
		if (!sourcePathIsValid()) {
			importStatus.text = "Choose a valid, safe source folder first.";
			return;
		}
		clearScan("Starting read-only scan...");
		sourcePathAtScan = sourcePath;
		importTypeAtScan = currentImportType();
		scanJob = ImportWorkflow.beginSongScan(sourcePath, importTypeAtScan);
		backRequested = false;
		importStatus.text = "Scanning as " + importTypeAtScan + "...";
		if (progressPresentation != null) progressPresentation.invalidateStatus();
		refreshButtons();
		#else
		importStatus.text = "Song scanning is unavailable on this target.";
		#end
	}

	function startImport():Void {
		#if sys
		if (hasActiveJob() || coordinatorWorkBusy()) {
			refreshButtons();
			return;
		}
		if (!canImport()) {
			importStatus.text = "Run a successful scan first; Import is disabled until then.";
			return;
		}
		var requests = ImportPackageNamePrompt.collectUnnamedRoots(cast scanResult.songs);
		if (requests.length > 0) {
			packageNamePromptOpen = true;
			importStatus.text = "Name each package without authored metadata before importing.";
			refreshButtons();
			openSubState(new ImportPackageNameSubState(requests, function(packageNames:Map<String, String>):Void {
				packageNamePromptOpen = false;
				if (!stateAlive)
					return;
				if (packageNames == null) {
					importStatus.text = "Import cancelled before writing any files.";
					refreshButtons();
					return;
				}
				beginImport(packageNames);
			}));
			return;
		}
		beginImport(null);
		#else
		importStatus.text = "Song importing is unavailable on this target.";
		#end
	}

	function beginImport(packageNames:Map<String, String>):Void {
		#if sys
		if (coordinatorWorkBusy()) {
			importStatus.text = "An automatic refresh is running. Import actions unlock when it finishes.";
			refreshButtons();
			return;
		}
		if (!canImport()) {
			importStatus.text = "The scan is no longer current. Scan the selected folder again.";
			refreshButtons();
			return;
		}
		var sourcePath = currentSourcePath();
		importJob = ImportWorkflow.beginSongImport(sourcePath, scanResult, currentImportType(), packageNames);
		backRequested = false;
		importStatus.text = "Importing as " + currentImportType() + "...";
		if (progressPresentation != null) progressPresentation.invalidateStatus();
		refreshButtons();
		#else
		importStatus.text = "Song importing is unavailable on this target.";
		#end
	}

	function cancelActiveJob():Void {
		// The naming substate owns its own Cancel/Escape handling. Do not ask a
		// nonexistent worker to stop while that modal is active.
		if (packageNamePromptOpen)
			return;
		if (!hasCancelableWorker())
			return;
		backRequested = true;
		if (scanJob != null && !scanJob.isFinished())
			scanJob.cancel();
		if (importJob != null && !importJob.isFinished())
			importJob.cancel();
		importStatus.text = "Stopping the active job safely...";
		if (progressPresentation != null) progressPresentation.invalidateStatus(false);
	}

	function pollJobs():Void {
		if (scanJob != null) {
			var snapshot = scanJob.snapshot();
			if (snapshot.complete) {
				var completedResult:ImportScanResult = cast snapshot.result;
				scanJob = null;
				if (completedResult != null) {
					scanResult = completedResult;
					importTypeAtScan = ImportSettings.normalizeType(completedResult.importType == null ? importTypeAtScan : completedResult.importType);
					// Keep the identity captured by the completed plan.  Reading the
					// mutable settings path here could accept a scan for donor A after
					// the source was changed to donor B while the worker was finishing.
					var completedSource = ImportSettings.normalizeSourcePath(completedResult.source);
					if (completedSource != '')
						sourcePathAtScan = completedSource;
					showScanResult(scanResult);
					importStatus.text = scanResult.errors != null && scanResult.errors.length > 0
						? "Scan complete with warnings. Review the details/report before importing."
						: "Scan complete. Review duplicates and missing dependencies, then import planned content.";
				} else {
					scanResult = null;
					importStatus.text = snapshot.error == null ? "Scan failed." : "Scan failed: " + snapshot.error;
				}
				if (progressPresentation != null) progressPresentation.invalidateStatus();
				refreshButtons();
				if (backRequested)
					leaveState();
			}
			return;
		}

		if (importJob != null) {
			var snapshot = importJob.snapshot();
			if (snapshot.complete) {
				var imported:Dynamic = snapshot.result;
				importJob = null;
				if (imported != null) {
					importStatus.text = ModuleFunctions.importBatchSummary(cast imported, true);
					appendImportSummary(cast imported);
				} else {
					importStatus.text = snapshot.error == null ? "Import failed." : "Import failed: " + snapshot.error;
				}
				if (progressPresentation != null) progressPresentation.invalidateStatus();
				refreshButtons();
				if (backRequested)
					leaveState();
			}
		}
	}

	function showScanResult(result:ImportScanResult):Void {
		if (result == null)
			return;
		var selectedType = ImportSettings.normalizeType(result.importType == null ? currentImportType() : result.importType);
		var detectedRootCount = result.detectedRoots == null ? 0 : result.detectedRoots.length;
		var rootEngines:Array<String> = result.detectedEngines == null ? [] : result.detectedEngines.copy();
		if (rootEngines.length == 0 && result.detectedRoots != null)
			for (root in result.detectedRoots) {
				if (root == null)
					continue;
				var engine = root.engine == null || StringTools.trim(root.engine) == '' ? selectedType : root.engine;
				if (rootEngines.indexOf(engine) < 0)
					rootEngines.push(engine);
			}
		// Do not include root paths or a long engine-name list here.  This field
		// has a fixed height and is a summary; the detail pages contain the
		// complete root/evidence information.
		var rootScanNote = result.rootScanTruncated == true ? "    ROOT SCAN TRUNCATED" : "";
		var packageScanNote = result.packageScanTruncated == true ? "    PACKAGE SCAN TRUNCATED" : "";
		scanSummary.text = "Importer: " + selectedType + "    Roots detected: " + detectedRootCount
			+ "    Engine types: " + rootEngines.length + rootScanNote + packageScanNote
			+ "\nSongs: " + result.songsFound + " found / " + result.songsToImport + " new / " + result.duplicateSongs + " duplicate"
			+ "    Global packs: " + (result.globalPacksToImport == null ? 0 : result.globalPacksToImport)
			+ "    Charts: " + result.chartsFound
			+ "    Characters: " + result.charactersFound
			+ "    Stages: " + result.stagesFound
			+ "\nAssets: " + result.assetFilesFound + " found / " + result.assetsToImport + " new / " + result.duplicateAssets + " duplicate"
			+ "    UI: " + result.uiPacksFound
			+ "    Layouts: " + result.layoutsFound
			+ "    Cutscenes: " + result.cutscenesFound
			+ "\nMissing: " + result.missingDependencies
			+ "    Overlays: " + (result.overlayPlanned == null ? 0 : result.overlayPlanned)
			+ "    Report: " + shortenPath(result.logPath, 90);

		detailLines = [];
		if (result.importerSuggestions != null)
			for (suggestion in result.importerSuggestions)
				detailLines.push("[SUGGESTION] " + shortenPath(suggestion, 88));
		if (result.detectedRoots != null)
			for (root in result.detectedRoots) {
				if (root == null)
					continue;
				detailLines.push("[ROOT] "
					+ (root.engine == null || StringTools.trim(root.engine) == '' ? selectedType : root.engine)
					+ (root.confidence <= 0 ? '' : " (confidence " + Std.string(root.confidence) + ")"));
				if (root.path != null && StringTools.trim(root.path) != '')
					detailLines.push("  path: " + shortenPath(root.path, 88));
				if (root.reason != null && StringTools.trim(root.reason) != '')
					detailLines.push("  " + root.reason);
				if (root.evidence != null)
				for (evidence in root.evidence)
					if (evidence != null && StringTools.trim(evidence) != '')
						detailLines.push("  evidence: " + evidence);
			}
		if (result.rootScanDiagnostics != null)
			for (diagnostic in result.rootScanDiagnostics) {
				if (diagnostic == null)
					continue;
				var severity = diagnostic.severity == null ? "diagnostic" : diagnostic.severity.toUpperCase();
					detailLines.push("[ROOT SCAN " + severity + "] " + diagnostic.code
						+ " (" + diagnostic.scannedDirectories + "/" + diagnostic.directoryLimit
						+ ", " + diagnostic.queuedDirectories + " queued)");
			}
		if (result.packageScanDiagnostics != null)
			for (diagnostic in result.packageScanDiagnostics) {
				if (diagnostic == null)
					continue;
				var packageSeverity = diagnostic.severity == null ? "diagnostic" : diagnostic.severity.toUpperCase();
					detailLines.push("[PACKAGE SCAN " + packageSeverity + "] " + diagnostic.code
						+ " (" + diagnostic.scannedDirectories + "/" + diagnostic.directoryLimit
						+ ", " + diagnostic.queuedDirectories + " queued)");
			}
		var rejectedSongCount = result.rejectedSongCount == null
			? (result.rejectedSongs == null ? 0 : result.rejectedSongs.length) : result.rejectedSongCount;
		if (rejectedSongCount > 0) {
			detailLines.push("[REJECTED SONG CANDIDATES] " + rejectedSongCount
				+ (result.rejectedSongsTruncated == true ? " (details truncated)" : ""));
			if (result.rejectedSongs != null)
				for (rejection in result.rejectedSongs) {
					if (rejection == null)
						continue;
					var code = rejection.code == null ? "invalid-song-import" : rejection.code.toUpperCase();
					var engine = rejection.engine == null || StringTools.trim(rejection.engine) == ""
						? "" : " [" + rejection.engine + "]";
					detailLines.push("[REJECTED SONG " + code + "] " + rejection.song + engine);
					if (rejection.sourceRoot != null && StringTools.trim(rejection.sourceRoot) != "")
						detailLines.push("  source root: " + shortenPath(rejection.sourceRoot, 88));
					if (rejection.sourcePath != null && StringTools.trim(rejection.sourcePath) != "")
						detailLines.push("  chart folder: " + shortenPath(rejection.sourcePath, 88));
					detailLines.push("  reason: " + rejection.reason);
					if (rejection.charts != null)
						for (chart in rejection.charts)
							detailLines.push("  chart: " + shortenPath(chart, 88));
					if (rejection.chartsTruncated == true)
						detailLines.push("  chart list truncated.");
				}
		}
		if ((result.overlayPlanned != null && result.overlayPlanned > 0)
			|| (result.overlayDiagnostics != null && result.overlayDiagnostics.length > 0)) {
			detailLines.push("[OVERLAY] " + result.overlayPlanned + " operation(s) planned");
			if (result.overlayProvenance != null)
				for (provenance in result.overlayProvenance)
					detailLines.push("  provenance: " + provenance);
			if (result.overlayDiagnostics != null)
				for (diagnostic in result.overlayDiagnostics)
					detailLines.push("  " + diagnostic);
		}
		var informationalRows:Array<String> = [];
		for (song in result.songs) {
			if (song.duplicate) {
				detailLines.push("[DUPLICATE SONG] " + song.name + " (not moved) -> assets/data/" + song.name.toLowerCase());
				if (song.reason != null && StringTools.trim(song.reason) != '')
					detailLines.push("  reason: " + shortenPath(song.reason, 88));
				if (song.source != null && StringTools.trim(song.source) != '')
					detailLines.push("  candidate source: " + shortenPath(song.source, 88));
			}
			if (song.diagnostics != null)
				for (diagnostic in song.diagnostics) {
					var label = diagnosticDetailLabel(diagnostic);
					var row = label + " " + song.name + ": " + shortenPath(diagnostic, 88);
					if (label == "[INFO]")
						informationalRows.push(row);
					else
						detailLines.push(row);
				}
			for (dependency in song.missing) {
				detailLines.push("[MISSING] " + dependency.kind + " '" + dependency.reference + "'");
				detailLines.push("  chart/script: " + shortenPath(dependency.origin, 88));
				if (dependency.searched != null && dependency.searched.length > 0)
					detailLines.push("  looked for: " + shortenPath(dependency.searched[0], 88));
			}
		}
		for (asset in result.assets) {
			if (asset.duplicate)
				detailLines.push("[DUPLICATE ASSET] " + asset.kind + " " + asset.name + " (not moved) -> " + shortenPath(asset.destination, 88));
		}
		if (result.errors != null)
			for (error in result.errors)
				detailLines.push("[ERROR] " + shortenPath(error, 88));
		if (informationalRows.length > 0) {
			detailLines.push("");
			detailLines.push("[INFO] Compatibility evidence (actionable findings are listed above)");
			for (row in informationalRows)
				detailLines.push(row);
		}
		if (detailLines.length == 0)
			detailLines.push("No duplicate songs/assets or missing dependencies were detected.");
		detailPage = 0;
		refreshDetails();
	}

	/** Keep compatibility evidence distinct from actionable failures.  Import
	 * diagnostics retain their stable `[code]` prefix, so this remains generic
	 * across every supported donor engine and does not inspect chart names. */
	static function diagnosticDetailLabel(diagnostic:String):String {
		return ImportDiagnostic.label(diagnostic);
	}

	function appendImportSummary(result:Dynamic):Void {
		if (result == null)
			return;
		detailLines.push("");
		detailLines.push("[IMPORT COMPLETE] " + ModuleFunctions.importBatchSummary(cast result, true));
		refreshDetails();
	}

	function detailsPerPage():Int {
		if (detailText == null || detailText.fieldHeight <= 0)
			return 8;
		// wordWrap=false makes every manually wrapped detail row one visual
		// line, so use a conservative line height for the fixed panel.
		return Std.int(Math.max(4, Math.floor(detailText.fieldHeight / DETAIL_LINE_HEIGHT)));
	}

	function detailCharsPerLine():Int {
		if (detailText == null || detailText.fieldWidth <= 0)
			return 48;
		// VCR is close to monospaced.  Leave a little horizontal slack so a
		// manually wrapped row remains a single row after the outline is drawn.
		return Std.int(Math.max(24, Math.floor(detailText.fieldWidth / (DETAIL_FONT_SIZE * 0.60))));
	}

	/** Wrap one diagnostic row before it reaches FlxText.  This handles paths
	 * and asset names without spaces by hard-splitting them, while preferring a
	 * nearby space for prose. */
	static function wrapDetailLine(line:String, maxChars:Int):Array<String> {
		var wrapped:Array<String> = [];
		if (line == null)
			line = '';
		if (maxChars < 8)
			maxChars = 8;
		var remaining = line;
		while (remaining.length > maxChars) {
			var splitAt = remaining.substr(0, maxChars + 1).lastIndexOf(' ');
			if (splitAt < Std.int(maxChars * 0.55))
				splitAt = maxChars;
			wrapped.push(StringTools.rtrim(remaining.substr(0, splitAt)));
			remaining = StringTools.ltrim(remaining.substr(splitAt));
		}
		wrapped.push(remaining);
		return wrapped;
	}

	function wrappedDetailLines():Array<String> {
		var wrapped:Array<String> = [];
		var lines = detailLines == null ? [] : detailLines.copy();
		#if sys
		var diagnostics = ImportRefreshManager.diagnostics();
		if (diagnostics.length > 0) {
			var warnings = [for (message in diagnostics) "[IMPORT REFRESH WARNING] " + message];
			warnings.push("");
			lines = warnings.concat(lines);
		}
		#end
		var maxChars = detailCharsPerLine();
		for (line in lines)
			for (piece in wrapDetailLine(line, maxChars))
				wrapped.push(piece);
		return wrapped;
	}

	function changeDetailPage(change:Int):Void {
		var perPage = detailsPerPage();
		var maxPage = maxDetailPage(perPage);
		detailPage += change;
		if (detailPage < 0)
			detailPage = 0;
		if (detailPage > maxPage)
			detailPage = maxPage;
		refreshDetails();
	}

	function maxDetailPage(perPage:Int):Int {
		var visibleLines = wrappedDetailLines();
		if (visibleLines.length == 0 || perPage <= 0)
			return 0;
		return Std.int(Math.ceil(visibleLines.length / perPage)) - 1;
	}

	function refreshDetails():Void {
		if (detailText == null)
			return;
		var visibleLines = wrappedDetailLines();
		var perPage = detailsPerPage();
		var maxPage = maxDetailPage(perPage);
		if (detailPage > maxPage)
			detailPage = maxPage;
		var start = detailPage * perPage;
		var visible:Array<String> = [];
		var remaining = Std.int(Math.max(0, visibleLines.length - start));
		var visibleCount = Std.int(Math.min(perPage, remaining));
		for (i in 0...visibleCount)
			visible.push(visibleLines[start + i]);
		detailText.text = visible.length == 0 ? "Scan details will appear here." : visible.join("\n");
		detailPageText.text = maxPage > 0 ? "Details page " + (detailPage + 1) + "/" + (maxPage + 1) + "   (Page Up/Down or mouse wheel)" : "";
	}

	function shortenPath(path:String, maxLength:Int):String {
		if (path == null)
			return '';
		var value = StringTools.trim(path);
		// Flixel's text field is deliberately single-line for details.  Keep
		// entries readable at smaller window sizes while the report preserves
		// the unshortened path for diagnosis.
		if (detailText != null && detailText.fieldWidth > 0) {
			var widthLimit = Std.int(detailText.fieldWidth / Math.max(7, DETAIL_FONT_SIZE * 0.52));
			maxLength = Std.int(Math.min(maxLength, Math.max(28, widthLimit)));
		}
		if (value.length <= maxLength)
			return value;
		if (maxLength < 12)
			return value.substr(0, maxLength);
		return value.substr(0, 8) + "..." + value.substr(value.length - (maxLength - 11));
	}

	function leaveState():Void {
		if (importJob != null) {
			detachImportAndLeave();
			return;
		}
		if (hasActiveJob()) {
			cancelActiveJob();
			return;
		}
		backRequested = false;
		LoadingState.loadAndSwitchState(new SaveDataState());
	}

	function detachImportAndLeave():Void {
		// Dropping only this view's handle does not stop the worker. The manager
		// retained the job reservation and completes the import/handoff in safe
		// menu frames; reopening Import Settings reads its shared status card.
		importJob = null;
		backRequested = false;
		if (progressPresentation != null)
			progressPresentation.invalidateStatus();
		LoadingState.loadAndSwitchState(new SaveDataState());
	}
}
