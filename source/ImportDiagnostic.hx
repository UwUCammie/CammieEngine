package;

/**
	Shared classification for diagnostics attached to an import song plan.

	Import scans keep compatibility evidence in the same string array as
	actionable findings, so callers must classify the stable bracketed code
	before presenting or persisting a line.  Keep this policy engine-owned so
	Import Settings and the on-disk scan report cannot drift apart.
*/
class ImportDiagnostic {
	/** Return the presentation label for one import diagnostic. */
	public static function label(diagnostic:String):String {
		if (diagnostic == null)
			return "[WARNING]";
		var trimmed = StringTools.trim(diagnostic);
		if (!StringTools.startsWith(trimmed, '['))
			return "[WARNING]";
		var end = trimmed.indexOf(']');
		if (end <= 1)
			return "[WARNING]";
		var code = trimmed.substr(1, end - 1).toLowerCase();
		if (code == 'unsupported' || StringTools.startsWith(code, 'unsupported-') || code.indexOf('-unsupported-') >= 0)
			return "[UNSUPPORTED]";
		if (code == 'missing' || StringTools.startsWith(code, 'missing-') || code.indexOf('-missing-') >= 0)
			return "[MISSING]";
		if (code.indexOf('adapter') >= 0 || code.indexOf('alias') >= 0 || code.indexOf('route') >= 0
			|| code.indexOf('fallback') >= 0 || code.indexOf('preserved') >= 0
			|| code == 'split-vocal-stems' || code == 'extra-vocal-stem' || code == 'extra-vocal-stems'
			|| code == 'native-character-asset' || code == 'note-kind-native')
			return "[INFO]";
		return "[WARNING]";
	}
}
