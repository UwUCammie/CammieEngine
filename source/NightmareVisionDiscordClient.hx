package;

/** Source-shaped Discord presence facade for Nightmare Vision scripts. */
class NightmareVisionDiscordClient {
	public var username(default, null):String = 'Unknown';
	public var NMV_ID(default, null):String = '1252033037680513115';
	public var rpcId(get, set):String;
	var publish:(String, Null<String>, Null<String>, Bool, Null<Float>, String) -> Void;
	var readClientId:Void->String;
	var writeClientId:String->Void;

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
