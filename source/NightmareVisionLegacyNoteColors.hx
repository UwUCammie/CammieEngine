package;

/** Historical NV note state; shares quant classification and the native HSV shader. */
class NightmareVisionLegacyNoteColors {
	public var prefs:Dynamic;
	public var swap:NightmareVisionLegacyColorSwap = new NightmareVisionLegacyColorSwap();
	var assignedType:Null<String>;
	var defaultSplashTexture:String;
	public function new(prefs:Dynamic, splashTexture:String = 'noteSplashes') {
		this.prefs = prefs;
		defaultSplashTexture = splashTexture;
	}

	public static function quantMode(prefs:Dynamic):Bool
		return prefs != null && (prefs.noteSkin == 'Quants' || prefs.noteSkin == 'QuantStep');

	public static function selectTexture(texture:String, prefs:Dynamic, canQuant:Bool, available:String->Bool):String {
		var candidate = 'QUANT' + texture;
		return canQuant && quantMode(prefs) && available(candidate) ? candidate : texture;
	}

	public static function setHSV(swap:NightmareVisionLegacyColorSwap, row:Array<Dynamic>):Void {
		if (row == null || row.length < 3) throw '[nightmare-vision-hsv] Expected three HSV values';
		swap.hue = row[0] / 360;
		swap.saturation = row[1] / 100;
		swap.brightness = row[2] / 100;
	}

	public static function laneHSV(prefs:Dynamic, lane:Int):Array<Dynamic>
		return prefs.arrowHSV[((lane % 4) + 4) % 4];

	/** 0: no assignment; 1: changed type and script; 2: colors/built-in assignment, no custom script. */
	public function prepare(note:Note, force:Bool):Int {
		var type = note.noteType;
		var changed = assignedType != type;
		if (!changed && !force) return 0;
		assignedType = type;
		note.noteSplashTexture = defaultSplashTexture;
		var row = laneHSV(prefs, note.noteData);
		if (note.isQuant && quantMode(prefs)) {
			var index = NightmareVisionQuantColorCompat.quantIndex(note.quant);
			var table:Dynamic = prefs.noteSkin == 'Quants' ? prefs.quantHSV : prefs.quantStepmania;
			row = table[index];
			if (note.noteSplashTexture == null || note.noteSplashTexture == '' || note.noteSplashTexture == 'noteSplashes')
				note.noteSplashTexture = 'QUANTnoteSplashes';
		}
		setHSV(swap, row);
		// Source clears the old attachment before built-in reloads or custom setup.
		note.noteScript = null;
		if (note.noteData > -1 && changed && type == 'Hurt Note') {
			note.reloadNote('HURT');
			note.noteSplashTexture = 'HURTnoteSplashes';
			setHSV(swap, [0, 0, 0]);
		}
		return note.noteData < 0 || !changed || isBuiltin(type) ? 2 : 1;
	}

	static function isBuiltin(type:String):Bool return switch (type) {
		case 'Hurt Note', 'No Animation', 'GF Sing', 'Ghost Note', 'Normal Slam',
			'Half Slam Lane 1', 'Half Slam Lane 2', 'Half Slam Lane 3', 'Half Slam Lane 4': true;
		default: false;
	};

	public function finish(note:Note):Void {
		note.noteSplashHue = swap.hue;
		note.noteSplashSat = swap.saturation;
		note.noteSplashBrt = swap.brightness;
	}
}
