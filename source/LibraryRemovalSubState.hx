package;

import flixel.FlxG;
import flixel.text.FlxText;

/** Explicit confirmation of a worker-validated, recoverable installed removal. */
class LibraryRemovalSubState extends LibraryMenuSubState {
	var owner:String;
	var displayTitle:String;
	var onPublished:Void->Void;
	var detail:FlxText;
	var signature:String = '';
	var notified:Bool = false;
	var started:Bool = false;
	/** Import work is running, so no review can start until it has finished. */
	var waitingForImport:Bool = false;
	/** Import generation the current review was started under. A publish since then makes it stale. */
	var previewGeneration:Int = 0;
	/** 0 asks about the chosen mod, 1 asks again about the mods linked to it. */
	var step:Int = 0;

	public function new(owner:String, ?onPublished:Void->Void, ?displayTitle:String) {
		super(); this.owner = owner; this.onPublished = onPublished;
		this.displayTitle = displayTitle == null ? '' : StringTools.trim(displayTitle);
		cardTitle = this.displayTitle;
	}
	override function create():Void {
		super.create();
		// Under the two or three choices this dialog ever offers.
		detail = new FlxText(panelX + 32, rowsY + 3 * LibraryMenuSubState.ROW_PITCH + 6, LibraryMenuSubState.PANEL_WIDTH - 64, '', 14);
		detail.setFormat('assets/fonts/vcr.ttf', 14, 0xFFCFD8E5, LEFT); add(detail);
		backAction = leaveOrCancel;
		#if sys
		// Import work blocks every removal, so the review starts once it is done.
		started = LibraryRemovalPresentation.eligible(owner) && !ImportRefreshManager.removalWaitStatus().busy && review();
		#end
		refreshRemoval();
	}
	#if sys
	/** Starts the worker review and remembers which import generation it describes. */
	function review():Bool {
		var generation = ImportRefreshManager.generation;
		if (!ImportRemovalManager.beginPreview(owner)) return false;
		previewGeneration = generation;
		return true;
	}
	#end
	function leaveOrCancel():Void {
		#if sys
		var state = ImportRemovalManager.poll();
		if (started && state.busy) {
			if (state.cancellable) ImportRemovalManager.cancel();
			return;
		}
		#end
		close();
	}
	/** Never leaves the player on an empty popup: a failure here is shown as text with a way back. */
	function refreshRemoval():Void {
		try refreshRemovalNow() catch (error:Dynamic) {
			var failure = 'failed:' + Std.string(error);
			if (signature != failure) { signature = failure; showActions('Removal unavailable', [{label:'Return', run:function() close()}]); }
			detail.text = 'The removal screen ran into a problem. Nothing was removed.\n' + Std.string(error);
		}
	}
	function refreshRemovalNow():Void {
		#if sys
		var state = ImportRemovalManager.poll();
		var wait = ImportRefreshManager.removalWaitStatus();
		if (LibraryRemovalPresentation.eligible(owner) && wait.busy && !state.busy && LibraryRemovalPresentation.waitsForImport(state.phase)) {
			// A refresh holds the packages and no removal can be reserved until it ends.
			waitingForImport = true; started = false;
			if (signature != 'import-wait') { signature = 'import-wait'; showActions('Mod refresh in progress', [{label:'Return', run:function() close()}]); }
			detail.text = LibraryRemovalPresentation.importWaitSummary(wait.label, wait.fraction, wait.queued);
			status.text = wait.label;
			return;
		}
		if ((waitingForImport || !started) && LibraryRemovalPresentation.eligible(owner) && !state.busy && state.phase != 'conflict' && state.phase != 'cleanup-pending') {
			// The refresh is over (or recovery has settled): review the removal now.
			var wasWaiting = waitingForImport; waitingForImport = false;
			if (review()) { started = true; signature = ''; state = ImportRemovalManager.poll(); }
			else if (wasWaiting) signature = '';
		}
		if (started && !state.busy && (state.phase == 'preview' || state.phase == 'blocked') && previewGeneration != ImportRefreshManager.generation
			&& LibraryRemovalPresentation.eligible(owner) && review()) {
			// A refresh published after this review began, so what it shows may be out of date. Check again.
			signature = ''; state = ImportRemovalManager.poll();
		}
		if (!started) {
			var entries:Array<LibraryMenuSubState.LibraryMenuAction> = [{label:'Return', run:function() close()}];
			if (!state.busy && (state.phase == 'conflict' || state.phase == 'cleanup-pending')) entries.push({label:'Retry interrupted removal recovery', run:function() ImportRemovalManager.retryCleanup()});
			else if (!state.busy && LibraryRemovalPresentation.eligible(owner)) entries.push({label:'Review this installed package again', run:function() { started = review(); signature = ''; }});
			var unavailableKey = 'unavailable:' + state.phase + ':' + state.busy + ':' + state.label;
			if (signature != unavailableKey) { signature = unavailableKey; showActions('Removal unavailable', entries); }
			detail.text = (owner == '' ? 'Recover an interrupted operation before starting another removal.\n' : 'Select an installed imported package with committed ownership.\n') + state.label;
			if (owner == '' && ImportedFreeplayCaller.ownerForFreeplay(CodenameModRuntime.activeRoot()) != '') detail.text += '\nReturn to Imported Mods to release the active source session before recovery.';
			return;
		}
		var plan = state.plan;
		var linked = LibraryRemovalPresentation.linked(plan);
		var confirming = LibraryRemovalPresentation.confirmable(state.phase, state.busy, plan);
		if (!confirming || linked.length == 0) step = 0;
		var key = state.phase + ':' + state.busy + ':' + state.cancellable + ':' + state.published + ':' + state.label + ':' + step;
		if (key != signature) {
			signature = key;
			var entries:Array<LibraryMenuSubState.LibraryMenuAction> = [];
			var title = 'Remove installed mod?';
			if (confirming) {
				// Keeping is always first, so the default choice never deletes anything.
				var total = linked.length + 1;
				if (step == 1) title = 'Also remove ' + linked.length + ' linked mod' + (linked.length == 1 ? '?' : 's?');
				entries.push({label:step == 1 ? 'NO   Keep all ' + total + ' mods installed' : 'NO   Keep it installed',
					run:leaveOrCancel, tone:LibraryRemovalPresentation.NO_COLOR});
				entries.push({label:step == 1 ? 'YES  Remove all ' + total + ' mods' : 'YES  Remove this mod',
					tone:LibraryRemovalPresentation.YES_COLOR, run:function() {
						if (step == 0 && linked.length > 0) step = 1; else ImportRemovalManager.confirm();
						signature = ''; refreshRemoval();
					}});
			} else if (state.busy) {
				title = state.phase == 'preview' ? 'Checking installed mod' : 'Removing installed mod';
				if (state.cancellable) entries.push({label:'Cancel and restore installed content', run:function() ImportRemovalManager.cancel()});
				else entries.push({label:'Finishing publication and cleanup...', run:function() {}});
			} else {
				title = state.phase == 'complete' ? 'Installed mod removed'
					: state.phase == 'cleanup-pending' ? 'Removed, cleanup pending'
					: state.phase == 'cancelled' ? 'Removal cancelled' : 'Removal blocked';
				entries.push({label:'Return', run:leaveOrCancel});
				if (LibraryRemovalPresentation.blockedByActiveSession(plan) && LibraryRemovalPresentation.eligible(owner)) {
					// A menu, Freeplay module or mod session still holds the packages. The
					// neutral removal state releases every one of them before it checks again.
					if (!Std.isOfType(FlxG.state, LibraryRemovalState))
						entries.push({label:'Close running mod menus and try again', run:function() {
							LoadingState.loadAndSwitchState(new LibraryRemovalState(owner, displayTitle));
						}});
					else entries.push({label:'Try again', run:function() {
						started = review(); signature = ''; refreshRemoval();
					}});
				}
				if (state.phase == 'cleanup-pending' || state.phase == 'conflict') entries.push({label:state.phase == 'conflict' ? 'Retry recovery (verify installed content)' : 'Retry managed cleanup', run:function() {
					ImportRemovalManager.retryCleanup(); signature = ''; refreshRemoval();
				}});
			}
			showActions(title, entries);
		}
		detail.text = step == 1 ? LibraryRemovalPresentation.linkedSummary(plan) : LibraryRemovalPresentation.summary(plan, owner, displayTitle);
		if (plan != null && plan.blockers.length > 0) {
			detail.text = 'No content will be removed.\n' + plan.blockers.join('\n');
			if (LibraryRemovalPresentation.blockedByActiveSession(plan))
				detail.text += Std.isOfType(FlxG.state, LibraryRemovalState)
					? '\nAn import or refresh is still working on these packages. Try again once it finishes.'
					: '\nChoose "Close running mod menus and try again" to release them.';
			if (detail.text.length > 1800) detail.text = detail.text.substr(0, 1800) + '\nAdditional ownership blockers recorded.';
		}
		status.text = state.label;
		if (!notified && LibraryRemovalPresentation.finished(state.phase, state.busy, state.published)) {
			notified = true; if (onPublished != null) onPublished();
		}
		#else
		showActions('Removal unavailable', [{label:'Return', run:function() close()}]);
		detail.text = 'Installed mod removal requires a native build.';
		#end
	}
	override function update(elapsed:Float):Void {
		refreshRemoval(); super.update(elapsed);
	}
}
