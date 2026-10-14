package;

/**
	Reads a V-Slice conversation (data/dialogue/conversations/<id>.json) into
	the base game's dialogue text, so PlayState.startConversation can show it
	in the same dialogue box Psych's startDialogue uses.

	A V-Slice entry holds one speaker and box with a list of text pages; the
	base box shows one page per line, so every page becomes its own line with
	the entry's speaker and box. Speaker sprites, box animations, backdrops and
	outro fades have no base equivalent yet and are left out.
*/
class VSliceConversation {
	static final FOLDERS:Array<String> = ['data/dialogue/conversations', 'dialogue/conversations'];

	/** Files under one root where conversation `id` may live, nearest layout first. */
	public static function candidatePaths(root:String, id:String):Array<String> {
		var paths:Array<String> = [];
		var name = safeId(id);
		if (name == '' || root == null)
			return paths;
		var base = StringTools.replace(root, '\\', '/');
		while (base.length > 0 && StringTools.endsWith(base, '/'))
			base = base.substr(0, base.length - 1);
		var prefix = base == '' ? '' : base + '/';
		for (folder in FOLDERS) {
			paths.push(prefix + folder + '/' + name + '.json');
			// Packs that keep each conversation's music beside it use one folder per id.
			paths.push(prefix + folder + '/' + name + '/' + name + '.json');
		}
		return paths;
	}

	/** The id when it is a plain relative name, otherwise ''. */
	public static function safeId(id:String):String {
		if (id == null)
			return '';
		var clean = StringTools.trim(StringTools.replace(id, '\\', '/'));
		if (StringTools.endsWith(clean.toLowerCase(), '.json'))
			clean = clean.substr(0, clean.length - 5);
		if (clean == '' || clean.indexOf(':') >= 0 || StringTools.startsWith(clean, '/'))
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		return clean;
	}

	/** One row per text page, in reading order. */
	public static function lines(data:Dynamic):Array<{speaker:String, box:String, text:String}> {
		var rows:Array<{speaker:String, box:String, text:String}> = [];
		var entries:Dynamic = data == null ? null : Reflect.field(data, 'dialogue');
		if (!Std.isOfType(entries, Array))
			return rows;
		for (entry in (cast entries:Array<Dynamic>)) {
			if (entry == null)
				continue;
			var speaker = stringField(entry, 'speaker');
			var box = stringField(entry, 'box');
			var text:Dynamic = Reflect.field(entry, 'text');
			var pages:Array<Dynamic> = Std.isOfType(text, Array) ? cast text : (text == null ? [] : [text]);
			for (page in pages)
				if (page != null && StringTools.trim(Std.string(page)) != '')
					rows.push({speaker: speaker, box: box, text: Std.string(page)});
		}
		return rows;
	}

	/** Base dialogue text for a conversation, or null when it has no lines. */
	public static function dialogueText(data:Dynamic, player1:String = 'bf', player2:String = 'dad'):String {
		var rows = lines(data);
		if (rows.length == 0)
			return null;
		return EngineCompat.legacyDialogueText({dialogue: rows}, player1, player2);
	}

	/** Music key the conversation plays, as V-Slice's Paths.music takes it; null when none. */
	public static function musicAsset(data:Dynamic):String {
		var music:Dynamic = data == null ? null : Reflect.field(data, 'music');
		if (music == null)
			return null;
		var asset = stringField(music, 'asset');
		return asset == '' ? null : asset;
	}

	static function stringField(value:Dynamic, field:String):String {
		var found:Dynamic = Reflect.field(value, field);
		return found == null ? '' : StringTools.trim(Std.string(found));
	}
}
