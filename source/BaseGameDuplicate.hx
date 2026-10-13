package;

typedef ChartFingerprint = {
	var title:String;
	/** Instrumental size in bytes, or -1 when it could not be read. */
	var audioBytes:Float;
	/** Instrumental length in seconds, or -1 when unknown. */
	var audioSeconds:Float;
	/** Chart tempo, or -1 until it has been read. */
	var bpm:Float;
	/** Player and opponent character ids from the chart, '' until read. */
	var player:String;
	var opponent:String;
}

/** Decides whether an imported chart is a copy of a base game song. A shared
 * title is never enough: the tempo must agree, and so must the instrumental
 * (and, unless that is byte-identical, the chart). A chart with its own cast
 * has its own graphics and is never a duplicate. */
class BaseGameDuplicate {
	public static inline var SECONDS_TOLERANCE:Float = 0.25;

	/** Letters and digits only, so "Dad Battle", "dad-battle" and "Dadbattle" agree. */
	public static function normalizeTitle(title:String):String {
		if (title == null) return '';
		var lower = title.toLowerCase(); var out = new StringBuf();
		for (i in 0...lower.length) {
			var c = lower.charCodeAt(i);
			if ((c >= 48 && c <= 57) || (c >= 97 && c <= 122) || c > 127) out.add(lower.charAt(i));
		}
		return out.toString();
	}

	/** Equal, or one a whole-word-free prefix of the other ("philly" and "philly nice"). */
	public static function sameTitle(left:String, right:String):Bool {
		var a = normalizeTitle(left); var b = normalizeTitle(right);
		if (a == '' || b == '') return false;
		if (a == b) return true;
		var short = a.length < b.length ? a : b; var long = a.length < b.length ? b : a;
		return short.length >= 4 && StringTools.startsWith(long, short);
	}

	static function sameAudioBytes(a:ChartFingerprint, b:ChartFingerprint):Bool
		return a.audioBytes > 0 && a.audioBytes == b.audioBytes;
	static function sameAudioLength(a:ChartFingerprint, b:ChartFingerprint):Bool
		return a.audioSeconds > 0 && b.audioSeconds > 0 && Math.abs(a.audioSeconds - b.audioSeconds) <= SECONDS_TOLERANCE;

	/** Cheap test that needs no chart read: worth comparing tempo and notes at all?
	 * A shared title is required, and is never sufficient. */
	public static function candidate(imported:ChartFingerprint, base:ChartFingerprint):Bool {
		if (imported == null || base == null || !sameTitle(imported.title, base.title)) return false;
		return sameAudioBytes(imported, base) || sameAudioLength(imported, base);
	}
	/** True when the instrumental is not byte-identical, so the charts must be compared too. */
	public static function needsNotes(imported:ChartFingerprint, base:ChartFingerprint):Bool
		return !sameAudioBytes(imported, base);

	/** Read the tempo and cast a comparison needs from chart text. */
	public static function readChart(text:String, into:ChartFingerprint):Void {
		into.bpm = FreeplayPulse.bpmFromChartText(text);
		var player = ~/"player1"\s*:\s*"([^"]*)"/; var opponent = ~/"player2"\s*:\s*"([^"]*)"/;
		into.player = text != null && player.match(text) ? player.matched(1) : '';
		into.opponent = text != null && opponent.match(text) ? opponent.matched(1) : '';
	}
	/** Both charts name the same player and opponent. Unknown never counts as equal. */
	public static function sameCast(a:ChartFingerprint, b:ChartFingerprint):Bool {
		var player = normalizeTitle(a.player); var opponent = normalizeTitle(a.opponent);
		return player != '' && opponent != '' && player == normalizeTitle(b.player) && opponent == normalizeTitle(b.opponent);
	}

	/** Full decision: same title, same tempo, same cast, and either a byte-identical
	 * instrumental or one of the same length under a chart with the same note
	 * count (within two percent). A remix that keeps a song's title, tempo and
	 * length still has its own audio and chart, so it is not a duplicate. */
	public static function matches(imported:ChartFingerprint, base:ChartFingerprint, importedNotes:Int = -1, baseNotes:Int = -1):Bool {
		if (!candidate(imported, base)) return false;
		if (!(imported.bpm > 0 && base.bpm > 0 && Math.abs(imported.bpm - base.bpm) < 0.01)) return false;
		if (!sameCast(imported, base)) return false;
		if (sameAudioBytes(imported, base)) return true;
		return importedNotes > 0 && baseNotes > 0
			&& Math.abs(importedNotes - baseNotes) <= Math.max(1, Math.ffloor(baseNotes * 0.02));
	}

	/** Length of an Ogg Vorbis stream from its identification header and the
	 * granule position of its final page. Returns -1 for anything else. */
	public static function oggSeconds(head:haxe.io.Bytes, tail:haxe.io.Bytes):Float {
		if (head == null || tail == null) return -1;
		var rate = -1; var at = 0;
		while (at + 16 <= head.length) {
			if (head.get(at) == 1 && head.getString(at + 1, 6) == 'vorbis') { rate = head.getInt32(at + 12); break; }
			at++;
		}
		if (rate <= 0) return -1;
		var page = tail.length - 14;
		while (page >= 0) {
			if (tail.get(page) == 0x4F && tail.get(page + 1) == 0x67 && tail.get(page + 2) == 0x67 && tail.get(page + 3) == 0x53) {
				var low:Float = tail.getInt32(page + 6); var high:Float = tail.getInt32(page + 10);
				if (low < 0) low += 4294967296.0;
				if (high < 0) return -1;
				return (high * 4294967296.0 + low) / rate;
			}
			page--;
		}
		return -1;
	}

	#if sys
	/** Size and length of an instrumental on disk. Reads at most 72 KiB. */
	public static function measureAudio(path:String, into:ChartFingerprint):Void {
		into.audioBytes = -1; into.audioSeconds = -1;
		try {
			if (path == null || !sys.FileSystem.exists(path) || sys.FileSystem.isDirectory(path)) return;
			var size = sys.FileSystem.stat(path).size;
			into.audioBytes = size;
			var input = sys.io.File.read(path, true);
			try {
				var head = input.read(Std.int(Math.min(8192, size)));
				var tailLength = Std.int(Math.min(65536, size));
				input.seek(size - tailLength, sys.io.FileSeek.SeekBegin);
				into.audioSeconds = oggSeconds(head, input.read(tailLength));
			} catch (_:Dynamic) {}
			input.close();
		} catch (_:Dynamic) {}
	}
	#end
}
