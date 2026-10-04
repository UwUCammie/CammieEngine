package;

#if sys
import sys.FileSystem;
#end

using StringTools;

typedef PsychSkinDescriptor = {
	var key:String;
	var ownerRoot:String;
	var image:String;
	var metadata:String;
	var endsImage:String;
	var pixel:Bool;
	/** Engine-owned colored NOTE_assets used when a loose legacy chart has no
	 * selected-owner Psych skin. Unlike authored Psych skins, it needs no RGB. */
	var nativeDefaultFallback:Bool;
}

typedef PsychSkinResolution = {
	var descriptor:PsychSkinDescriptor;
	var reason:String;
}

/** Resolve complete Psych note atlases without crossing import ownership. */
class PsychSkinResolver {
	public static function resolve(key:String, selectedRoot:String, pixel:Bool,
		?postfix:String):PsychSkinDescriptor {
		return resolveDetailed(key, selectedRoot, pixel, postfix).descriptor;
	}

	public static function resolveDetailed(key:String, selectedRoot:String, pixel:Bool,
		?postfix:String):PsychSkinResolution {
		#if !sys
		return failure('Psych skin filesystem resolution requires a sys target');
		#else
		var clean = safeKey(key);
		if (clean == '')
			return failure('unsafe skin key: ' + Std.string(key));
		var root = selectedRoot == null ? '' : selectedRoot;
		if (root != '' && !safeOwner(root))
			return failure('unsafe owner: ' + root + ' for Psych skin ' + clean);
		var suffix = postfix == null ? '' : postfix;
		if (suffix != '' && !safePostfix(suffix))
			return failure('unsafe skin postfix: ' + suffix + ' for ' + clean);

		var owner = root == '' ? 'assets/images' : root;
		var directories = root == ''
			? ['assets/images']
			: [root + '/images', root + '/shared/images'];
		var missing:Array<String> = [];
		for (directory in directories) {
			var relative = pixel ? 'pixelUI/' + clean : clean;
			var variant = suffix == '' ? null : candidate(directory, relative + suffix, clean + suffix,
				owner, pixel, pixel ? relative + 'ENDS' + suffix : null);
			if (variant != null && variant.descriptor != null)
				return variant;
			var base = candidate(directory, relative, clean, owner, pixel);
			if (base.descriptor != null)
				return base;
			if (variant != null && variant.reason != '')
				missing.push(variant.reason);
			missing.push(base.reason);
		}
		// Psych's unmodified note skin is part of the source engine, so a mod
		// does not need to package its own copy. The native normal UI atlas is
		// that base skin; only this default key may cross the selected owner.
		if (root != '' && !pixel && clean == 'noteSkins/NOTE_assets') {
			var nativeDefault = candidate('assets/images/custom_ui/ui_packs/normal',
				'NOTE_assets', clean, 'assets/images', false, null, true);
			if (nativeDefault.descriptor != null)
				return nativeDefault;
			missing.push(nativeDefault.reason);
		}
		return failure('missing Psych skin ' + clean + ' in ' + owner + ': ' + missing.join('; '));
		#end
	}

	#if sys
	static function candidate(directory:String, relative:String, key:String, owner:String,
		pixel:Bool, ?pixelEndsRelative:String, ?nativeDefaultFallback:Bool = false):PsychSkinResolution {
		var stem = directory + '/' + relative;
		var image = stem + '.png';
		var metadata = pixel ? null : stem + '.xml';
		var endsImage = pixel
			? directory + '/' + (pixelEndsRelative == null ? relative + 'ENDS' : pixelEndsRelative) + '.png'
			: null;
		var files = pixel ? [image, endsImage] : [image, metadata];
		var missing:Array<String> = [];
		for (file in files) {
			var state = fileState(file);
			if (state != 'ok')
				missing.push(state + ' ' + file);
		}
		if (missing.length > 0)
			return failure(missing.join(', '));
		var descriptor:PsychSkinDescriptor = {
			key:key, ownerRoot:owner, image:image, metadata:metadata,
			endsImage:endsImage, pixel:pixel, nativeDefaultFallback:nativeDefaultFallback
		};
		return {descriptor:descriptor, reason:''};
	}
	#end

	static function failure(reason:String):PsychSkinResolution {
		return {descriptor:null, reason:reason};
	}

	/** A logical key may contain subfolders, but never a filesystem escape. */
	static function safeKey(value:String):String {
		if (value == null || value == '' || value != value.trim() || value.indexOf('\\') >= 0
			|| value.indexOf(':') >= 0 || value.indexOf('\x00') >= 0)
			return '';
		var clean = value;
		if (clean.endsWith('.png') || clean.endsWith('.xml'))
			return '';
		var parts = clean.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || hasControl(part))
				return '';
		return clean;
	}

	static function safePostfix(value:String):Bool {
		return value != '' && value.indexOf('/') < 0 && value.indexOf('\\') < 0
			&& value.indexOf(':') < 0 && value.indexOf('.') < 0 && !hasControl(value);
	}

	static function safeOwner(value:String):Bool {
		if (value.indexOf('\\') >= 0 || value.indexOf(':') >= 0
			|| !value.startsWith('assets/imported_mods/'))
			return false;
		var parts = value.split('/');
		if (parts.length != 3)
			return false;
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || hasControl(part))
				return false;
		return true;
	}

	static function hasControl(value:String):Bool {
		for (i in 0...value.length) {
			var code = value.charCodeAt(i);
			if (code < 32 || code == 127)
				return true;
		}
		return false;
	}

	/** Check each existing path component for exact case and case collisions. */
	#if sys
	static function fileState(path:String):String {
		var current = '';
		for (part in path.split('/')) {
			if (current != '' && FileSystem.exists(current) && FileSystem.isDirectory(current)) {
				var matches = 0;
				var exact = false;
				for (entry in FileSystem.readDirectory(current))
					if (entry.toLowerCase() == part.toLowerCase()) {
						matches++;
						if (entry == part)
							exact = true;
					}
				if (matches > 1)
					return 'ambiguous case';
				if (matches == 1 && !exact)
					return 'case mismatch';
			}
			current = current == '' ? part : current + '/' + part;
		}
		return FileSystem.exists(path) && !FileSystem.isDirectory(path) ? 'ok' : 'missing';
	}
	#end
}
