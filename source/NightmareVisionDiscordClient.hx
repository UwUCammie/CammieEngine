package;

/** Source-shaped Discord presence facade for Nightmare Vision scripts. Real
	owners get one built over the shared presence lease, the same one the Psych
	facade writes through, so whatever a script changes is put back when the
	owner leaves. */
class NightmareVisionDiscordClient {
	public var username(default, null):String = 'Unknown';
	public var NMV_ID(default, null):String = '1252033037680513115';
	public var rpcId(get, set):String;
	static inline var ENGINE_NAME:String = 'Cammie Engine';
	static inline var ENGINE_PREFIX:String = 'Cammie Engine | ';
	var publish:(String, Null<String>, Null<String>, Bool, Null<Float>, String) -> Void;
	var readClientId:Void->String;
	var writeClientId:String->Void;
	static var ownerLease:SourceDiscordPresenceLease;
	static var ownerLeaseRoot:String = '';
	// Goes up every time the current owner is retired. A facade remembers the
	// value it was made under, so one that outlives its owner can't quietly
	// take a fresh lease nobody would hand back.
	static var ownerEpoch:Int = 0;

	/** Facade for scripts of one imported owner. Every facade of that owner
		shares one lease, taken the first time it is needed; another owner asking
		retires the previous one. A facade whose owner was replaced or released
		stops working. */
	public static function forOwner(root:String, ?ownerActive:Void->Bool):NightmareVisionDiscordClient {
		var key = ownerKey(root);
		if (key == '') throw '[nmv-discord] Missing owner root';
		if (ownerLeaseRoot != key) {
			releaseOwner();
			ownerLeaseRoot = key;
		}
		var epoch = ownerEpoch;
		function lease():SourceDiscordPresenceLease {
			if (epoch != ownerEpoch || (ownerActive != null && !ownerActive()))
				throw '[nmv-discord] Released imported owner';
			if (ownerLease == null) ownerLease = new SourceDiscordPresenceLease();
			return ownerLease;
		}
		return new NightmareVisionDiscordClient(function(details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey)
			publishThrough(lease(), details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey),
			function() return lease().getClientId(),
			function(value:String) lease().setClientId(value));
	}

	/** Give the engine its presence and client id back, unless something else
		wrote them after this owner did. `keepRoot` leaves that owner alone. */
	public static function releaseOwner(?keepRoot:String):Void {
		if (ownerLeaseRoot == '' || (ownerKey(keepRoot) != '' && ownerKey(keepRoot) == ownerLeaseRoot)) return;
		var lease = ownerLease;
		ownerLease = null;
		ownerLeaseRoot = '';
		ownerEpoch++;
		if (lease != null) lease.release();
	}

	static function ownerKey(root:String):String {
		if (root == null) return '';
		var key = StringTools.replace(root, '\\', '/');
		while (StringTools.endsWith(key, '/')) key = key.substr(0, key.length - 1);
		return key;
	}

	static function publishThrough(lease:SourceDiscordPresenceLease, details:String, state:Null<String>,
		smallImageKey:Null<String>, hasStartTimestamp:Bool, endTimestamp:Null<Float>, largeImageKey:String):Void {
		lease.publish(SourceDiscordPresenceLease.sourcePresence(ENGINE_PREFIX + details, state, smallImageKey,
			hasStartTimestamp, endTimestamp, largeImageKey == null ? 'icon' : largeImageKey, ENGINE_NAME));
	}

	/** Facade over an existing lease. It stops working once the lease is
		released or `ownerActive` says the owner is gone. */
	public static function leased(lease:SourceDiscordPresenceLease, ?ownerActive:Void->Bool):NightmareVisionDiscordClient {
		if (lease == null) throw '[nmv-discord] A shared presence lease is required';
		function ensureActive():Void {
			if (lease.isReleased() || (ownerActive != null && !ownerActive()))
				throw '[nmv-discord] Released imported owner';
		}
		return new NightmareVisionDiscordClient(function(details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey) {
			ensureActive();
			publishThrough(lease, details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey);
		}, function() {
			ensureActive();
			return lease.getClientId();
		}, function(value:String) {
			ensureActive();
			lease.setClientId(value);
		});
	}

	public function new(publish:(String, Null<String>, Null<String>, Bool, Null<Float>, String) -> Void,
			?getClientId:Void->String, ?setClientId:String->Void) {
		this.publish = publish;
		var localRpcId = NMV_ID;
		this.readClientId = getClientId == null ? function() return localRpcId : getClientId;
		this.writeClientId = setClientId == null ? function(value:String) localRpcId = value : setClientId;
	}

	function get_rpcId():String return readClientId();

	function set_rpcId(value:String):String {
		if (value != null) writeClientId(value);
		return readClientId();
	}

	public function changePresence(details:String = 'In the Menus', ?state:String, ?smallImageKey:String,
			hasStartTimestamp:Bool = false, ?endTimestamp:Float, largeImageKey:String = 'icon'):Void {
		publish(details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey);
	}
}
