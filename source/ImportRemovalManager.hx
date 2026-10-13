package;

#if sys
import sys.thread.Mutex;
import sys.thread.Thread;
import ImportRemovalTransaction.ImportRemovalResult;
#end

typedef ImportRemovalStatus = {
	var phase:String;
	var busy:Bool;
	var label:String;
	var plan:Null<ImportRemovalPlan>;
	var published:Bool;
	var cancellable:Bool;
}

/** Worker filesystem work, with a reserved main-thread publication handoff. */
class ImportRemovalManager {
	#if sys
	static var mutex:Mutex = new Mutex();
	static var value:ImportRemovalStatus = {phase:'idle',busy:false,label:'',plan:null,published:false,cancellable:false};
	static var cancelRequested:Bool = false;
	static var token:String = '';
	static var pendingResult:Null<ImportRemovalResult>;
	static var pendingRecovery:Null<Array<String>>;
	static var installRoot:String;
	static var recoveryReady:Bool = false;
	static var recoveryRunning:Bool = false;
	static var protectedRoots:Array<String> = BundledImportOwnership.roots();
	static var recoveryWasRetry:Bool = false;
	static var retryPublished:Bool = false;
	static var workerCommitted:Bool = false;
	static var removedRoots:Array<String> = [];
	#end

	public static function install():Void {
		#if sys
		installRoot = Sys.getCwd();
		startRecovery(false);
		#end
	}
	#if sys
	static function startRecovery(retry:Bool):Bool {
		if (recoveryRunning) return false;
		if (token == '') token = ImportRefreshManager.reserveRemovalRecovery();
		if (token == '') {
			if (!retry) value = {phase:'conflict',busy:false,label:'',plan:null,published:false,cancellable:false};
			value.label = 'Import work must finish before removal recovery can retry.';
			return false;
		}
		recoveryRunning = true; recoveryWasRetry = retry; retryPublished = value.published || workerCommitted;
		value.busy = true; value.cancellable = false;
		value.label = 'Checking interrupted mod removals...';
		Thread.create(function() {
			var errors:Array<String>;
			try errors = ImportRemovalTransaction.recover(installRoot) catch (error:Dynamic) errors = [Std.string(error)];
			mutex.acquire(); pendingRecovery = errors; mutex.release();
		});
		return true;
	}
	static function cancelled():Bool { mutex.acquire(); var result = cancelRequested; mutex.release(); return result; }
	static function activeRoots():Array<String> {
		var roots = ImportedMenuEntry.activeOwnerRoots();
		for (root in ImportRefreshManager.removalActiveOwners()) if (roots.indexOf(root) < 0) roots.push(root);
		return roots;
	}
	static function foregroundBusy():Bool {
		return ImportWorkScheduler.gameplayActive() || Std.isOfType(flixel.FlxG.state, PlayState)
			|| Std.isOfType(flixel.FlxG.state, LoadingState);
	}
	#end
	public static function beginPreview(owner:String):Bool {
		#if sys
		poll();
		if (!recoveryReady || value.busy || token != '' || foregroundBusy() || !LibraryRemovalPresentation.eligible(owner)) return false;
		var active = activeRoots();
		cancelRequested = false; workerCommitted = false; removedRoots = [];
		value = {phase:'preview',busy:true,label:'Checking committed ownership...',plan:null,published:false,cancellable:true};
		Thread.create(function() {
			try {
				var plan = ImportRemovalTransaction.preview(installRoot,[owner],protectedRoots,active,cancelled);
				mutex.acquire();
				value.plan = plan; value.busy = false; value.cancellable = false;
				value.phase = cancelRequested ? 'cancelled' : plan.blockers.length > 0 ? 'blocked' : 'preview';
				value.label = cancelRequested ? 'Preview cancelled. Installed content is unchanged.'
					: plan.blockers.length > 0 ? plan.blockers.join('\n') : 'Review the managed content below before confirming.';
				mutex.release();
			} catch (error:Dynamic) {
				mutex.acquire(); value.busy = false; value.cancellable = false;
				value.phase = cancelRequested ? 'cancelled' : 'blocked';
				value.label = cancelRequested ? 'Preview cancelled. Installed content is unchanged.' : Std.string(error); mutex.release();
			}
		});
		return true;
		#else
		return false;
		#end
	}
	public static function confirm():Bool {
		#if sys
		poll();
		if (foregroundBusy() || !LibraryRemovalPresentation.confirmable(value.phase,value.busy,value.plan)) return false;
		var plan = value.plan;
		var active = activeRoots();
		for (root in plan.affectedOwners) if (active.indexOf(root) >= 0) {
			value.phase = 'blocked'; value.label = 'Package became active or reserved. Return and review again.'; return false;
		}
		token = ImportRefreshManager.reserveForRemoval(plan);
		if (token == '') { value.phase = 'blocked'; value.label = 'Import work or recovery is active. Return and review again.'; return false; }
		cancelRequested = false; value.phase = 'applying'; value.busy = true; value.cancellable = true;
		value.label = 'Preparing verified rollback copies...';
		Thread.create(function() {
			var result:ImportRemovalResult;
			try result = ImportRemovalTransaction.apply(installRoot,plan,protectedRoots,cancelled,function(progress:Dynamic) {
				mutex.acquire();
				if (progress.phase == 'removal-committed') { value.cancellable = false; value.label = 'Finishing managed cleanup...'; }
				else if (progress.current == null || progress.current == '') value.label = 'Preparing recoverable mod removal...';
				else value.label = 'Removing managed content: ' + Std.string(progress.current);
				mutex.release();
			}) catch (error:Dynamic) result = {status:'conflict',blockers:[Std.string(error)],affectedOwners:plan.affectedOwners,transactionId:''};
			mutex.acquire(); pendingResult = result; value.cancellable = false;
			value.label = 'Publishing the updated library...'; mutex.release();
		});
		return true;
		#else
		return false;
		#end
	}
	public static function cancel():Void {
		#if sys
		mutex.acquire(); if (value.busy && value.cancellable) { cancelRequested = true; value.label = 'Cancelling and restoring installed content...'; }
		mutex.release();
		#end
	}
	public static function retryCleanup():Bool {
		#if sys
		poll();
		if (value.busy || value.phase != 'cleanup-pending' && value.phase != 'conflict') return false;
		return startRecovery(true);
		#else
		return false;
		#end
	}
	/** Poll on the main thread. Completion is advertised only after its handoff. */
	public static function poll():ImportRemovalStatus {
		#if sys
		mutex.acquire(); var result = pendingResult; pendingResult = null;
		var recovery = pendingRecovery; pendingRecovery = null; mutex.release();
		if (recovery != null) {
			recoveryRunning = false;
			if (recovery.length == 0) {
				try {
					ImportRefreshManager.finishRemovalReservation(token,removedRoots,true); token = ''; recoveryReady = true;
					value.busy = false; value.published = recoveryWasRetry && retryPublished;
					value.phase = recoveryWasRetry ? value.published ? 'complete' : 'cancelled' : 'idle';
					value.label = recoveryWasRetry ? 'Managed recovery and cleanup finished.' : '';
				} catch (error:Dynamic) {
					value.phase = 'conflict'; value.busy = false; value.label = Std.string(error);
				}
			} else {
				value.phase = retryPublished ? 'cleanup-pending' : 'conflict'; value.busy = false;
				value.label = 'Removal recovery needs attention. Imported content stays locked.\n' + recovery.join('\n');
			}
		}
		if (result != null) {
			var committed = result.status == 'applied' || result.status == 'cleanup-pending';
			workerCommitted = committed; removedRoots = result.affectedOwners.copy();
			try {
				// A conflict can include an unfinished rollback. Keep its reservation
				// until the worker recovery verifies restoration or committed cleanup.
				if (result.status != 'conflict') { ImportRefreshManager.finishRemovalReservation(token,result.affectedOwners,committed); token = ''; }
				value.phase = result.status == 'applied' ? 'complete' : result.status;
				value.busy = false; value.cancellable = false; value.published = committed;
				value.label = committed ? result.status == 'applied' ? 'Installed content removed. Saved history preserved.'
					: 'Installed content removed. Managed cleanup is pending.\n' + result.blockers.join('\n')
					: result.status == 'cancelled' ? 'Removal cancelled. Installed content restored.' : result.blockers.join('\n');
			} catch (error:Dynamic) {
				value.phase = 'conflict'; value.busy = false; value.published = false; value.label = 'Library publication needs recovery: ' + Std.string(error);
			}
		}
		mutex.acquire();
		var snapshot:ImportRemovalStatus = {phase:value.phase,busy:value.busy,label:value.label,plan:value.plan,published:value.published,cancellable:value.cancellable};
		mutex.release(); return snapshot;
		#else
		return {phase:'blocked',busy:false,label:'Native builds only.',plan:null,published:false,cancellable:false};
		#end
	}
}
