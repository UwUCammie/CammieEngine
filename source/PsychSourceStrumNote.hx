package;

import Strumline.StrumNote;

/**
	Psych scripts build extra receptors with `new StrumNote(x, y, leData, player)`.
	The host receptor takes `(x, y, noteId, uiType)`, so those arguments put an Int
	where a UI name belongs and a lane past the key count, and the game crashed
	natively. This keeps Psych's meaning: the receptor uses the song's UI, gets
	the lane it asked for and is skinned like the song's own Psych receptors.
**/
@:access(PlayState)
class PsychSourceStrumNote {
	public static function create(host:PlayState, args:Array<Dynamic>):StrumNote {
		var x = number(args, 0);
		var y = number(args, 1);
		var lane = args != null && args.length > 2 && args[2] != null ? Std.int(number(args, 2)) : 0;
		if (lane < 0) lane = 0;
		var fourth:Dynamic = args != null && args.length > 3 ? args[3] : null;
		var type = uiType(Std.isOfType(fourth, String) ? fourth : null);
		var keys = Note.NOTE_AMOUNT > 0 ? Note.NOTE_AMOUNT : 4;
		// Built on a lane the UI pack has, then given the lane Psych asked for:
		// a fifth receptor (leData 4) is how scripts add an extra key.
		var strum = new StrumNote(x, y, lane % keys, type);
		strum.ID = lane;
		var owner = host == null ? null : host.selectedPsychSkinRoot();
		if (owner != null && PlayState.SONG != null)
			strum.configurePsychSkin(owner, PlayState.SONG.arrowSkin, PlayState.SONG.disableNoteRGB == true, host.pixelUI);
		return strum;
	}

	static function uiType(requested:String):String {
		var ui:Dynamic = Judgement.uiJson;
		if (requested != null && ui != null && Reflect.hasField(ui, requested)) return requested;
		var song = PlayState.SONG == null ? null : PlayState.SONG.uiType;
		if (song != null && ui != null && Reflect.hasField(ui, song)) return song;
		return 'normal';
	}

	static function number(args:Array<Dynamic>, index:Int):Float {
		if (args == null || args.length <= index || args[index] == null) return 0;
		var value:Dynamic = args[index];
		if (Std.isOfType(value, Float) || Std.isOfType(value, Int)) return value;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : parsed;
	}
}
