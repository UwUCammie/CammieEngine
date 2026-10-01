package;

#if sys
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
#end

/** HTTPS transport for the Windows updater. URLMon uses the Windows/Wine
 * certificate store and follows the release asset redirect while streaming
 * the response to disk. Digest verification remains in the update helper. */
#if (cpp && windows)
@:cppFileCode('#include <windows.h>\n#include <urlmon.h>')
@:buildXml("<target id='haxe' if='HXCPP_MINGW'><lib name='-lurlmon'/></target><target id='haxe' unless='HXCPP_MINGW'><lib name='urlmon.lib'/></target>")
#end
class WindowsUpdateDownload {
	public static function toFile(url:String, destination:String):Void {
		if (url == null || !StringTools.startsWith(url, 'https://'))
			throw 'The updater requires an HTTPS URL.';
		#if (cpp && windows)
		var result:Int = untyped __cpp__('URLDownloadToFileW(NULL, {0}.__WCStr(), {1}.__WCStr(), 0, NULL)', url, destination);
		if (result < 0) throw 'Windows HTTPS download failed (HRESULT 0x' + StringTools.hex(result, 8) + ').';
		#elseif sys
		var request = new haxe.Http(url);
		var error:Null<String> = null;
		request.onError = function(message:String) error = message;
		var output = File.write(destination, true);
		try request.customRequest(false, output) catch (failure:Dynamic) error = Std.string(failure);
		output.close();
		if (error != null) throw error;
		#else
		throw 'The updater download is unavailable on this target.';
		#end
	}

	#if sys
	public static function getText(url:String):String {
		var tempRoot = Sys.getEnv('TEMP');
		if (tempRoot == null || tempRoot == '') tempRoot = Sys.getCwd();
		var path = Path.join([tempRoot, 'cammie-update-api-' + Std.string(Std.int(Date.now().getTime()))
			+ '-' + Std.string(Std.random(1000000000)) + '.json']);
		var content:String;
		try {
			toFile(url, path);
			content = File.getContent(path);
		} catch (error:Dynamic) {
			if (FileSystem.exists(path)) FileSystem.deleteFile(path);
			throw error;
		}
		FileSystem.deleteFile(path);
		return content;
	}
	#end
}
