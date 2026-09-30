package;

/** Source-declared mapping from a Psych Character constructor to a chart and
 * a stage object's static note list. Names come from the selected owner. */
class PsychMappedAnimsSource {
	public static function discover(source:String):Null<{
		character:String, chart:String, className:String, field:String,
		initialAnim:Null<String>, skipDance:Bool
	}> {
		if (source == null || source.length > 1024 * 1024 || !~/switch\s*\(\s*curCharacter\s*\)/.match(source))
			return null;
		var constructorCase = ~/case\s*['"]([^'"]+)['"]\s*:\s*([^{}]*?loadMappedAnims\s*\(\s*\))/;
		var chartRead = ~/Song\.getChart\s*\(\s*['"]([A-Za-z0-9_-]+)['"]/;
		var staticWrite = ~/([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*animationNotes\s*;/;
		if (!constructorCase.match(source) || !chartRead.match(source) || !staticWrite.match(source))
			return null;
		var character = constructorCase.matched(1);
		var afterCall = constructorCase.matchedPos().pos + constructorCase.matchedPos().len;
		var caseEnd = source.indexOf('case ', afterCall);
		var close = source.indexOf('}', afterCall);
		if (caseEnd < 0 || (close >= 0 && close < caseEnd)) caseEnd = close;
		if (caseEnd < 0) caseEnd = source.length;
		var rest = source.substr(constructorCase.matchedPos().pos,
			caseEnd - constructorCase.matchedPos().pos);
		var initialCall = ~/playAnim\s*\(\s*['"]([A-Za-z0-9_-]+)['"]/;
		var initialAnim = initialCall.match(rest) ? initialCall.matched(1) : null;
		var chart = chartRead.matched(1);
		if (!CodenameScriptDiscovery.safeName(character) || !CodenameScriptDiscovery.safeName(chart))
			return null;
		return {
			character:character, chart:chart,
			className:staticWrite.matched(1), field:staticWrite.matched(2),
			initialAnim:initialAnim, skipDance:~/skipDance\s*=\s*true/.match(rest)
		};
	}
}
