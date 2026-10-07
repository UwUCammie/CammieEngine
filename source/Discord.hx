package;

#if cpp
import discord_rpc.DiscordRpc;
import sys.thread.Deque;
import sys.thread.Lock;
import sys.thread.Mutex;
import sys.thread.Thread;
#end

typedef DiscordRpcCommand = {
	var kind:String;
	var value:Dynamic;
	@:optional var complete:Void->Void;
}

/** A detached view of the requested RPC state, safe to retain across owners. */
typedef DiscordPresenceSnapshot = {
	var presence:Dynamic;
	var hasPresence:Bool;
	var explicitlyCleared:Bool;
	var clientId:String;
	var presenceRevision:Int;
	var identityRevision:Int;
}

/**
	Serializes the RPC lifecycle and preserves the latest presence across an
	application identity change. The driver is injected so the transitions can
	be tested without starting the native Discord client.
*/
class DiscordRpcLifecycle {
	var clientId:String;
	var started:Bool = false;
	var currentPresence:Dynamic;
	var hasPresence:Bool = false;
	var explicitlyCleared:Bool = false;
	final startClient:String->Void;
	final processClient:Void->Void;
	final shutdownClient:Void->Void;
	final publishPresence:Dynamic->Void;
	final clearClientPresence:Void->Void;

	public function new(clientId:String, startClient:String->Void, processClient:Void->Void,
			shutdownClient:Void->Void, publishPresence:Dynamic->Void,
			?clearClientPresence:Void->Void) {
		this.clientId = clientId;
		this.startClient = startClient;
		this.processClient = processClient;
		this.shutdownClient = shutdownClient;
		this.publishPresence = publishPresence;
		this.clearClientPresence = clearClientPresence == null
			? function() publishPresence({}) : clearClientPresence;
	}

	public function getClientId():String return clientId;

	public function initialize(?requestedClientId:String):Void {
		if (requestedClientId != null) clientId = requestedClientId;
		if (started) return;
		startClient(clientId);
		started = true;
	}

	public function setClientId(value:String):Void {
		if (value == null || value == clientId) return;
		clientId = value;
		if (!started) return;

		shutdownClient();
		started = false;
		initialize();
		if (hasPresence) publishPresence(DiscordClient.clonePresence(currentPresence));
		else if (explicitlyCleared) clearClientPresence();
	}

	public function setPresence(value:Dynamic):Void {
		if (value == null) {
			clearPresence();
			return;
		}
		currentPresence = DiscordClient.clonePresence(value);
		hasPresence = true;
		explicitlyCleared = false;
		if (started) publishPresence(DiscordClient.clonePresence(currentPresence));
	}

	/** Seed a new daemon with the state requested before it was initialized. */
	public function seedRequestedState(snapshot:DiscordPresenceSnapshot):Void {
		clientId = snapshot.clientId;
		seedRequestedPresence(snapshot);
	}

	/** Seed presence without changing the daemon's applied identity. The ready
	 * callback can race with a queued identity command after startup. */
	public function seedRequestedPresence(snapshot:DiscordPresenceSnapshot):Void {
		hasPresence = snapshot.hasPresence;
		explicitlyCleared = snapshot.explicitlyCleared;
		currentPresence = snapshot.hasPresence ? DiscordClient.clonePresence(snapshot.presence) : null;
	}

	/** Explicit absence does not fall back to an invented menu status. */
	public function clearPresence():Void {
		currentPresence = null;
		hasPresence = false;
		explicitlyCleared = true;
		if (started) clearClientPresence();
	}

	/** Called from the SDK callback on the same daemon that processes RPC. */
	public function onReady(menuPresence:Dynamic):Void {
		if (hasPresence) publishPresence(DiscordClient.clonePresence(currentPresence));
		else if (explicitlyCleared) clearClientPresence();
		else setPresence(menuPresence);
	}

	public function process():Void {
		if (started) processClient();
	}

	public function dispatch(command:DiscordRpcCommand):Void {
		try {
			switch (command.kind) {
				case 'clientId': setClientId(cast command.value);
				case 'presence': setPresence(command.value);
				case 'clearPresence': clearPresence();
				case 'shutdown': shutdown();
				case 'initialize': initialize(cast command.value);
				case _: // Ignore unknown commands so a future producer cannot stop the daemon.
			}
		} catch (error:Dynamic) {
			if (command.complete != null) command.complete();
			throw error;
		}
		if (command.complete != null) command.complete();
	}

	public function shutdown():Void {
		if (!started) return;
		shutdownClient();
		started = false;
	}
}

class DiscordClient {
	public static inline var NATIVE_CLIENT_ID:String = "840632338949210114";
	static var requestedClientId:String = NATIVE_CLIENT_ID;
	static var requestedPresence:Dynamic;
	static var requestedHasPresence:Bool = false;
	static var requestedPresenceCleared:Bool = false;
	static var requestedPresenceRevision:Int = 0;
	static var requestedIdentityRevision:Int = 0;
	static var rpcSdkStarted:Bool = false;
	static final PRESENCE_FIELDS:Array<String> = [
		'state', 'details', 'startTimestamp', 'endTimestamp', 'largeImageKey', 'largeImageText',
		'smallImageKey', 'smallImageText', 'partyID', 'partySize', 'partyMax', 'matchSecret',
		'joinSecret', 'spectateSecret', 'instance'
	];
	#if cpp
	static var clientIdMutex:Mutex = new Mutex();
	static var rpcCommands:Deque<DiscordRpcCommand>;
	static var rpcWake:Lock;
	static var rpcDaemonRunning:Bool = false;
	static var rpcLifecycle:DiscordRpcLifecycle;
	#end

	/** Return the requested application identity, including before daemon startup. */
	public static function getClientId():String {
		#if cpp
		clientIdMutex.acquire();
		var result = requestedClientId;
		clientIdMutex.release();
		return result;
		#else
		return requestedClientId;
		#end
	}

	/** Change the shared RPC identity. A live SDK restart is queued on its daemon. */
	public static function setClientId(value:String):Void {
		setClientIdAndGetSnapshot(value);
	}

	/** Change the shared identity atomically and return its new revision. */
	public static function setClientIdAndGetSnapshot(value:String):DiscordPresenceSnapshot {
		if (value == null) return getRequestedSnapshot();
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		if (requestedClientId != value) {
			requestedClientId = value;
			requestedIdentityRevision++;
			if (rpcDaemonRunning) {
				rpcCommands.add({kind: 'clientId', value: value});
				wake = rpcWake;
			}
		}
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		if (wake != null) wake.release();
		return snapshot;
		#else
		if (requestedClientId != value) {
			requestedClientId = value;
			requestedIdentityRevision++;
		}
		return requestedSnapshotLocked();
		#end
	}

	/** Snapshot requested values without exposing the daemon's mutable objects. */
	public static function getRequestedSnapshot():DiscordPresenceSnapshot {
		#if cpp
		clientIdMutex.acquire();
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		return snapshot;
		#else
		return requestedSnapshotLocked();
		#end
	}

	/** Store a presence request even when the daemon has not started yet. */
	public static function publishPresenceAndGetSnapshot(presence:Dynamic):DiscordPresenceSnapshot {
		if (presence == null) return clearPresenceAndGetSnapshot();
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		requestedPresence = clonePresence(presence);
		requestedHasPresence = true;
		requestedPresenceCleared = false;
		requestedPresenceRevision++;
		if (rpcDaemonRunning) {
			var queuedPresence = clonePresence(requestedPresence);
			rpcCommands.add({kind: 'presence', value: queuedPresence});
			wake = rpcWake;
		}
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		if (wake != null) wake.release();
		return snapshot;
		#else
		requestedPresence = clonePresence(presence);
		requestedHasPresence = true;
		requestedPresenceCleared = false;
		requestedPresenceRevision++;
		return requestedSnapshotLocked();
		#end
	}

	/** Clear requested activity and keep reconnects from publishing menu defaults. */
	public static function clearPresenceAndGetSnapshot():DiscordPresenceSnapshot {
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		requestedPresence = null;
		requestedHasPresence = false;
		requestedPresenceCleared = true;
		requestedPresenceRevision++;
		if (rpcDaemonRunning) {
			rpcCommands.add({kind: 'clearPresence', value: null});
			wake = rpcWake;
		}
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		if (wake != null) wake.release();
		return snapshot;
		#else
		requestedPresence = null;
		requestedHasPresence = false;
		requestedPresenceCleared = true;
		requestedPresenceRevision++;
		return requestedSnapshotLocked();
		#end
	}

	/** Restore presence only while its revision is still owned by this lease. */
	public static function restorePresenceIfRevision(expectedRevision:Int,
			snapshot:DiscordPresenceSnapshot):Bool {
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		if (requestedPresenceRevision != expectedRevision) {
			clientIdMutex.release();
			return false;
		}
		applyPresenceSnapshotLocked(snapshot);
		requestedPresenceRevision++;
		if (rpcDaemonRunning) {
			if (requestedHasPresence)
				rpcCommands.add({kind: 'presence', value: clonePresence(requestedPresence)});
			else
				rpcCommands.add({kind: 'clearPresence', value: null});
			wake = rpcWake;
		}
		clientIdMutex.release();
		if (wake != null) wake.release();
		return true;
		#else
		if (requestedPresenceRevision != expectedRevision) return false;
		applyPresenceSnapshotLocked(snapshot);
		requestedPresenceRevision++;
		return true;
		#end
	}

	/** Restore identity only while its revision is still owned by this lease. */
	public static function restoreClientIdIfRevision(expectedRevision:Int, value:String):Bool {
		if (value == null) return false;
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		if (requestedIdentityRevision != expectedRevision) {
			clientIdMutex.release();
			return false;
		}
		if (requestedClientId != value) {
			requestedClientId = value;
			requestedIdentityRevision++;
			if (rpcDaemonRunning) {
				rpcCommands.add({kind: 'clientId', value: value});
				wake = rpcWake;
			}
		}
		clientIdMutex.release();
		if (wake != null) wake.release();
		return true;
		#else
		if (requestedIdentityRevision != expectedRevision) return false;
		if (requestedClientId != value) {
			requestedClientId = value;
			requestedIdentityRevision++;
		}
		return true;
		#end
	}

	public static function isInitialized():Bool {
		#if cpp
		clientIdMutex.acquire();
		var result = rpcSdkStarted;
		clientIdMutex.release();
		return result;
		#else
		return false;
		#end
	}

	public static function initialize():Void {
		#if cpp
		// Isolated native smoke runs never need to connect to an external client.
		if (RuntimeSmokeHarness.enabled()) return;

		clientIdMutex.acquire();
		if (!rpcDaemonRunning) {
			rpcDaemonRunning = true;
			rpcCommands = new Deque<DiscordRpcCommand>();
			rpcWake = new Lock();
			var startupSnapshot = requestedSnapshotLocked();
			var commands = rpcCommands;
			var wake = rpcWake;
			Thread.create(() -> runDaemon(startupSnapshot, commands, wake));
		} else {
			rpcCommands.add({kind: 'initialize', value: requestedClientId});
			var wake = rpcWake;
			clientIdMutex.release();
			wake.release();
			trace("Discord Client initialized");
			return;
		}
		clientIdMutex.release();
		#end
		trace("Discord Client initialized");
	}

	#if cpp
	static function runDaemon(startupSnapshot:DiscordPresenceSnapshot, commands:Deque<DiscordRpcCommand>, wake:Lock):Void {
		rpcLifecycle = new DiscordRpcLifecycle(startupSnapshot.clientId, startRpc, DiscordRpc.process, shutdownRpc,
			function(presence:Dynamic) DiscordRpc.presence(presence), clearRpcPresence);
		rpcLifecycle.seedRequestedState(startupSnapshot);
		rpcLifecycle.initialize();

		while (true) {
			var command = commands.pop(false);
			while (command != null) {
				rpcLifecycle.dispatch(command);
				command = commands.pop(false);
			}
			rpcLifecycle.process();
			wake.wait(2);
		}
	}

	static function startRpc(clientId:String):Void {
		trace("Discord Client starting...");
		DiscordRpc.start({
			clientID: clientId,
			onReady: onReady,
			onError: onError,
			onDisconnected: onDisconnected
		});
		clientIdMutex.acquire(); rpcSdkStarted = true; clientIdMutex.release();
		trace("Discord Client started.");
	}

	static function shutdownRpc():Void {
		DiscordRpc.shutdown();
		clientIdMutex.acquire(); rpcSdkStarted = false; clientIdMutex.release();
	}

	static function clearRpcPresence():Void {
		// The bundled Discord RPC SDK clears activity when sent a zeroed presence.
		DiscordRpc.presence({});
	}
	#end

	public static function shutdown():Void {
		#if cpp
		var completed = new Lock();
		clientIdMutex.acquire();
		if (rpcDaemonRunning) {
			rpcCommands.add({kind: 'shutdown', value: null, complete: function() completed.release()});
			var wake = rpcWake;
			clientIdMutex.release();
			wake.release();
			completed.wait(5);
		} else {
			clientIdMutex.release();
		}
		#end
	}

	static function menuPresence():Dynamic {
		return {
			details: "Cammie Engine | In the Menus",
			state: null,
			largeImageKey: 'icon',
			largeImageText: "Cammie Engine"
		};
	}

	static function onReady():Void {
		#if cpp
		var fallback = menuPresence();
		var snapshot = captureReadyPresence(fallback);
		if (rpcLifecycle != null) {
			rpcLifecycle.seedRequestedPresence(snapshot);
			rpcLifecycle.onReady(fallback);
		}
		#end
	}

	/** Capture a real SDK-ready fallback in the shared request state. An explicit
	 * source request or clear made before readiness always takes precedence. */
	@:noCompletion public static function captureReadyPresence(menuPresence:Dynamic):DiscordPresenceSnapshot {
		#if cpp
		clientIdMutex.acquire();
		if (!requestedHasPresence && !requestedPresenceCleared) {
			requestedPresence = clonePresence(menuPresence);
			requestedHasPresence = true;
			requestedPresenceRevision++;
		}
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		return snapshot;
		#else
		if (!requestedHasPresence && !requestedPresenceCleared) {
			requestedPresence = clonePresence(menuPresence);
			requestedHasPresence = true;
			requestedPresenceRevision++;
		}
		return requestedSnapshotLocked();
		#end
	}

	static function onError(_code:Int, _message:String):Void {
		trace('Error! $_code : $_message');
	}

	static function onDisconnected(_code:Int, _message:String):Void {
		trace('Disconnected! $_code : $_message');
	}

	static function enqueuePresence(request:Dynamic):DiscordPresenceSnapshot {
		#if cpp
		var wake:Lock = null;
		clientIdMutex.acquire();
		requestedPresence = clonePresence(request);
		requestedHasPresence = true;
		requestedPresenceCleared = false;
		requestedPresenceRevision++;
		if (rpcDaemonRunning) {
			var presence = clonePresence(requestedPresence);
			rpcCommands.add({kind: 'presence', value: presence});
			wake = rpcWake;
		}
		var snapshot = requestedSnapshotLocked();
		clientIdMutex.release();
		if (wake != null) wake.release();
		return snapshot;
		#else
		requestedPresence = clonePresence(request);
		requestedHasPresence = true;
		requestedPresenceCleared = false;
		requestedPresenceRevision++;
		return requestedSnapshotLocked();
		#end
	}

	static function requestedSnapshotLocked():DiscordPresenceSnapshot return {
		presence:requestedHasPresence ? clonePresence(requestedPresence) : null,
		hasPresence:requestedHasPresence, explicitlyCleared:requestedPresenceCleared,
		clientId:requestedClientId, presenceRevision:requestedPresenceRevision,
		identityRevision:requestedIdentityRevision
	};

	static function applyPresenceSnapshotLocked(snapshot:DiscordPresenceSnapshot):Void {
		requestedHasPresence = snapshot != null && snapshot.hasPresence;
		requestedPresence = requestedHasPresence ? clonePresence(snapshot.presence) : null;
		// Absence restored over a live source request must clear that stale request
		// and remain clear across reconnects instead of falling back to a fake menu.
		requestedPresenceCleared = !requestedHasPresence || snapshot.explicitlyCleared;
	}

	public static function clonePresence(value:Dynamic):Dynamic {
		if (value == null) return null;
		var copy:Dynamic = {};
		for (field in PRESENCE_FIELDS) if (Reflect.hasField(value, field)) {
			var item:Dynamic = Reflect.field(value, field);
			if (item == null || Std.isOfType(item, String) || Std.isOfType(item, Bool)
				|| Std.isOfType(item, Int) || Std.isOfType(item, Float))
				Reflect.setField(copy, field, item);
		}
		return copy;
	}

	public static function changePresence(details:String, state:Null<String>, ?smallImageKey:String, ?hasStartTimestamp:Bool, ?endTimestamp:Float,
			?smallImageString:String):Void {
		var startTimestamp:Float = if (hasStartTimestamp) Date.now().getTime() else 0;
		var finishTimestamp:Float = endTimestamp == null ? 0 : endTimestamp;
		if (finishTimestamp > 0) finishTimestamp = startTimestamp + finishTimestamp;
		if (smallImageKey == null) smallImageKey = "icon";
		if (smallImageString == null) smallImageString = "Cammie Engine";

		enqueuePresence({
			details: "Cammie Engine | " + details,
			state: state,
			largeImageKey: smallImageKey,
			largeImageText: smallImageString,
			// Obtained times are in milliseconds so they are divided so Discord can use it
			startTimestamp: Std.int(startTimestamp / 1000),
			endTimestamp: Std.int(finishTimestamp / 1000)
		});
	}

	/** Nightmare Vision supplies separate small and large image keys. */
	public static function changePresenceWithImages(details:String, state:Null<String>, smallImageKey:Null<String>,
			hasStartTimestamp:Bool, endTimestamp:Null<Float>, largeImageKey:String):Void {
		var startTimestamp:Float = hasStartTimestamp ? Date.now().getTime() : 0;
		var finishTimestamp:Float = endTimestamp == null ? 0 : endTimestamp;
		if (finishTimestamp > 0) finishTimestamp += startTimestamp;

		enqueuePresence({
			details: "Cammie Engine | " + details,
			state: state,
			smallImageKey: smallImageKey,
			largeImageKey: largeImageKey == null ? 'icon' : largeImageKey,
			largeImageText: 'Cammie Engine',
			startTimestamp: Std.int(startTimestamp / 1000),
			endTimestamp: Std.int(finishTimestamp / 1000)
		});
	}
}
