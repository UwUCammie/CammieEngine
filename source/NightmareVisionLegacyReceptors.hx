package;

/** Captured source pointers, independent of mutable field IDs and collection order. */
class NightmareVisionLegacyReceptors {
	public var player:NightmareVisionPlayFieldView;
	public var opponent:NightmareVisionPlayFieldView;
	public function new() {}
	public function capture(lane:Int, field:NightmareVisionPlayFieldView):Void {
		if (lane == 0) player = field;
		else if (lane == 1) opponent = field;
	}
	public static function hasProperty(name:String):Bool {
		return name == 'playerStrums' || name == 'opponentStrums' || name == 'strumLineNotes';
	}
	public function readProperty(name:String, fields:Array<NightmareVisionPlayFieldView>):Dynamic {
		if (name == 'playerStrums') return player;
		if (name == 'opponentStrums') return opponent;
		var notes:Array<Dynamic> = [];
		if (fields != null) for (field in fields) for (note in field.members) notes.push(note);
		return notes;
	}
	public function writeProperty(name:String, value:Dynamic):Dynamic {
		return switch (name) {
			case 'playerStrums': player = cast value;
			case 'opponentStrums': opponent = cast value;
			default: throw '[nightmare-vision-script] Read-only source property: ' + name;
		};
	}
	public function release():Void {player = null; opponent = null;}
}
