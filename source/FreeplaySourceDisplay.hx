package;

/** Separate an imported chart's title from its package label for Freeplay.
 * Existing imports kept the label in display; their destination provenance
 * supplies the exact suffix so ordinary titles containing · are untouched. */
class FreeplaySourceDisplay {
	static function normalized(value:String):String {
		var result = '';
		for (char in value.toLowerCase().split(''))
			if ((char >= 'a' && char <= 'z') || (char >= '0' && char <= '9'))
				result += char;
		return result;
	}

	public static function resolve(display:String, sourceLabel:String, songKey:String,
		legacyProvenance:Dynamic, ?legacyChartTitle:String,
		?validatedStaleGenericLabel:String):{title:String, source:String} {
		var title = display == null ? '' : display;
		var source = sourceLabel == null ? '' : StringTools.trim(sourceLabel);
		// The destination receipt is the ownership proof.  Older collision rows
		// also embedded the package label in display, while ordinary imported rows
		// did not; both should get the same separate Freeplay subtitle.
		if (source == '' && legacyProvenance != null
			&& Reflect.field(legacyProvenance, 'destinationFolder') == songKey) {
			var modName:Dynamic = Reflect.field(legacyProvenance, 'modName');
			var engine:Dynamic = Reflect.field(legacyProvenance, 'sourceEngine');
			if (Std.isOfType(modName, String) && StringTools.trim(cast(modName, String)) != '') {
				var engineName = Std.isOfType(engine, String) ? cast(engine, String) : '';
				var candidate = ImportSongOwnership.displayWithEngine(cast modName, engineName);
				if (candidate != '')
					source = candidate;
			}
			if (source == '' && Std.isOfType(engine, String)
				&& Std.isOfType(Reflect.field(legacyProvenance, 'sourceFolder'), String)) {
				var sourceFolder:String = Reflect.field(legacyProvenance, 'sourceFolder');
				var knownTitle = legacyChartTitle == null ? '' : StringTools.trim(legacyChartTitle);
				var boundary = title.indexOf(' · ');
				while (boundary >= 0) {
					var candidate = title.substr(boundary + 3);
					var prefix = normalized(title.substr(0, boundary));
					if ((prefix == normalized(sourceFolder)
						|| (knownTitle != '' && prefix == normalized(knownTitle)))
						&& StringTools.endsWith(candidate.toLowerCase(),
							StringTools.trim(cast(engine, String)).toLowerCase())) {
						source = candidate;
						break;
					}
					boundary = title.indexOf(' · ', boundary + 3);
				}
			}
		}
		if (source != '') {
			var suffix = ' · ' + source;
			if (StringTools.endsWith(title, suffix))
				title = title.substr(0, title.length - suffix.length);
		}
		// FreeplayState supplies this only after the same receipt has passed the
		// inferred-container owner and engine checks. Strip the old label suffix
		// only when it is the exact trailing text, preserving authored title text.
		if (validatedStaleGenericLabel != null && validatedStaleGenericLabel != '') {
			var staleSuffix = ' · ' + validatedStaleGenericLabel;
			if (StringTools.endsWith(title, staleSuffix))
				title = title.substr(0, title.length - staleSuffix.length);
		}
		return {title:title, source:source};
	}
}
