package;

import Discord.DiscordClient;
import Discord.DiscordPresenceSnapshot;

/** Injectable boundary for exercising presence ownership without an SDK. */
typedef SourceDiscordPresenceLeaseDriver = {
	var snapshot:Void->DiscordPresenceSnapshot;
	var setClientId:String->DiscordPresenceSnapshot;
	var publish:Dynamic->DiscordPresenceSnapshot;
	var clear:Void->DiscordPresenceSnapshot;
	var restorePresence:Int->DiscordPresenceSnapshot->Bool;
	var restoreClientId:Int->String->Bool;
}

/**
	One owner lease over the shared Discord daemon. Providers may share this
	instance; each provider's facade can be retired independently. Restore is a
	compare-and-set on both independently versioned parts of the snapshot so a
	later engine or owner write is never overwritten.
*/
@:keep
class SourceDiscordPresenceLease {
	final driver:SourceDiscordPresenceLeaseDriver;
	final initial:DiscordPresenceSnapshot;
	var lastPresenceRevision:Int;
	var lastIdentityRevision:Int;
	var ownsPresenceRevision:Bool = false;
	var ownsIdentityRevision:Bool = false;
	var released:Bool = false;

	public function new(?driver:SourceDiscordPresenceLeaseDriver) {
		this.driver = driver == null ? defaultDriver() : driver;
		initial = copySnapshot(this.driver.snapshot());
		lastPresenceRevision = initial.presenceRevision;
		lastIdentityRevision = initial.identityRevision;
	}

	/** Build the rich presence request a Psych-family DiscordClient.changePresence
		makes. Both donors do the same timestamp maths: the start is "now" when
		asked for, a positive end is a duration counted from that start, and both
		are sent as whole seconds. `now` is only passed by tests. */
	public static function sourcePresence(details:String, state:Null<String>, smallImageKey:Null<String>,
		hasStartTimestamp:Bool, endTimestamp:Null<Float>, largeImageKey:String, largeImageText:String,
		?now:Null<Float>):Dynamic {
		var startTimestamp:Float = !hasStartTimestamp ? 0 : (now == null ? Date.now().getTime() : now);
		var finishTimestamp:Float = endTimestamp == null ? 0 : endTimestamp;
		if (finishTimestamp > 0) finishTimestamp = startTimestamp + finishTimestamp;
		return {
			state:state,
			details:details,
			smallImageKey:smallImageKey,
			largeImageKey:largeImageKey,
			largeImageText:largeImageText,
			startTimestamp:Std.int(startTimestamp / 1000),
			endTimestamp:Std.int(finishTimestamp / 1000)
		};
	}

	public function publish(presence:Dynamic):Void {
		ensureActive();
		var current = presence == null ? driver.clear() : driver.publish(presence);
		lastPresenceRevision = current.presenceRevision;
		ownsPresenceRevision = lastPresenceRevision != initial.presenceRevision;
	}

	public function clear():Void {
		publish(null);
	}

	/** Re-submit the shared request without inventing a menu default. */
	public function republish():Void {
		ensureActive();
		var current = driver.snapshot();
		if (current.hasPresence) publish(current.presence) else clear();
	}

	public function getClientId():String {
		ensureActive();
		return driver.snapshot().clientId;
	}

	public function setClientId(value:String):Void {
		ensureActive();
		if (value == null) return;
		var before = driver.snapshot();
		var current = driver.setClientId(value);
		// A no-op assignment must not adopt a revision written by another owner.
		if (before.clientId != value && current.identityRevision != before.identityRevision) {
			lastIdentityRevision = current.identityRevision;
			ownsIdentityRevision = true;
		}
	}

	/** Restore only state whose revision still belongs to this lease. */
	public function release():Void {
		if (released) return;
		released = true;
		if (ownsPresenceRevision)
			driver.restorePresence(lastPresenceRevision, copySnapshot(initial));
		if (ownsIdentityRevision)
			driver.restoreClientId(lastIdentityRevision, initial.clientId);
	}

	public function isReleased():Bool return released;

	function ensureActive():Void {
		if (released) throw '[source-discord] Presence lease has been released';
	}

	static function copySnapshot(snapshot:DiscordPresenceSnapshot):DiscordPresenceSnapshot {
		return {
			presence:snapshot.hasPresence ? DiscordClient.clonePresence(snapshot.presence) : null,
			hasPresence:snapshot.hasPresence,
			explicitlyCleared:snapshot.explicitlyCleared,
			clientId:snapshot.clientId,
			presenceRevision:snapshot.presenceRevision,
			identityRevision:snapshot.identityRevision
		};
	}

	static function defaultDriver():SourceDiscordPresenceLeaseDriver return {
		snapshot:DiscordClient.getRequestedSnapshot,
		setClientId:DiscordClient.setClientIdAndGetSnapshot,
		publish:DiscordClient.publishPresenceAndGetSnapshot,
		clear:DiscordClient.clearPresenceAndGetSnapshot,
		restorePresence:DiscordClient.restorePresenceIfRevision,
		restoreClientId:DiscordClient.restoreClientIdIfRevision
	};
}
