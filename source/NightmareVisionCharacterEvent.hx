package;

/** NV retains the older event-push role aliases separately from trigger aliases. */
class NightmareVisionCharacterEvent {
	public static function preloadRole(value:String, strict:Bool = false):Int {
		var normalized = strict ? value.toLowerCase() : value == null ? '' : value.toLowerCase();
		return switch (normalized) {
			case 'gf', 'girlfriend', '1': 2;
			case 'dad', 'opponent', '0': 1;
			default: PsychCharacterChangeEvent.role(normalized);
		};
	}
}
