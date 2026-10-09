package;

import animate.FlxAnimateFrames;
import animate.FlxAnimateFrames.SpritemapInput;

/** Loads a source Animate folder through an already owner-bound Assets facade.
 * No host registry, working-directory switch, filesystem scan or guessed alias. */
class SourceAnimateAtlasLoader {
	public static function load(path:String, assets:Dynamic, requireActive:Void->Void, cacheNamespace:String):{frames:FlxAnimateFrames, data:Dynamic} {
		requireActive();
		if (path == null || path == '') throw '[source-animate-atlas] Atlas path is empty';
		path = path.split('\\').join('/');
		while (StringTools.endsWith(path, '/')) path = path.substr(0, path.length - 1);
		if (StringTools.endsWith(path.toLowerCase(), '.zip'))
			throw '[source-animate-atlas] Packed ZIP atlas loading is not implemented';
		var manifest:String = assets.getText(path + '/Animation.json');
		var spritemaps:Array<SpritemapInput> = [];
		function append(id:String):Void {
			requireActive();
			var json:String = assets.getText(id).split(String.fromCharCode(0xFEFF)).join('');
			var map:Dynamic = haxe.Json.parse(json);
			var name:Dynamic = map.meta == null ? null : map.meta.image;
			if (!Std.isOfType(name,String) || name == '')
				throw '[source-animate-atlas] Missing declared spritemap image: ' + id;
			var imageId = path + '/' + Std.string(name);
			if (Std.string(name).split('/').indexOf('..') >= 0 || name.indexOf('\x00') >= 0 || name.indexOf(':') >= 0 || name.indexOf('\\') >= 0 || StringTools.startsWith(name,'/'))
				throw '[source-animate-atlas] Spritemap image leaves atlas namespace: ' + id;
			if (!assets.exists(imageId,'IMAGE')) throw '[source-animate-atlas] Missing declared image: ' + imageId;
			spritemaps.push({source:assets.getBitmapData(imageId),json:json});
		}
		// The historical loader checks the unnumbered map, then the contiguous
		// sequence starting at one. It does not enumerate all Assets.list entries.
		if (assets.exists(path + '/spritemap.json','TEXT')) append(path + '/spritemap.json');
		var index = 1;
		while (assets.exists(path + '/spritemap' + index + '.json','TEXT')) {
			if (index > 4096) throw '[source-animate-atlas] Spritemap count limit';
			append(path + '/spritemap' + index + '.json'); index++;
		}
		if (spritemaps.length == 0) throw '[source-animate-atlas] No declared spritemaps: ' + path;
		var metadataId = path + '/metadata.json';
		var metadata:String = assets.exists(metadataId, 'TEXT') ? assets.getText(metadataId) : null;
		requireActive();
		var frames = FlxAnimateFrames.fromAnimate(manifest, spritemaps, metadata, cacheNamespace + ':legacy-animate:' + path, true);
		if (frames == null) throw '[source-animate-atlas] Could not decode atlas: ' + path;
		return {frames:frames, data:haxe.Json.parse(manifest)};
	}
}
