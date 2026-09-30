package;

import haxe.io.Bytes;
import haxe.io.Path;

#if sys
import sys.FileSystem;
import sys.io.File;
import sys.io.Process;
#end

using StringTools;

/** The fixed header and payload facts of one raw ASTC 2D image. */
typedef VSliceAstcHeader = {
	var valid:Bool;
	var source:String;
	var width:Int;
	var height:Int;
	var depth:Int;
	var blockX:Int;
	var blockY:Int;
	var blockZ:Int;
	var payloadBytes:Int;
	var expectedPayloadBytes:Float;
	var payloadMatches:Bool;
	var error:String;
}

/** Result of the optional external ASTC decoder capability probe. */
typedef VSliceAstcProbe = {
	var available:Bool;
	var executable:String;
	var reason:String;
	var searched:Array<String>;
}

/** Result of one ASTC -> PNG conversion attempt. */
typedef VSliceAstcDecodeResult = {
	var success:Bool;
	var executable:String;
	var message:String;
	var exitCode:Int;
}

/**
	Portable ASTC inspection and conversion boundary for V-Slice imports.

	V-Slice desktop exports contain raw ASTC 2D files rather than PNGs.  Lime
	and the old OpenFL/Flixel asset path used by this project do not provide a
	portable ASTC decoder, so this class keeps the boundary explicit:

	  * the 16-byte ASTC header is validated without a platform API;
	  * the build launchers install a pinned official `astcenc`, while compatible
	    user-provided executables remain discoverable on Linux or Windows;
	  * conversion uses `sys.io.Process` with an argument array, never a shell;
	  * a missing or failing decoder remains an actionable importer diagnostic.

	The adapter deliberately does not invent a PNG, reinterpret compressed
	blocks as pixels, or edit donor files.  The external dependency is the
	official `astcenc -ds input.astc output.png` command-line decoder. `-ds`
	selects the LDR sRGB profile used by the game's ordinary sprite/texture
	assets; raw ASTC headers do not carry a color profile.
*/
class VSliceAstcAdapter {
	public static inline var ASTC_MAGIC:Int = 0x5CA1AB13;
	public static inline var DECODER_ENV:String = 'DISAPPOINTINGPLUS_ASTCENC';
	public static inline var DECODER_INSTALL_HINT:String =
		'Rerun the platform build launcher to install its checksum-verified astcenc runtime tool, '
		+ 'or set DISAPPOINTINGPLUS_ASTCENC to a compatible executable path '
		+ '(it must support "astcenc -ds input.astc output.png").';

	#if sys
	static var cachedProbe:Null<VSliceAstcProbe> = null;
	static var cachedProbeKey:String = null;
	#end

	/** Parse a complete ASTC file held in memory.  The format stores all
	 * dimensions as little-endian 24-bit integers after the 4-byte magic. */
	public static function parseHeader(bytes:Bytes, ?source:String):VSliceAstcHeader {
		if (bytes == null)
			return invalidHeader(source, 'No ASTC bytes were provided.');
		if (bytes.length < 16)
			return invalidHeader(source, 'ASTC data is shorter than its 16-byte header.');
		return parseHeaderBytes(bytes, bytes.length - 16, source);
	}

	#if sys
	/** Read only the ASTC header from disk and use stat size for the payload
	 * check.  Large character atlases are not loaded into memory just to scan
	 * their dimensions. */
	public static function inspectFile(path:String):VSliceAstcHeader {
		if (path == null || path.trim() == '')
			return invalidHeader(path, 'ASTC source path is empty.');
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path))
			return invalidHeader(path, 'ASTC source file does not exist.');
		var input:haxe.io.Input = null;
		try {
			input = File.read(path, true);
			var bytes = input.read(16);
			input.close();
			input = null;
			var payload = FileSystem.stat(path).size - 16;
			return parseHeaderBytes(bytes, payload < 0 ? 0 : payload, path);
		} catch (error:Dynamic) {
			if (input != null)
				try input.close() catch (_:Dynamic) {}
			return invalidHeader(path, 'Could not read the ASTC header: ' + Std.string(error));
		}
	}

	/** Clear the process-level probe cache.  Tests and tools that change the
	 * environment between probes can opt into a fresh deterministic lookup. */
	public static function resetProbeCache():Void {
		cachedProbe = null;
		cachedProbeKey = null;
	}

	/** Discover and validate an astcenc executable without invoking a shell. */
	public static function probe(?workingDirectory:String):VSliceAstcProbe {
		var cacheKey = probeCacheKey(workingDirectory);
		if (cachedProbe != null && cachedProbeKey == cacheKey)
			return cachedProbe;
		var searched:Array<String> = [];
		for (candidate in decoderCandidates(workingDirectory)) {
			searched.push(candidate);
			var result = probeExecutable(candidate);
			if (result.available) {
				cachedProbe = {
					available: true,
					executable: candidate,
					reason: result.reason,
					searched: searched.copy()
				};
				cachedProbeKey = cacheKey;
				return cachedProbe;
			}
		}
		cachedProbe = {
			available: false,
			executable: '',
			reason: 'No usable astcenc executable was found. ' + DECODER_INSTALL_HINT,
		searched: searched
		};
		cachedProbeKey = cacheKey;
		return cachedProbe;
	}

	/** Decode one validated donor file to a new PNG.  Existing output files are
	 * never overwritten by this adapter. */
	public static function decodeFile(source:String, destination:String,
		?workingDirectory:String):VSliceAstcDecodeResult {
		var header = inspectFile(source);
		if (!header.valid)
			return failure('', 'Cannot decode ASTC source: ' + header.error, -1);
		if (!header.payloadMatches)
			return failure('', 'Cannot decode ASTC source: ' + header.error, -1);
		if (destination == null || destination.trim() == '')
			return failure('', 'ASTC conversion destination is empty.', -1);
		if (!destination.toLowerCase().endsWith('.png'))
			return failure('', 'ASTC conversion destination must end in .png: ' + destination, -1);
		if (FileSystem.exists(destination))
			return failure('', 'Refusing to overwrite existing ASTC conversion output: ' + destination, -1);

		var available = probe(workingDirectory);
		if (!available.available)
			return failure('', available.reason, -1);

		var process:Process = null;
		var exitCode = -1;
		var output = '';
		try {
			// Passing args separately is important: Haxe quotes/escapes each path for
			// the native process on both POSIX and Windows.  Do not concatenate a
			// command line or route this through `sh`/`cmd.exe`.
			process = new Process(available.executable, ['-ds', source, destination]);
			exitCode = process.exitCode(true);
			output = readProcessOutput(process);
			process.close();
			process = null;
		} catch (error:Dynamic) {
			if (process != null)
				try process.close() catch (_:Dynamic) {}
			removePartialOutput(destination);
			return failure(available.executable,
				'Could not run astcenc at ' + available.executable + ': ' + Std.string(error)
				+ '. ' + DECODER_INSTALL_HINT, -1);
		}
		if (exitCode != 0)
		{
			removePartialOutput(destination);
			return failure(available.executable,
				'astcenc failed with exit code ' + exitCode + ' for ' + source
				+ (output.trim() == '' ? '.' : ': ' + output.trim()), exitCode);
		}
		if (!FileSystem.exists(destination) || FileSystem.isDirectory(destination))
			return failure(available.executable,
				'astcenc reported success but did not create PNG output: ' + destination, exitCode);
		if (!isPngFile(destination)) {
			removePartialOutput(destination);
			return failure(available.executable,
				'astcenc reported success but output is not a PNG: ' + destination, exitCode);
		}
		return {success: true, executable: available.executable,
			message: 'Decoded ASTC to PNG.', exitCode: exitCode};
	}
	#end

	/** Stable, precise diagnostic text for importer scan results. */
	public static function diagnostic(path:String, ?header:VSliceAstcHeader):String {
		if (header != null && !header.valid)
			return 'V-Slice ASTC asset is invalid and cannot be converted: ' + path + ' (' + header.error + ')';
		if (header != null && !header.payloadMatches)
			return 'V-Slice ASTC asset has an invalid payload length and cannot be converted: ' + path
				+ ' (' + header.error + ')';
		if (header != null && header.valid)
			return 'V-Slice ASTC asset is valid ' + header.width + 'x' + header.height
				+ ' (' + header.blockX + 'x' + header.blockY + 'x' + header.blockZ
				+ ' blocks) but requires a portable decoder and no usable decoder was found: ' + path
				+ '. ' + DECODER_INSTALL_HINT;
		return 'V-Slice ASTC asset requires a portable decoder and no usable decoder was found: ' + path
			+ '. ' + DECODER_INSTALL_HINT;
	}

	static function parseHeaderBytes(bytes:Bytes, payloadBytes:Int, ?source:String):VSliceAstcHeader {
		var magic = bytes.get(0) | (bytes.get(1) << 8) | (bytes.get(2) << 16) | (bytes.get(3) << 24);
		if (magic != ASTC_MAGIC)
			return invalidHeader(source, 'Unexpected magic 0x' + StringTools.hex(magic, 8) + '.');
		var blockX = bytes.get(4);
		var blockY = bytes.get(5);
		var blockZ = bytes.get(6);
		var width = read24(bytes, 7);
		var height = read24(bytes, 10);
		var depth = read24(bytes, 13);
		if (blockX < 1 || blockX > 12 || blockY < 1 || blockY > 12 || blockZ < 1 || blockZ > 12)
			return invalidHeader(source, 'ASTC block dimensions are outside the 1..12 range.');
		if (width < 1 || height < 1 || depth < 1)
			return invalidHeader(source, 'ASTC image dimensions must be positive.');
		if (depth != 1)
			return invalidHeader(source, 'ASTC 3D images are not supported by the V-Slice 2D importer.');
		var blocksX:Float = Math.ceil(width / blockX);
		var blocksY:Float = Math.ceil(height / blockY);
		var blocksZ:Float = Math.ceil(depth / blockZ);
		var expected:Float = blocksX * blocksY * blocksZ * 16;
		var matches = expected == payloadBytes;
		var error = matches ? '' : 'Expected ' + Std.string(expected) + ' payload bytes after the 16-byte header, found ' + payloadBytes + '.';
		return {
			valid: true,
			source: source == null ? '' : source,
			width: width,
			height: height,
			depth: depth,
			blockX: blockX,
			blockY: blockY,
			blockZ: blockZ,
			payloadBytes: payloadBytes,
			expectedPayloadBytes: expected,
			payloadMatches: matches,
			error: error
		};
	}

	static function read24(bytes:Bytes, offset:Int):Int {
		return bytes.get(offset) | (bytes.get(offset + 1) << 8) | (bytes.get(offset + 2) << 16);
	}

	static function invalidHeader(?source:String, message:String):VSliceAstcHeader {
		return {
			valid: false,
			source: source == null ? '' : source,
			width: 0,
			height: 0,
			depth: 0,
			blockX: 0,
			blockY: 0,
			blockZ: 0,
			payloadBytes: 0,
			expectedPayloadBytes: 0,
			payloadMatches: false,
			error: message
		};
	}

	#if sys
	static function decoderCandidates(?workingDirectory:String):Array<String> {
		var result:Array<String> = [];
		var add = function(value:String):Void {
			if (value == null || value.trim() == '')
				return;
			var normalized = value;
			if (result.indexOf(normalized) < 0)
				result.push(normalized);
		};
		var configured = Sys.getEnv(DECODER_ENV);
		if (configured != null && configured.trim() != '')
			add(configured.trim());
		var cwd = workingDirectory == null || workingDirectory.trim() == '' ? Sys.getCwd() : workingDirectory;
		var localNames = ['astcenc', 'astcenc.exe', 'astcenc-avx2', 'astcenc-avx2.exe',
			'astcenc-sse4.1', 'astcenc-sse4.1.exe', 'astcenc-neon', 'astcenc-neon.exe'];
		// The importer is normally launched from export/<target>/bin, while a
		// developer run is often launched from the repository root.  Search a
		// small, deterministic set of runtime-local roots so a decoder supplied
		// beside the game or in the repository's tools/ directory works on both
		// POSIX and Windows.  We never recursively scan a donor or the filesystem.
		var roots:Array<String> = [];
		var addRoot = function(value:String):Void {
			if (value == null || value.trim() == '')
				return;
			var normalized = Path.normalize(value);
			if (roots.indexOf(normalized) < 0)
				roots.push(normalized);
		};
		addRoot(cwd);
		try {
			var program = Sys.programPath();
			if (program != null && program.trim() != '') {
				var programRoot = Path.directory(Path.normalize(program));
				addRoot(programRoot);
				// A release binary is commonly export/<target>/bin/Funkin;
				// walking only a few parents reaches the checkout's tools/ folder
				// without making an unbounded or donor-controlled search.
				for (_ in 0...4) {
					var parent = Path.directory(programRoot);
					if (parent == null || parent == programRoot || parent.trim() == '')
						break;
					programRoot = parent;
					addRoot(programRoot);
				}
			}
		} catch (_:Dynamic) {}
		for (root in roots) {
			for (name in localNames) {
				add(Path.normalize(Path.join([root, 'tools', name])));
				// The repository's development toolchain keeps the pinned decoder in
				// `.tools/astcenc`, while a packaged game keeps it beside the binary
				// in `tools/`.  Probe both roots so read-only importer scans launched
				// from the checkout plan the same ASTC mappings as the game runtime.
				add(Path.normalize(Path.join([root, '.tools', 'astcenc', name])));
				add(Path.normalize(Path.join([root, name])));
			}
		}
		// Bare allow-listed names let Process resolve a decoder supplied by PATH.
		// They are never concatenated into a shell command.
		for (name in localNames)
			add(name);
		return result;
	}

	static function probeCacheKey(?workingDirectory:String):String {
		var cwd = workingDirectory == null || workingDirectory.trim() == '' ? Sys.getCwd() : workingDirectory;
		var configured = Sys.getEnv(DECODER_ENV);
		var pathEnv = Sys.getEnv('PATH');
		var program = '';
		try program = Sys.programPath() catch (_:Dynamic) {}
		return Path.normalize(cwd) + '\n' + Path.normalize(program == null ? '' : program)
			+ '\n' + (configured == null ? '' : configured.trim())
			+ '\n' + (pathEnv == null ? '' : pathEnv);
	}

	static function probeExecutable(command:String):Dynamic {
		var lower = command == null ? '' : command.toLowerCase();
		if (command == null || command.trim() == '')
			return {available: false, reason: 'Empty decoder candidate.'};
		// A configured/local path must be a file. Bare names are allowed so the
		// native process API can resolve them from PATH.
		var isBare = command.indexOf('/') < 0 && command.indexOf('\\') < 0 && command.indexOf(':') < 0;
		if (!isBare && (!FileSystem.exists(command) || FileSystem.isDirectory(command)))
			return {available: false, reason: 'Decoder candidate does not exist.'};
		for (args in [['--version'], ['-v'], ['-help']]) {
			var process:Process = null;
			try {
				process = new Process(command, args);
				var exitCode = process.exitCode(true);
				var output = readProcessOutput(process);
				process.close();
				process = null;
				var text = output.toLowerCase();
				if (exitCode == 0 && (text.indexOf('astc') >= 0 || lower.indexOf('astcenc') >= 0))
					return {available: true, reason: 'Validated astcenc executable.'};
			} catch (_:Dynamic) {
				if (process != null)
					try process.close() catch (_:Dynamic) {}
			}
		}
		return {available: false, reason: 'Decoder candidate could not be validated.'};
	}

	static function readProcessOutput(process:Process):String {
		var output = '';
		try output += process.stdout.readAll().toString() catch (_:Dynamic) {}
		try output += process.stderr.readAll().toString() catch (_:Dynamic) {}
		return output;
	}

	static function removePartialOutput(path:String):Void {
		if (path == null || path.trim() == '' || !FileSystem.exists(path) || FileSystem.isDirectory(path))
			return;
		try FileSystem.deleteFile(path) catch (_:Dynamic) {}
	}

	static function isPngFile(path:String):Bool {
		var input:haxe.io.Input = null;
		try {
			input = File.read(path, true);
			var header = input.read(24);
			input.close();
			input = null;
			// A decoder that only writes the eight-byte signature is not a usable
			// image. Require the fixed signature plus a complete IHDR header so a
			// successful process cannot make the importer claim a fake PNG.
			if (header.length < 24)
				return false;
			var expected = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
			for (i in 0...expected.length)
				if (header.get(i) != expected[i])
					return false;
			// PNG stores the IHDR chunk length as a big-endian u32 at byte 8 and
			// the chunk type at byte 12.
			if (header.get(8) != 0 || header.get(9) != 0 || header.get(10) != 0 || header.get(11) != 13)
				return false;
			return header.get(12) == 0x49 && header.get(13) == 0x48
				&& header.get(14) == 0x44 && header.get(15) == 0x52;
		} catch (_:Dynamic) {
			if (input != null)
				try input.close() catch (_:Dynamic) {}
			return false;
		}
	}

	static function failure(executable:String, message:String, exitCode:Int):VSliceAstcDecodeResult {
		return {success: false, executable: executable == null ? '' : executable,
			message: message, exitCode: exitCode};
	}
	#end
}
