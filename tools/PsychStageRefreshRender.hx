import haxe.Json;
import sys.io.File;

/** Thin interpreter bridge to the engine-owned Psych source-stage parser. */
class PsychStageRefreshRender {
	static function main():Void {
		var args = Sys.args();
		if (args.length == 0)
			throw 'missing request file';
		var request:Dynamic = Json.parse(File.getContent(args[0]));
		var donorRoot:Dynamic = Reflect.field(request, 'donorRoot');
		if (donorRoot == null || !Std.isOfType(donorRoot, String))
			throw 'missing donor root';
		var root:String = cast donorRoot;
		var charts:Array<Dynamic> = cast Reflect.field(request, 'charts');
		if (charts == null)
			charts = [];
		var rendered:Array<Dynamic> = [];
		for (chart in charts) {
			var id:Dynamic = Reflect.field(chart, 'id');
			var song:Dynamic = Reflect.field(chart, 'song');
			if (id == null || song == null || !Std.isOfType(id, String)
				|| !Std.isOfType(song, String))
				throw 'chart inference request requires string id and song';
			rendered.push({id:id, song:song, stage:PsychStageInference.resolve(root, cast song)});
		}
		Sys.println(Json.stringify({
			owner:CompatScriptManifest.destinationRoot(root, 'Psych Engine'),
			charts:rendered
		}));
	}
}
