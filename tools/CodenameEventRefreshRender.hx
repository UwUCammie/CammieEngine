import haxe.Json;
import sys.io.File;

/** Read-only, portable-Haxe bridge for the reviewed Codename event refresh. */
class CodenameEventRefreshRender {
	static function legacy(current:Array<Dynamic>, chartCount:Int):Array<Dynamic> {
		var ordered:Array<{index:Int, time:Float, row:Array<Dynamic>}> = [];
		for (group in current) for (entry in (cast group[1]:Array<Dynamic>)) {
			var row:Array<Dynamic> = cast entry;
			var info:Dynamic = row[4];
			var source:String = Reflect.field(info, 'source');
			var order:Int = Reflect.field(info, 'order');
			ordered.push({index:(source == 'shared' ? chartCount : 0) + order,
				time:Reflect.field(info, 'time'), row:row.slice(0, 4)});
		}
		ordered.sort(function(a, b) return a.index - b.index);
		var groups:Array<Dynamic> = [];
		for (entry in ordered) {
			var found = false;
			for (group in groups) {
				var delta = Math.abs((group[0]:Float) - entry.time);
				if (delta < 0.0001) {
					(cast group[1]:Array<Dynamic>).push(entry.row);
					found = true;
					break;
				}
			}
			if (!found) groups.push([entry.time, [entry.row]]);
		}
		// Keep the original insertion order of equal-time groups.
		var sorted:Array<Dynamic> = [];
		for (group in groups) {
			var at = sorted.length;
			while (at > 0 && (sorted[at - 1][0]:Float) > (group[0]:Float)) {
				sorted[at] = sorted[at - 1];
				at--;
			}
			sorted[at] = group;
		}
		return sorted;
	}

	static function main():Void {
		var args = Sys.args();
		if (args.length != 1) throw 'Expected one request file';
		var request:Dynamic = Json.parse(File.getContent(args[0]));
		var donor:String = Reflect.field(request, 'donorRoot');
		var result:Array<Dynamic> = [];
		for (item in (cast Reflect.field(request, 'charts'):Array<Dynamic>)) {
			var chart:Dynamic = Json.parse(File.getContent(Reflect.field(item, 'chart')));
			var sidecarPath:String = Reflect.field(item, 'sidecar');
			var sidecar:Dynamic = sidecarPath == null ? null : Json.parse(File.getContent(sidecarPath));
			var chartEvents:Dynamic = Reflect.field(chart, 'events');
			var count = Std.isOfType(chartEvents, Array) ? (cast chartEvents:Array<Dynamic>).length : 0;
			var merged = CodenameImporter.mergeEventSources(chartEvents,
				CodenameImporter.sidecarEvents(sidecar));
			var current = CodenameImporter.convertEvents(merged, [], '', Reflect.field(item, 'difficulty'), count);
			result.push({id:Reflect.field(item, 'id'),
				nativeFile:VSliceImporter.nativeFileName('chart', Reflect.field(item, 'difficulty')),
				current:current,
				legacy:legacy(current, count)});
		}
		Sys.println(Json.stringify({namespace:CompatScriptManifest.destinationRoot(donor,
			ImportEngine.CODENAME), charts:result}));
	}
}
