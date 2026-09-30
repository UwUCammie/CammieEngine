package;

import flixel.FlxG;
import haxe.io.Path;

/** Owner-scoped implementation of the classless StickerPack API used by
	Codename imports. It mirrors the donor helper's JSON shape and fallback
	behavior without compiling or editing the donor's source file.
*/
class CodenameStickerPack {
	public var id:String;
	public var _data:Dynamic;
	final ownerRoot:String;
	final paths:CodenamePaths;

	public function new(id:String) {
		var selectedOwner = CodenameTransitionScope.resolveStickerOwner(
			CodenameTransitionScope.executingTransitionOwner(),
			CodenameMusicBeatTransition.currentOwnerRoot(),
			CodenameTransitionScope.stateHandoffOwner());
		if (selectedOwner == null || selectedOwner == '')
			throw '[codename-sticker-pack] Sticker packs require an active Codename owner';
		ownerRoot = selectedOwner;
		paths = new CodenamePaths(ownerRoot);
		this.id = id;

		var packContent = readPack(id);
		if (packContent == null) {
			trace('[codename-sticker-pack] Sticker Pack "' + id + '" could not be found. Using default.');
			// The upstream helper reassigns its constructor argument here rather
			// than `this.id`; preserve that observable behavior.
			id = 'default';
			packContent = readPack(id);
			if (packContent == null)
				throw 'Default sticker pack "default" was null! This should not happen!';
		}
		_data = haxe.Json.parse(packContent);
	}

	function readPack(packId:String):Null<String> {
		if (packId == null || !CodenameScriptDiscovery.safeName(packId)) return null;
		var absolute:String;
		try absolute = paths.json('stickerpacks/' + packId) catch (_:Dynamic) return null;
		return FNFAssets.exists(absolute) ? FNFAssets.getText(absolute) : null;
	}

	public function getStickerPackName():Dynamic return _data.name;
	public function getStickerPackArtist():Dynamic return _data.artist;
	public function getStickers():Array<String> return cast _data.stickers;

	/** The D-Sides consumer passes an unused boolean although its donor helper
	 * declares no parameter. Accept and ignore that extra value so the helper
	 * retains the donor's actual random-selection behavior.
	 */
	public function getRandomStickerPath(?unused:Dynamic):String
		return getRandomString(getStickers());

	public function getRandomString(array:Array<String>):String
		return array[FlxG.random.int(0, array.length - 1)];
}
