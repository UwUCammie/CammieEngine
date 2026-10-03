package;

/** Owner-scoped `funkin.data.Chart` used by Nightmare Vision scripts. */
class NightmareVisionChartApi {
	final loadText:String->String;
	final songPath:(String, Int)->String;

	public function new(loadText:String->String, songPath:(String, Int)->String) {
		this.loadText = loadText;
		this.songPath = songPath;
	}

	public function fromPath(path:String):Dynamic {
		var content = loadText(path);
		if (content == null) throw 'couldnt find chart at (' + path + ')';
		return fromData(haxe.Json.parse(content));
	}

	public function fromSong(songName:String, difficulty:Int = -1):Dynamic
		return fromPath(songPath(songName, difficulty));

	public function fromData(data:Dynamic):Dynamic {
		if (data == null) throw 'data provided was null';
		var format = checkFormat(data);
		if (format != 'unknown') throw 'this is using a incompatible format\n(' + format + ')';
		if (!Reflect.hasField(data, 'song')) throw 'data provided is invalid';
		var song:Dynamic = Reflect.field(data, 'song');
		correctFormat(song);
		return song;
	}

	public function checkFormat(data:Dynamic):String {
		if (data == null) return 'unknown';
		var format:Dynamic = Reflect.field(data, 'format');
		if (format != null && Std.string(format).indexOf('psych_v1') >= 0) return 'Psych_1.0';
		if (Reflect.hasField(data, 'version') && Reflect.hasField(data, 'scrollSpeed')) return 'V-Slice';
		if (Reflect.hasField(data, 'codenameChart')) return 'Codename Engine';
		return 'unknown';
	}

	function correctFormat(song:Dynamic):Void {
		if (Reflect.field(song, 'gfVersion') == null) {
			Reflect.setField(song, 'gfVersion', Reflect.field(song, 'player3'));
			if (Reflect.hasField(song, 'player3')) Reflect.deleteField(song, 'player3');
		}
		if (Reflect.field(song, 'keys') == null) Reflect.setField(song, 'keys', 4);
		if (Reflect.field(song, 'lanes') == null) Reflect.setField(song, 'lanes', 2);
		var keys:Int = Std.int(Reflect.field(song, 'keys'));
		var lanes:Int = Std.int(Reflect.field(song, 'lanes'));
		var skins:Array<Dynamic> = cast Reflect.field(song, 'arrowSkins');
		if (skins == null || skins.length == 0) {
			skins = [];
			for (_ in 0...lanes) skins.push('default');
			Reflect.setField(song, 'arrowSkins', skins);
		}
		var sections:Array<Dynamic> = cast Reflect.field(song, 'notes');
		if (Reflect.field(song, 'events') == null) {
			var events:Array<Dynamic> = [];
			if (sections != null) for (section in sections) {
				var rows:Array<Dynamic> = cast Reflect.field(section, 'sectionNotes');
				if (rows == null) continue;
				var i = 0;
				while (i < rows.length) {
					var row:Array<Dynamic> = cast rows[i];
					if (row != null && row.length > 1 && (row[1]:Float) < 0) {
						events.push([row[0], [[row.length > 2 ? row[2] : null,
							row.length > 3 ? row[3] : null, row.length > 4 ? row[4] : null]]]);
						rows.splice(i, 1);
					} else i++;
				}
			}
			Reflect.setField(song, 'events', events);
		}
		if (sections == null) {
			Reflect.setField(song, 'notes', []);
			return;
		}
		if (Reflect.field(song, 'format') != 'psych_v1' && Reflect.field(song, 'format') != 'nmv2') {
			Reflect.setField(song, 'format', 'nmv2');
			for (section in sections) {
				var rows:Array<Dynamic> = cast Reflect.field(section, 'sectionNotes');
				if (rows == null) continue;
				for (row in rows) if (row != null && row.length > 1) {
					var lane:Int = Std.int(row[1]);
					if (lane >= 0 && lane < keys * 2 && Reflect.field(section, 'mustHitSection') != true)
						row[1] = (lane + keys) % (keys * 2);
				}
			}
		}
		for (section in sections) {
			var beats:Dynamic = Reflect.field(section, 'sectionBeats');
			if (beats == null || Math.isNaN(Std.parseFloat(Std.string(beats)))) {
				Reflect.setField(section, 'sectionBeats', 4);
				if (Reflect.hasField(section, 'lengthInSteps')) Reflect.deleteField(section, 'lengthInSteps');
			}
		}
	}
}
