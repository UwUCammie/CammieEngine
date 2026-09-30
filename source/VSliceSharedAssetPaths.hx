package;

using StringTools;

/** Donor logical countdown names backed by the engine's shared sound pack. */
class VSliceSharedAssetPaths {
	/** Native equivalents for V-Slice's base countdown image library. V-Slice
	 * scripts use Paths.image() for these resources even when the mod export does
	 * not include the shared base game library. Keep custom/owner paths on their
	 * normal lookup path and only map this exact logical namespace. */
	public static function imageCandidates(key:String, ?uiPack:String):Array<String> {
		if (key == null) return [];
		var clean = StringTools.trim(StringTools.replace(key, '\\', '/'));
		while (clean.startsWith('./')) clean = clean.substr(2);
		while (clean.startsWith('/')) clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/images/'))
			clean = clean.substr('assets/images/'.length);
		else if (clean.toLowerCase().startsWith('images/'))
			clean = clean.substr('images/'.length);
		var separator = clean.indexOf(':');
		if (separator > 0) {
			var namespace = clean.substr(0, separator).toLowerCase();
			if (namespace != 'shared' && namespace != 'default') return [];
			clean = clean.substr(separator + 1);
		}
		if (clean.toLowerCase().startsWith('shared/'))
			clean = clean.substr('shared/'.length);
		if (clean.toLowerCase().endsWith('.png'))
			clean = clean.substr(0, clean.length - 4);
		var parts = clean.split('/');
		if (parts.length != 4 || parts[0].toLowerCase() != 'ui'
			|| parts[1].toLowerCase() != 'countdown')
			return [];
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return [];
		var style = parts[2].toLowerCase();
		var token = parts[3].toLowerCase();
		var pixel = style == 'pixel';
		var stem = switch (token) {
			case 'ready': 'ready';
			case 'set': 'set';
			case 'go': pixel ? 'date' : 'go';
			default: null;
		};
		if (stem == null) return [];
		var suffix = pixel ? '-pixel' : '';
		var file = stem + suffix;
		var candidates:Array<String> = [];
		var pack = safePackName(uiPack);
		if (pack != '') candidates.push('custom_ui/ui_packs/' + pack + '/' + file);
		if (pack != 'normal') candidates.push('custom_ui/ui_packs/normal/' + file);
		if (pixel)
			candidates.push('weeb/pixelUI/' + file);
		else
			candidates.push(stem);
		return candidates;
	}

	static function safePackName(value:String):String {
		if (value == null) return '';
		var clean = StringTools.trim(value);
		if (clean == '' || clean == '.' || clean == '..' || clean.indexOf('/') >= 0
			|| clean.indexOf('\\') >= 0 || clean.indexOf(':') >= 0)
			return '';
		return clean;
	}

	public static function sound(key:String):String {
		if (key == null) return null;
		var parts = StringTools.replace(StringTools.trim(key), '\\', '/').split('/');
		if (parts.length != 3 && parts.length != 4) return null;
		if (parts[0].toLowerCase() != 'gameplay' || parts[1].toLowerCase() != 'countdown')
			return null;
		var pixel = parts.length == 4;
		if (pixel && parts[2].toLowerCase() != 'pixel') return null;
		var token = parts[parts.length - 1].toLowerCase();
		if (token.endsWith('.ogg')) token = token.substr(0, token.length - 4);
		var ordinal = switch (token) {
			case 'introthree' | 'intro3': '3';
			case 'introtwo' | 'intro2': '2';
			case 'introone' | 'intro1': '1';
			case 'introgo': 'Go';
			default: null;
		};
		return ordinal == null ? null : 'assets/sounds/intro' + ordinal
			+ (pixel ? '-pixel' : '') + '.ogg';
	}
}
