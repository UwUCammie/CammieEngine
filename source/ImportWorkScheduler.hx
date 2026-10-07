package;

#if sys
import sys.thread.Mutex;
import sys.thread.Thread;
#end

/** Cooperative gate shared by background import workers and live gameplay.
 *
 * Gameplay leases are counted because Flixel can briefly have both the old and
 * new PlayState alive during a state transition. Import workers call
 * cooperate() only at bounded filesystem/conversion checkpoints. They wait
 * there while any gameplay lease is active, then resume the same operation.
 */
class ImportWorkScheduler {
	#if sys
	static var gate:Mutex = new Mutex();
	static var activeGameplayLeases:Map<Int, Bool> = new Map();
	static var nextLeaseId:Int = 1;
	static var foregroundThread:Thread = null;
	static var publicationToken:Int = 0;
	static var publicationOwner:Thread = null;
	static var nextPublicationToken:Int = 1;
	static var pausedSince:Float = -1;
	static var pausedDuration:Float = 0;
	#end

	/** Capture the Flixel thread before starting background import work.
	 * Repeated calls do not replace the original thread identity.
	 */
	public static function bindForegroundThread():Void {
		#if sys
		gate.acquire();
		if (foregroundThread == null) foregroundThread = Thread.current();
		syncPauseClockLocked(haxe.Timer.stamp());
		gate.release();
		#end
	}

	/** Begin one gameplay interval and return its idempotent release token. */
	public static function beginGameplay():Int {
		#if sys
		gate.acquire();
		var token = nextLeaseId++;
		if (nextLeaseId <= 0) nextLeaseId = 1;
		while (activeGameplayLeases.exists(token)) {
			token = nextLeaseId++;
			if (nextLeaseId <= 0) nextLeaseId = 1;
		}
		activeGameplayLeases.set(token, true);
		syncPauseClockLocked(haxe.Timer.stamp());
		gate.release();
		return token;
		#else
		return 0;
		#end
	}

	/** Release a gameplay interval. Repeated or unknown tokens are harmless. */
	public static function endGameplay(token:Int):Void {
		#if sys
		if (token <= 0) return;
		gate.acquire();
		activeGameplayLeases.remove(token);
		syncPauseClockLocked(haxe.Timer.stamp());
		gate.release();
		#end
	}

	/** Whether one or more gameplay intervals currently own the foreground. */
	public static function gameplayActive():Bool {
		#if sys
		gate.acquire();
		var active = activeGameplayLeases.iterator().hasNext();
		gate.release();
		return active;
		#else
		return false;
		#end
	}

	/** Enter the journaled publication window only after gameplay is idle.
	 * Once acquired, gameplay may start but import checkpoints do not pause until
	 * endUninterruptedPublication() commits or rolls back the transaction.
	 * Returns zero if called from the foreground thread or before it is bound,
	 * and -1 if the caller is cancelled while waiting.
	 */
	public static function beginUninterruptedPublication(?cancelled:Void->Bool):Int {
		#if sys
		while (true) {
			if (cancelled != null && cancelled()) return -1;
			gate.acquire();
			var current = Thread.current();
			if (foregroundThread == null || current == foregroundThread) {
				gate.release();
				return 0;
			}
			var gameplayActive = activeGameplayLeases.iterator().hasNext();
			if (!gameplayActive && publicationToken == 0) {
				var token = nextPublicationToken++;
				if (nextPublicationToken <= 0) nextPublicationToken = 1;
				while (token <= 0 || token == publicationToken) {
					token = nextPublicationToken++;
					if (nextPublicationToken <= 0) nextPublicationToken = 1;
				}
				publicationToken = token;
				publicationOwner = current;
				syncPauseClockLocked(haxe.Timer.stamp());
				gate.release();
				return token;
			}
			gate.release();
			Sys.sleep(0.025);
		}
		return 0;
		#else
		return 0;
		#end
	}

	/** End a previously acquired uninterrupted publication window. */
	public static function endUninterruptedPublication(token:Int):Void {
		#if sys
		if (token <= 0) return;
		gate.acquire();
		if (publicationToken == token) {
			publicationToken = 0;
			publicationOwner = null;
			syncPauseClockLocked(haxe.Timer.stamp());
		}
		gate.release();
		#end
	}

	/** Wait at a safe work boundary until gameplay releases the foreground.
	 * The timed poll avoids coupling the scheduler to a particular thread event
	 * API and bounds import resume latency after the last lease is released.
	 */
	public static function cooperate(?cancelled:Void->Bool):Bool {
		#if sys
		gate.acquire();
		var current = Thread.current();
		var isForeground = foregroundThread == null || current == foregroundThread;
		gate.release();
		if (isForeground) return true;
		while (true) {
			gate.acquire();
			var shouldWait = activeGameplayLeases.iterator().hasNext()
				&& (publicationToken == 0 || !(publicationOwner == current));
			gate.release();
			if (!shouldWait) return true;
			if (cancelled != null && cancelled()) return false;
			Sys.sleep(0.025);
		}
		return true;
		#else
		return cancelled == null || !cancelled();
		#end
	}

	/** Monotonic time excluding intervals when all import work is paused. */
	public static function workStamp():Float {
		#if sys
		var now = haxe.Timer.stamp();
		gate.acquire();
		syncPauseClockLocked(now);
		var excluded = pausedDuration;
		if (pausedSince >= 0) excluded += now - pausedSince;
		gate.release();
		return now - excluded;
		#else
		return haxe.Timer.stamp();
		#end
	}

	/** Whether this caller would currently wait at a cooperative checkpoint. */
	public static function backgroundWorkPaused():Bool {
		#if sys
		gate.acquire();
		var current = Thread.current();
		var paused = foregroundThread != null && !(current == foregroundThread)
			&& activeGameplayLeases.iterator().hasNext()
			&& (publicationToken == 0 || !(publicationOwner == current));
		gate.release();
		return paused;
		#else
		return false;
		#end
	}

	#if sys
	static function syncPauseClockLocked(now:Float):Void {
		var shouldPause = foregroundThread != null
			&& activeGameplayLeases.iterator().hasNext()
			&& publicationToken == 0;
		if (shouldPause && pausedSince < 0) pausedSince = now;
		else if (!shouldPause && pausedSince >= 0) {
			pausedDuration += now - pausedSince;
			pausedSince = -1;
		}
	}
	#end
}
