package;

/** Data-only Codename ChartData projection used when an imported package no
 * longer contains its original Codename chart JSON. Authored metadata remains
 * available from the importer's resolved metadata sidecar; native gameplay
 * data is exposed separately instead of being mislabeled as source strumlines.
 */
class CodenameChartDataCompat {
	static function safeName(value:String):Bool {
		return value != null && StringTools.trim(value) != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0
			&& value.indexOf('\u0000') < 0;
	}

	static function field(value:Dynamic, name:String):Dynamic
		return value == null ? null : Reflect.field(value, name);

	static function defaultMeta(song:String, nativeChart:Dynamic):Dynamic {
		var bpm:Dynamic = field(nativeChart, 'bpm');
		if (!Std.isOfType(bpm, Int) && !Std.isOfType(bpm, Float)) bpm = 100.0;
		return {name:song, displayName:song, bpm:bpm, beatsPerMeasure:4, stepsPerBeat:4,
			icon:'face', coopAllowed:false, opponentModeAllowed:false, instSuffix:'',
			vocalsSuffix:'', needsVoices:true, difficulties:[], variants:[], metas:{}, variant:null};
	}

	/** Build a transparent source-facing view around the selected native chart.
		The chart payload is intentionally named `nativeChart`: callers can inspect
		its converted fields without mistaking them for Codename's authored line
		and note structures. */
	public static function fromNative(song:String, difficulty:String, variant:Null<String>,
		nativeChart:Dynamic, resolvedMeta:Dynamic):Dynamic {
		if (!safeName(song) || !safeName(difficulty) || nativeChart == null
			|| Type.typeof(nativeChart) != TObject)
			throw '[codename-chart] Native chart projection requires a song, difficulty, and parsed chart';
		if (variant != null && StringTools.trim(variant) != '')
			throw '[codename-chart] Variant chart data was not imported for ' + song + ' (' + variant + ')';
		var meta = resolvedMeta == null ? defaultMeta(song, nativeChart) : resolvedMeta;
		var events:Dynamic = field(nativeChart, 'events');
		if (!Std.isOfType(events, Array)) events = [];
		return {
			strumLines:null,
			noteTypes:null,
			events:events,
			meta:meta,
			scrollSpeed:field(nativeChart, 'speed') == null ? 1 : field(nativeChart, 'speed'),
			stage:field(nativeChart, 'stage') == null ? 'stage' : field(nativeChart, 'stage'),
			codenameChart:true,
			fromMods:true,
			sourceChartAvailable:false,
			nativeChart:nativeChart
		};
	}

	/** Clone and complete an authored Codename chart's metadata without
		changing the donor source object. */
	public static function fromSource(song:String, difficulty:String, variant:Null<String>,
		sourceChart:Dynamic, resolvedMeta:Dynamic, ?config:Dynamic):Dynamic {
		if (!safeName(song) || !safeName(difficulty) || sourceChart == null
			|| Type.typeof(sourceChart) != TObject)
			throw '[codename-chart] Source chart must be an object';
		var chart:Dynamic = haxe.Json.parse(haxe.Json.stringify(sourceChart));
		if (!Std.isOfType(Reflect.field(chart, 'strumLines'), Array))
			throw '[codename-chart] Source chart has no strumLines array';
		var meta = resolvedMeta == null ? defaultMeta(song, chart) : resolvedMeta;
		var inlineMeta:Dynamic = Reflect.field(chart, 'meta');
		if (inlineMeta != null) {
			if (Type.typeof(inlineMeta) != TObject)
				throw '[codename-chart] Source chart meta must be an object';
			meta = haxe.Json.parse(haxe.Json.stringify(meta));
			for (name in Reflect.fields(inlineMeta)) {
				var value = Reflect.field(inlineMeta, name);
				if (value != null) Reflect.setField(meta, name, value);
			}
		}
		Reflect.setField(meta, 'name', song);
		Reflect.setField(meta, 'variant', variant == null || StringTools.trim(variant) == '' ? null : variant);
		Reflect.setField(chart, 'meta', meta);
		if (!Std.isOfType(Reflect.field(chart, 'events'), Array))
			Reflect.setField(chart, 'events', []);
		if (!Std.isOfType(Reflect.field(chart, 'noteTypes'), Array))
			Reflect.setField(chart, 'noteTypes', []);
		if (Reflect.field(chart, 'scrollSpeed') == null) {
			var defaultSpeed:Dynamic = config == null ? null : Reflect.field(config, 'scrollSpeed');
			Reflect.setField(chart, 'scrollSpeed', defaultSpeed == null ? 1 : defaultSpeed);
		}
		if (Reflect.field(chart, 'stage') == null) {
			var defaultStage:Dynamic = config == null ? null : Reflect.field(config, 'stage');
			Reflect.setField(chart, 'stage', defaultStage == null ? 'stage' : defaultStage);
		}
		Reflect.setField(chart, 'codenameChart', true);
		Reflect.setField(chart, 'fromMods', true);
		Reflect.setField(chart, 'sourceChartAvailable', true);
		var lines:Array<Dynamic> = cast Reflect.field(chart, 'strumLines');
		for (line in lines)
			if (line != null && Reflect.field(line, 'keyCount') == null)
				Reflect.setField(line, 'keyCount', 4);
		return chart;
	}
}
