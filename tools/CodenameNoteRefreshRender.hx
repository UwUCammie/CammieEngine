import haxe.Json;
import sys.io.File;

/** Read-only, portable-Haxe bridge for the reviewed Codename note refresh. */
class CodenameNoteRefreshRender {
	static function main():Void {
		var args = Sys.args();
		if (args.length != 1) throw 'Expected one request file';
		var request:Dynamic = Json.parse(File.getContent(args[0]));
		var donor:String = Reflect.field(request, 'donorRoot');
		var sharedDefinitions:Array<Dynamic> = [];
		var sharedKindIndexes:Map<String, Int> = new Map();
		var previousSong:String = null;
		var result:Array<Dynamic> = [];
		for (item in (cast Reflect.field(request, 'charts'):Array<Dynamic>)) {
			var song:String = Reflect.field(item, 'song');
			if (song != previousSong) {
				sharedDefinitions = [];
				sharedKindIndexes = new Map();
				previousSong = song;
			}
			var meta:Dynamic = Json.parse(File.getContent(Reflect.field(item, 'meta')));
			var chart:Dynamic = Json.parse(File.getContent(Reflect.field(item, 'chart')));
			var converted = CodenameImporter.convert(meta, chart,
				Reflect.field(item, 'difficulty'), Reflect.field(item, 'chart'), null,
				sharedDefinitions, sharedKindIndexes);
			if (converted.charts == null || converted.charts.length != 1)
				throw 'Codename converter did not return exactly one chart';
			var nativeChart:Dynamic = converted.charts[0].chart;
			var songData:Dynamic = Reflect.field(nativeChart, 'song');
			var notes:Dynamic = Reflect.field(songData, 'notes');
			if (!Std.isOfType(notes, Array)) throw 'Converted chart has no native notes';
			result.push({id:Reflect.field(item, 'id'),
				nativeFile:VSliceImporter.nativeFileName('chart', Reflect.field(item, 'difficulty')),
				current:notes});
		}
		Sys.println(Json.stringify({namespace:CompatScriptManifest.destinationRoot(donor,
			ImportEngine.CODENAME), charts:result}));
	}
}
