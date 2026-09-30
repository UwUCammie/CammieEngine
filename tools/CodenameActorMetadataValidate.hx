import haxe.Json;
import sys.io.File;

/** Validate refresh inputs using the same schema as live actor construction. */
class CodenameActorMetadataValidate {
	static function main():Void {
		var paths:Array<String> = Json.parse(File.getContent(Sys.args()[0]));
		for (path in paths) CodenameScriptPlan.parseCamera(File.getContent(path));
		Sys.println('validated');
	}
}
