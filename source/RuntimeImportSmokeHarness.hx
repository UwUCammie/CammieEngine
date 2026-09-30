package;

import haxe.Json;
using StringTools;

#if sys
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
#end

/**
	Opt-in native import-preparation entry point.

	Unlike the structural mounted audit, this harness runs inside the already
	built game.  ImportWorkflow therefore uses the complete native
	ModuleFunctions/HxcCompat/LuaCompat/converter graph and writes real assets
	beside the built runtime.  No normal launch enables this mode: it is entered
	only when --smoke-import-source is present.
*/
typedef RuntimeImportSmokeOptions = {
	var source:String;
	var importType:String;
	var scanOnly:Bool;
	/** Continue in this process to one direct chart smoke after the import. */
	var playAfterImport:Bool;
	var packageName:String;
	var packageNameProvided:Bool;
	var timeoutMs:Int;
	var logPath:String;
}

class RuntimeImportSmokeHarness {
	static var parsed:Null<RuntimeImportSmokeOptions>;
	static var argumentsSeen:Bool = false;
	static var finished:Bool = false;
	static var startedAt:Float = 0;
	static var timeoutReported:Bool = false;
	/** RuntimeImportSmokeState already initialized the shared game services. */
	static var preparedRuntimeForPlay:Bool = false;

	public static function enabled():Bool {
		return config() != null && argumentsSeen;
	}

	public static function config():Null<RuntimeImportSmokeOptions> {
		if (parsed != null)
			return parsed;
		var result:RuntimeImportSmokeOptions = {
			source: '',
			importType: 'Auto',
			scanOnly: false,
			playAfterImport: false,
			packageName: '',
			packageNameProvided: false,
			timeoutMs: 900000,
			logPath: 'tmp/runtime-smoke/import.log'
		};
		#if sys
		var args = Sys.args();
		var index = 0;
		while (index < args.length) {
			var key = args[index];
			var value:Null<String> = null;
			var equals = key.indexOf('=');
			if (equals >= 0) {
				value = key.substr(equals + 1);
				key = key.substr(0, equals);
			} else if (index + 1 < args.length && !args[index + 1].startsWith('--')) {
				value = args[index + 1];
				index++;
			}
			switch (key) {
				case '--smoke-import-source':
					argumentsSeen = true;
					result.source = value == null ? '' : StringTools.trim(value);
				case '--smoke-import-type':
					argumentsSeen = true;
					result.importType = value == null ? 'Auto' : StringTools.trim(value);
				case '--smoke-import-scan-only':
					argumentsSeen = true;
					result.scanOnly = true;
				case '--smoke-import-play-after-complete':
					argumentsSeen = true;
					result.playAfterImport = true;
				case '--smoke-import-package-name':
					argumentsSeen = true;
					result.packageNameProvided = true;
					result.packageName = value == null ? '' : StringTools.trim(value);
				case '--smoke-import-timeout-ms':
					argumentsSeen = true;
					result.timeoutMs = boundedTimeout(parseInt(value, result.timeoutMs));
				case '--smoke-import-log':
					argumentsSeen = true;
					result.logPath = value == null ? '' : StringTools.trim(value);
				default:
			}
			index++;
		}
		#else
		argumentsSeen = false;
		#end
		if (!argumentsSeen) {
			parsed = null;
			return null;
		}
		if (result.importType == '')
			result.importType = 'Auto';
		parsed = result;
		return parsed;
	}

	public static function start():Void {
		if (!enabled() || startedAt != 0)
			return;
		startedAt = #if sys Sys.time() #else 0 #end;
		emit('startup', {
			source: config().source,
			importType: config().importType,
			timeoutMs: config().timeoutMs
		});
	}

	public static function expired():Bool {
		if (!enabled() || finished || startedAt == 0)
			return false;
		#if sys
		return Sys.time() - startedAt >= config().timeoutMs / 1000.0;
		#else
		return false;
		#end
	}

	public static function timeoutCancellationRequested():Bool
		return timeoutReported;

	public static function markScanReady(result:Dynamic):Void {
		if (!enabled() || finished)
			return;
		emit('scan_ready', {
			songsFound: fieldInt(result, 'songsFound'),
			songsToImport: fieldInt(result, 'songsToImport'),
			duplicateSongs: fieldInt(result, 'duplicateSongs'),
			missingDependencies: fieldInt(result, 'missingDependencies'),
			errors: arrayLength(result == null ? null : Reflect.field(result, 'errors')),
			errorDetails: boundedErrors(result == null ? null : Reflect.field(result, 'errors'))
		});
	}

	/** A scan probe stops before the importer writes any selected content. */
	public static function finishScan(result:Dynamic):Void {
		if (!enabled() || finished)
			return;
		finished = true;
		emit('success', {
			phase: 'scan',
			songsFound: fieldInt(result, 'songsFound'),
			songsToImport: fieldInt(result, 'songsToImport'),
			errors: arrayLength(result == null ? null : Reflect.field(result, 'errors'))
		});
		#if sys
		Sys.exit(0);
		#end
	}

	public static function markImportStart():Void {
		if (!enabled() || finished)
			return;
		emit('import_start', {importType: config().importType});
	}

	public static function finish(result:Dynamic, error:Dynamic):Bool {
		if (!enabled() || finished)
			return false;
		if (error != null) {
			fail('import', Std.string(error));
			return false;
		}
		if (result == null) {
			fail('import', 'ImportWorkflow returned no result');
			return false;
		}
		var failed = fieldInt(result, 'failed');
		var found = fieldInt(result, 'found');
		if (failed > 0) {
			fail('import', 'writer reported failed=' + failed);
			return false;
		}
		if (found <= 0) {
			fail('import', 'writer found no songs');
			return false;
		}
		var summary = {
			found: found,
			imported: fieldInt(result, 'imported'),
			skipped: fieldInt(result, 'skipped'),
			failed: failed,
			copiedAssets: fieldInt(result, 'copiedAssets'),
			skippedAssets: fieldInt(result, 'skippedAssets'),
			missingDependencies: fieldInt(result, 'missingDependencies'),
			errors: arrayLength(Reflect.field(result, 'errors')),
			errorDetails: boundedErrors(Reflect.field(result, 'errors'))
		};
		finished = true;
		if (config().playAfterImport) {
			// RuntimeImportSmokeState has already polled ImportImportJob to
			// completion, which performs completeImportOnMainThread before the
			// progress snapshot is returned. Keep this runtime alive and let the
			// caller enter the normal direct-chart smoke state.
			preparedRuntimeForPlay = true;
			emit('import_complete', summary);
			return true;
		}
		emit('success', summary);
		#if sys
		Sys.exit(0);
		#end
		return false;
	}

	/** Consume the setup performed before import so follow-up play does not
	 * reinitialize process-global plugin and difficulty registries. */
	public static function consumePreparedRuntimeForPlay():Bool {
		var prepared = preparedRuntimeForPlay;
		preparedRuntimeForPlay = false;
		return prepared;
	}

	public static function fail(kind:String, detail:String):Void {
		if (!enabled() || finished)
			return;
		finished = true;
		emit('failure', {kind: kind, detail: detail == null ? '' : detail});
		#if sys
		Sys.exit(1);
		#end
	}

	/** Request cancellation once; the state waits for the worker before exit. */
	public static function requestTimeoutCancellation():Void {
		if (!enabled() || finished || timeoutReported)
			return;
		timeoutReported = true;
		emit('timeout', {timeoutMs: config().timeoutMs});
	}

	static function fieldInt(value:Dynamic, name:String):Int {
		if (value == null)
			return 0;
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? 0 : Std.int(field);
	}

	static function arrayLength(value:Dynamic):Int
		return value != null && Std.isOfType(value, Array) ? (cast value:Array<Dynamic>).length : 0;

	static function boundedErrors(value:Dynamic):Array<String> {
		var result:Array<String> = [];
		if (value == null || !Std.isOfType(value, Array)) return result;
		for (item in (cast value:Array<Dynamic>)) {
			if (result.length >= 20) break;
			var message = Std.string(item);
			result.push(message.length > 500 ? message.substr(0, 500) : message);
		}
		return result;
	}

	static function parseInt(raw:Null<String>, fallback:Int):Int {
		if (raw == null)
			return fallback;
		var value = Std.parseInt(StringTools.trim(raw));
		return value == null ? fallback : value;
	}

	static function boundedTimeout(value:Int):Int
		return Std.int(Math.max(1000, Math.min(3600000, value)));

	static function emit(event:String, extra:Dynamic):Void {
		var payload:Dynamic = {
			event: event,
			marker: 'runtime-import-smoke',
			time: #if sys Sys.time() #else 0 #end
		};
		if (extra != null)
			for (field in Reflect.fields(extra))
				Reflect.setField(payload, field, Reflect.field(extra, field));
		var line = 'RUNTIME_IMPORT_SMOKE|' + Json.stringify(payload);
		#if sys
		Sys.println(line);
		var path = config() == null ? '' : config().logPath;
		if (path != null && StringTools.trim(path) != '') {
			try {
				ensureParent(path);
				var stream = File.append(path, false);
				stream.writeString(line + '\n');
				stream.close();
			} catch (error:Dynamic) {
				Sys.println('RUNTIME_IMPORT_SMOKE|' + Json.stringify({event: 'log_failure', detail: Std.string(error)}));
			}
		}
		#end
	}

	#if sys
	static function ensureParent(path:String):Void {
		var parent = Path.directory(Path.normalize(path));
		if (parent == null || parent == '' || parent == '.')
			return;
		ensureDirectory(parent);
	}

	static function ensureDirectory(path:String):Void {
		var normalized = Path.normalize(path);
		if (normalized == '' || normalized == '.' || FileSystem.exists(normalized))
			return;
		var parent = Path.directory(normalized);
		if (parent != normalized && parent != '')
			ensureDirectory(parent);
		try FileSystem.createDirectory(normalized) catch (_:Dynamic) {}
	}
	#end
}
