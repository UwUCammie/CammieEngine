package;

/** Psych's source character-role aliases, shared by its derivative adapters. */
class PsychCharacterChangeEvent {
	public static function role(value:String):Int {
		switch (value) {
			case 'gf', 'girlfriend': return 2;
			case 'dad', 'opponent': return 1;
			default:
				var parsed = value == null ? null : Std.parseInt(value);
				return parsed == null ? 0 : parsed;
		}
	}
}
