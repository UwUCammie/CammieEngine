package;

using StringTools;

/** Owner-captured inputs for the small Language service surface used by Psych. */
typedef PsychLanguageHost = {
	var ownerActive:Void->Bool;
	/** Lines from authenticated language files already merged in source order. */
	var mergedLines:String->Array<String>;
	/** Captured Psych alphabet context, including its owner-scoped data. */
	var loadAlphabetData:String->Void;
	var report:String->Void;
}

/** Psych 1.0.4 Language semantics isolated to one authenticated import owner. */
@:keep
class PsychLanguageRuntime {
	public var ownerRoot(default, null):String;
	public var defaultLangName(get, set):String;
	/** The donor field is private; it remains reachable through source reflection. */
	public var phrases(get, set):Map<String, String>;

	var ownerPrefs:Dynamic;
	var host:PsychLanguageHost;
	var ownerPhrases:Map<String, String> = new Map();
	var languageName:String = 'English (US)';
	var released:Bool = false;

	public function new(ownerRoot:String, prefs:Dynamic, host:PsychLanguageHost) {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '')
			throw '[psych-language] A captured source owner is required';
		if (prefs == null || Reflect.field(prefs, 'data') == null
			|| Reflect.field(prefs, 'defaultData') == null)
			throw '[psych-language] Owner-local ClientPrefs data is unavailable';
		if (host == null || host.ownerActive == null || host.mergedLines == null
			|| host.loadAlphabetData == null || host.report == null)
			throw '[psych-language] A complete owner language host is required';
		this.ownerRoot = ownerRoot;
		this.ownerPrefs = prefs;
		this.host = host;
	}

	function get_defaultLangName():String {
		ensureActive();
		return languageName;
	}

	function set_defaultLangName(value:String):String {
		ensureActive();
		languageName = value;
		return value;
	}

	function get_phrases():Map<String, String> {
		ensureActive();
		return ownerPhrases;
	}

	function set_phrases(value:Map<String, String>):Map<String, String> {
		ensureActive();
		ownerPhrases = value;
		return value;
	}

	/** Reload this owner's selected language and perform the donor alphabet side effect. */
	public function reloadPhrases():Void {
		ensureActive();
		var language = preferenceString(ownerPrefs, 'data', 'language');
		var loadedText:Array<String> = null;
		try loadedText = host.mergedLines(language) catch (error:Dynamic) {
			reportFailure('merged language sources', error);
			throw error;
		}
		ensureActive();
		if (loadedText == null)
			throw '[psych-language] The captured language source returned no merged lines';

		ownerPhrases.clear();
		var hasPhrases:Bool = false;
		for (num in 0...loadedText.length) {
			var phrase = loadedText[num];
			phrase = phrase.trim();
			if (num < 1 && !phrase.contains(':')) {
				ownerPhrases.set('language_name', phrase.trim());
				continue;
			}

			if (phrase.length < 4 || phrase.startsWith('//')) continue;
			var n:Int = phrase.indexOf(':');
			if (n < 0) continue;

			var key:String = phrase.substr(0, n).trim().toLowerCase();
			var value:String = phrase.substr(n);
			n = value.indexOf('"');
			if (n < 0) continue;

			ownerPhrases.set(key, value.substring(n + 1, value.lastIndexOf('"')).replace('\\n', '\n'));
			hasPhrases = true;
		}

		if (!hasPhrases)
			Reflect.setField(Reflect.field(ownerPrefs, 'data'), 'language', preferenceString(ownerPrefs, 'defaultData', 'language'));

		var alphaPath:String = getFileTranslation('images/alphabet');
		if (alphaPath.startsWith('images/')) alphaPath = alphaPath.substr('images/'.length);
		var pngPos:Int = alphaPath.indexOf('.png');
		if (pngPos > -1) alphaPath = alphaPath.substring(0, pngPos);
		ensureActive();
		try host.loadAlphabetData(alphaPath) catch (error:Dynamic) {
			reportFailure('load source alphabet data', error);
			throw error;
		}
		ensureActive();
	}

	/** Look up a phrase using Psych's normalized key, fallback and format rules. */
	public function getPhrase(key:String, ?defaultPhrase:String, values:Array<Dynamic> = null):String {
		ensureActive();
		var str:String = ownerPhrases.get(formatKey(key));
		if (str == null) str = defaultPhrase;
		if (str == null) str = key;
		if (values != null)
			for (num => value in values)
				str = str.replace('{${num + 1}}', value);
		return str;
	}

	/** More optimized file-key lookup used by Psych's asset path helpers. */
	public function getFileTranslation(key:String):String {
		ensureActive();
		var str:String = ownerPhrases.get(key.trim().toLowerCase());
		if (str != null) key = str;
		return key;
	}

	/** Release every callback and phrase table retained by this imported owner. */
	public function release():Void {
		if (released) return;
		released = true;
		if (ownerPhrases != null) ownerPhrases.clear();
		ownerPhrases = null;
		ownerPrefs = null;
		host = null;
	}

	function formatKey(key:String):String {
		final hideChars = ~/[~&\\\/;:<>#.,'"%?!]/g;
		return hideChars.replace(key.replace(' ', '_'), '').toLowerCase().trim();
	}

	function preferenceString(prefs:Dynamic, objectField:String, valueField:String):String {
		var object = Reflect.field(prefs, objectField);
		var value:Dynamic = object == null ? null : Reflect.field(object, valueField);
		if (!Std.isOfType(value, String))
			throw '[psych-language] Owner ClientPrefs.$objectField.$valueField is unavailable';
		return cast value;
	}

	function reportFailure(operation:String, error:Dynamic):Void {
		if (host == null || host.report == null) return;
		try host.report('[psych-language] $operation failed for $ownerRoot: ${Std.string(error)}') catch (_:Dynamic) {}
	}

	function ensureActive():Void {
		if (released || host == null || host.ownerActive == null || !host.ownerActive())
			throw '[psych-language] This imported owner language runtime has been released';
	}
}
