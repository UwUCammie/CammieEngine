package;

/** Explicit placeholder for a donor import whose implementation is absent.
	Import validation can still distinguish an unused import from an invoked
	constructor; invocation fails once with a precise compatibility diagnostic.
*/
class CodenameUnavailableApi {
	public function new(?sourceType:String = 'imported API') {
		throw '[codename-unsupported-api] ' + sourceType + ' has no native adapter';
	}
}
