package;

/** Source-shaped Discord presence facade for Nightmare Vision scripts. */
class NightmareVisionDiscordClient {
	public var username(default, null):String = 'Unknown';
	var publish:(String, Null<String>, Null<String>, Bool, Null<Float>, String) -> Void;

	public function new(publish:(String, Null<String>, Null<String>, Bool, Null<Float>, String) -> Void) {
		this.publish = publish;
	}

	public function changePresence(details:String = 'In the Menus', ?state:String, ?smallImageKey:String,
			hasStartTimestamp:Bool = false, ?endTimestamp:Float, largeImageKey:String = 'icon'):Void {
		publish(details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey);
	}
}
