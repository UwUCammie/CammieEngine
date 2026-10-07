package;

import Discord.DiscordClient;

/** Psych Engine 1.0.4's owner-scoped view of the shared Discord daemon. */
@:keep
class PsychDiscordClient {
	public static inline var DEFAULT_CLIENT_ID:String = '863222024192262205';
	public static inline var PSYCH_ENGINE_VERSION:String = '1.0.4';
	public var username(default, null):String = 'Unknown';
	public var clientID(get, set):String;
	public var isInitialized(get, never):Bool;
	final lease:SourceDiscordPresenceLease;
	final ownerActive:Void->Bool;
	var released:Bool = false;

	public function new(lease:SourceDiscordPresenceLease, ?ownerActive:Void->Bool) {
		if (lease == null) throw '[psych-discord] A shared presence lease is required';
		this.lease = lease;
		this.ownerActive = ownerActive == null ? function() return true : ownerActive;
	}

	function get_clientID():String {
		ensureActive();
		return lease.getClientId();
	}

	function set_clientID(value:String):String {
		ensureActive();
		if (value != null) lease.setClientId(value);
		return lease.getClientId();
	}

	function get_isInitialized():Bool {
		ensureActive();
		return DiscordClient.isInitialized();
	}

	/** Matches the pinned donor's optional/default argument signature and field
	 * mapping. Psych's `smallImageKey` stays small; its final key is large. */
	public function changePresence(details:String = 'In the Menus', ?state:String,
		?smallImageKey:String, ?hasStartTimestamp:Bool, ?endTimestamp:Float,
		largeImageKey:String = 'icon'):Void {
		ensureActive();
		var startTimestamp:Float = if (hasStartTimestamp) Date.now().getTime() else 0;
		var finishTimestamp:Float = endTimestamp == null ? 0 : endTimestamp;
		if (finishTimestamp > 0) finishTimestamp = startTimestamp + finishTimestamp;
		lease.publish({
			state:state,
			details:details,
			smallImageKey:smallImageKey,
			largeImageKey:largeImageKey,
			largeImageText:'Engine Version: ' + PSYCH_ENGINE_VERSION,
			startTimestamp:Std.int(startTimestamp / 1000),
			endTimestamp:Std.int(finishTimestamp / 1000)
		});
	}

	public function changeDiscordClientID(?newID:String):Void {
		ensureActive();
		lease.setClientId(newID == null ? DEFAULT_CLIENT_ID : newID);
	}

	public function resetClientID():Void {
		changeDiscordClientID();
	}

	public function updatePresence():Void {
		ensureActive();
		lease.republish();
	}

	/** A provider owns only its guard facade; the session manager owns the shared
	 * lease and releases it once the imported owner departs. */
	public function release():Void {
		released = true;
	}

	public function isReleased():Bool return released;

	public function ensureActive():Void {
		if (released || !ownerActive())
			throw '[psych-discord] Released imported owner';
	}
}
