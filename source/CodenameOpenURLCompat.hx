package;

/** Validate user-requested web links before handing them to the host browser. */
@:keep
class CodenameOpenURLCompat {
	public static function open(url:String, opener:String->Void):Bool {
		var safeUrl = normalize(url);
		if (safeUrl == null) {
			trace('[codename-open-url-rejected] Only absolute HTTP(S) URLs without credentials are allowed.');
			return false;
		}
		if (opener == null) {
			trace('[codename-open-url-unavailable] No native browser opener is available.');
			return false;
		}
		#if sys
		// Private offscreen menu checks must not activate the desktop browser.
		// Validate the source URL first so the test still exercises that boundary.
		if (Sys.getEnv('FNF_COMPAT_TEST_NO_BROWSER') == '1') {
			trace('[codename-open-url-test-suppressed] ' + safeUrl);
			return true;
		}
		#end
		try {
			opener(safeUrl);
			return true;
		} catch (error:Dynamic) {
			trace('[codename-open-url-failed] ' + Std.string(error));
			return false;
		}
	}

	/** Return a canonical web URL or null. Requiring a scheme and authority
	 * prevents FlxG.openURL's convenient implicit-https behavior from accepting
	 * javascript:, file:, protocol-relative, or credential-bearing destinations.
	 */
	public static function normalize(url:String):Null<String> {
		if (url == null || url != StringTools.trim(url)) return null;
		var lower = url.toLowerCase();
		var prefix = StringTools.startsWith(lower, 'https://') ? 'https://'
			: (StringTools.startsWith(lower, 'http://') ? 'http://' : null);
		if (prefix == null || url.length <= prefix.length) return null;

		for (index in 0...url.length) {
			var code = url.charCodeAt(index);
			if (isSpaceOrControl(code) || url.charAt(index) == '\\') return null;
		}

		var remainder = url.substr(prefix.length);
		var authorityEnd = remainder.length;
		for (separator in ['/', '?', '#']) {
			var index = remainder.indexOf(separator);
			if (index >= 0 && index < authorityEnd) authorityEnd = index;
		}
		var authority = remainder.substr(0, authorityEnd);
		if (authority == '' || authority.indexOf('@') >= 0 || !validAuthority(authority))
			return null;
		return prefix + remainder;
	}

	static function validAuthority(authority:String):Bool {
		var port:Null<String> = null;
		if (authority.charAt(0) == '[') {
			var close = authority.indexOf(']');
			if (close <= 1) return false;
			var address = authority.substr(1, close - 1);
			if (address.indexOf(':') < 0 || !~/^[0-9A-Fa-f:.]+$/.match(address)) return false;
			var suffix = authority.substr(close + 1);
			if (suffix != '') {
				if (!StringTools.startsWith(suffix, ':')) return false;
				port = suffix.substr(1);
			}
		} else {
			if (authority.indexOf('[') >= 0 || authority.indexOf(']') >= 0) return false;
			var colon = authority.indexOf(':');
			var host = authority;
			if (colon >= 0) {
				if (colon != authority.lastIndexOf(':')) return false;
				host = authority.substr(0, colon);
				port = authority.substr(colon + 1);
			}
			if (host == '' || host.length > 253 || !~/^[A-Za-z0-9.-]+$/.match(host)) return false;
			if (host.charAt(0) == '.' || host.charAt(0) == '-'
				|| host.charAt(host.length - 1) == '-' || host.indexOf('..') >= 0) return false;
			var labels = host.split('.');
			for (index in 0...labels.length) {
				var label = labels[index];
				if (label == '' && index == labels.length - 1) continue;
				if (label == '' || label.length > 63
					|| label.charAt(0) == '-' || label.charAt(label.length - 1) == '-') return false;
			}
		}
		if (port != null) {
			if (port == '' || !~/^[0-9]+$/.match(port)) return false;
			var number = Std.parseInt(port);
			if (number == null || number < 1 || number > 65535) return false;
		}
		return true;
	}

	static function isSpaceOrControl(code:Int):Bool {
		return code <= 0x20 || code == 0x7F || code == 0xA0 || code == 0x1680
			|| (code >= 0x2000 && code <= 0x200A) || code == 0x2028 || code == 0x2029
			|| code == 0x202F || code == 0x205F || code == 0x3000 || code == 0xFEFF;
	}
}
