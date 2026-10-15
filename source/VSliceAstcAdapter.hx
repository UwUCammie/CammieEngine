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

		// astcenc writes with plain C file calls, which fail on Windows once a
		// path reaches 260 characters; deep import stages get there. It then
		// writes a short temporary file that this process moves into place.
		var output = longPathTarget(destination) ? shortTemporaryPng() : destination;
		var decoded = runDecoder(available.executable, source, output);
		if (decoded.success && output != destination) {
			try {
				File.copy(output, destination);
			} catch (error:Dynamic) {
				decoded = failure(available.executable,
					'Could not move the decoded PNG into ' + destination + ': ' + Std.string(error), decoded.exitCode);
			}
			removePartialOutput(output);
			if (!decoded.success)
				removePartialOutput(destination);
		}
		return decoded;
	}

	/** One astcenc run writing `output`, which is checked to be a real PNG. */
	static function runDecoder(executable:String, source:String, output:String):VSliceAstcDecodeResult {
		var process:Process = null;
		var exitCode = -1;
		var text = '';
		try {
			// Passing args separately is important: Haxe quotes/escapes each path for
			// the native process on both POSIX and Windows.  Do not concatenate a
			// command line or route this through `sh`/`cmd.exe`.
			process = new Process(executable, ['-ds', source, output]);
			exitCode = process.exitCode(true);
			text = readProcessOutput(process);
			process.close();
			process = null;
		} catch (error:Dynamic) {
			if (process != null)
				try process.close() catch (_:Dynamic) {}
			removePartialOutput(output);
			return failure(executable,
				'Could not run astcenc at ' + executable + ': ' + Std.string(error)
				+ '. ' + DECODER_INSTALL_HINT, -1);
		}
		if (exitCode != 0)
		{
			removePartialOutput(output);
			return failure(executable,
				'astcenc failed with exit code ' + exitCode + ' for ' + source
				+ (text.trim() == '' ? '.' : ': ' + text.trim()), exitCode);
		}
		if (!FileSystem.exists(output) || FileSystem.isDirectory(output))
			return failure(executable,
				'astcenc reported success but did not create PNG output: ' + output, exitCode);
		if (!isPngFile(output)) {
			removePartialOutput(output);
			return failure(executable,
				'astcenc reported success but output is not a PNG: ' + output, exitCode);
		}
		return {success: true, executable: executable,
			message: 'Decoded ASTC to PNG.', exitCode: exitCode};
	}

	/** Leaves room under Windows' 260 character limit for the decoder's own work. */
	public static function longPathTarget(path:String):Bool {
		return path != null && FileSystem.absolutePath(path).length >= 240;
	}

	static var temporaryCounter:Int = 0;

	/** A fresh PNG path in the system temporary folder, which is always short. */
	static function shortTemporaryPng():String {
		var folder = Sys.getEnv('TEMP');
		if (folder == null || folder == '') folder = Sys.getEnv('TMPDIR');
		if (folder == null || folder == '') folder = '/tmp';
		temporaryCounter++;
		// Milliseconds since the epoch overflow a 32-bit Int, so only their low
		// part is kept, taken while still a Float.
		var stamp = Std.int((Sys.time() * 1000) % 100000000);
		return Path.join([folder, 'cammie-astc-' + stamp + '-' + temporaryCounter + '-' + Std.random(1000000) + '.png']);
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

/** Facts read from one DDS header. */
typedef DdsTextureHeader = {
	var valid:Bool;
	var width:Int;
	var height:Int;
	/** 'BC1', 'BC2', 'BC3', 'RGBA32', 'BGRA32', 'RGB24' or '' when unsupported. */
	var format:String;
	var dataOffset:Int;
	/** Bytes per pixel row for RGB24; 0 for every other format. */
	var rowPitch:Int;
	var error:String;
}

/** Result of one DDS to PNG conversion. */
typedef DdsTextureDecodeResult = {
	var success:Bool;
	var message:String;
}

/**
	Reads DirectDraw Surface textures and writes them as PNG.

	Some V-Slice builds ship sprite sheets as DDS files (block compressed
	DXT1, DXT3 or DXT5, or plain 32/24-bit pixels) next to their Sparrow XML.
	Lime cannot load DDS, so the importer converts the first mip level to an
	ordinary PNG once, at import time, the same way ASTC sheets are turned
	into PNG. Nothing here runs during gameplay. It lives in this module so
	every tool that already carries the ASTC boundary carries this one too.
*/
class DdsTextureDecoder {
	static inline var HEADER_BYTES:Int = 128;
	static inline var DX10_HEADER_BYTES:Int = 20;
	static inline var DDPF_ALPHAPIXELS:Int = 0x1;
	static inline var DDPF_FOURCC:Int = 0x4;
	static inline var DDPF_RGB:Int = 0x40;
	static inline var DDSD_PITCH:Int = 0x8;
	/** Larger than any texture the game can upload; guards a corrupt header. */
	static inline var MAX_SIDE:Int = 16384;

	/** Parse the header of a complete DDS file held in memory. */
	public static function parseHeader(bytes:Bytes):DdsTextureHeader {
		return parseHeaderFields(bytes, bytes == null ? 0 : bytes.length);
	}

	/** Parse the header bytes of a DDS file whose full size is `fileLength`. */
	static function parseHeaderFields(bytes:Bytes, fileLength:Int):DdsTextureHeader {
		if (bytes == null || bytes.length < HEADER_BYTES)
			return invalid('file is shorter than a DDS header');
		if (bytes.getString(0, 4) != 'DDS ' || bytes.getInt32(4) != 124)
			return invalid('missing DDS signature');
		var height = bytes.getInt32(12);
		var width = bytes.getInt32(16);
		if (width <= 0 || height <= 0 || width > MAX_SIDE || height > MAX_SIDE)
			return invalid('unsupported size ' + width + 'x' + height);
		var pixelFlags = bytes.getInt32(80);
		var fourCC = bytes.getString(84, 4);
		var offset = HEADER_BYTES;
		var format = '';
		if (pixelFlags & DDPF_FOURCC != 0) {
			switch (fourCC) {
				case 'DXT1': format = 'BC1';
				case 'DXT2' | 'DXT3': format = 'BC2';
				case 'DXT4' | 'DXT5': format = 'BC3';
				case 'DX10':
					if (bytes.length < HEADER_BYTES + DX10_HEADER_BYTES)
						return invalid('truncated DX10 header');
					offset += DX10_HEADER_BYTES;
					format = switch (bytes.getInt32(HEADER_BYTES)) {
						case 70 | 71 | 72: 'BC1';
						case 73 | 74 | 75: 'BC2';
						case 76 | 77 | 78: 'BC3';
						case 27 | 28 | 29: 'RGBA32';
						case 87 | 90 | 91: 'BGRA32';
						default: '';
					};
				default:
			}
			if (format == '')
				return invalid('unsupported compression ' + fourCC);
		} else if (pixelFlags & DDPF_RGB != 0) {
			var bits = bytes.getInt32(88);
			var redMask = bytes.getInt32(92);
			var hasAlpha = pixelFlags & DDPF_ALPHAPIXELS != 0;
			if (bits == 32 && redMask == 0x000000ff)
				format = hasAlpha ? 'RGBA32' : 'RGBX32';
			else if (bits == 32 && redMask == 0x00ff0000)
				format = hasAlpha ? 'BGRA32' : 'BGRX32';
			else if (bits == 24 && redMask == 0x00ff0000)
				format = 'RGB24';
			if (format == '')
				return invalid('unsupported ' + bits + '-bit pixel layout');
		} else
			return invalid('unsupported pixel format');
		var rowPitch = format == 'RGB24' ? rgb24RowPitch(bytes, width) : 0;
		var needed = offset + payloadBytes(format, width, height, rowPitch);
		if (fileLength < needed)
			return invalid('pixel data is truncated');
		return {valid: true, width: width, height: height, format: format, dataOffset: offset, rowPitch: rowPitch,
			error: ''};
	}

	/**
		Row length of a 24-bit surface. The DDS rule is tightly packed rows
		(width * 3 bytes); some older writers pad each row to whole 32-bit words
		and say so in the header's pitch field, so an authored pitch within that
		padding is used as written.
	*/
	static function rgb24RowPitch(bytes:Bytes, width:Int):Int {
		var packed = width * 3;
		var authored = bytes.getInt32(20);
		if (bytes.getInt32(8) & DDSD_PITCH != 0 && authored >= packed && authored <= packed + 3)
			return authored;
		return packed;
	}

	/** Decode the first mip level to straight RGBA bytes, row by row. */
	public static function decodeRgba(bytes:Bytes, header:DdsTextureHeader):Bytes {
		if (header == null || !header.valid)
			return null;
		var width = header.width;
		var height = header.height;
		var out = Bytes.alloc(width * height * 4);
		var at = header.dataOffset;
		switch (header.format) {
			case 'BC1' | 'BC2' | 'BC3':
				// Format checks hoisted out of the per-pixel loop: a 4096 square
				// sheet is sixteen million pixels.
				var isBc1 = header.format == 'BC1';
				var isBc2 = header.format == 'BC2';
				var blockBytes = isBc1 ? 8 : 16;
				var colors = new haxe.ds.Vector<Int>(4);
				var alphas = new haxe.ds.Vector<Int>(16);
				var by = 0;
				while (by < height) {
					var bx = 0;
					while (bx < width) {
						var colorAt = at;
						if (isBc2) {
							for (i in 0...16) {
								var nibble = (bytes.get(at + (i >> 1)) >> ((i & 1) * 4)) & 0xF;
								alphas[i] = nibble * 17;
							}
							colorAt = at + 8;
						} else if (!isBc1) {
							readInterpolatedAlpha(bytes, at, alphas);
							colorAt = at + 8;
						}
						readBlockColors(bytes, colorAt, colors, isBc1);
						var indices = bytes.getInt32(colorAt + 4);
						for (py in 0...4) {
							var y = by + py;
							if (y >= height)
								break;
							for (px in 0...4) {
								var x = bx + px;
								if (x >= width)
									continue;
								var pixel = py * 4 + px;
								var color = colors[(indices >>> (pixel * 2)) & 3];
								var o = (y * width + x) * 4;
								out.set(o, (color >> 16) & 0xFF);
								out.set(o + 1, (color >> 8) & 0xFF);
								out.set(o + 2, color & 0xFF);
								out.set(o + 3, isBc1 ? (color >>> 24) & 0xFF : alphas[pixel]);
							}
						}
						at += blockBytes;
						bx += 4;
					}
					by += 4;
				}
			case 'RGBA32' | 'RGBX32' | 'BGRA32' | 'BGRX32':
				var swap = header.format.charAt(0) == 'B';
				var opaque = header.format.charAt(3) == 'X';
				for (i in 0...(width * height)) {
					var s = at + i * 4;
					var o = i * 4;
					out.set(o, bytes.get(s + (swap ? 2 : 0)));
					out.set(o + 1, bytes.get(s + 1));
					out.set(o + 2, bytes.get(s + (swap ? 0 : 2)));
					out.set(o + 3, opaque ? 255 : bytes.get(s + 3));
				}
			case 'RGB24':
				var pitch = header.rowPitch > 0 ? header.rowPitch : width * 3;
				for (y in 0...height)
					for (x in 0...width) {
						var s = at + y * pitch + x * 3;
						var o = (y * width + x) * 4;
						out.set(o, bytes.get(s + 2));
						out.set(o + 1, bytes.get(s + 1));
						out.set(o + 2, bytes.get(s));
						out.set(o + 3, 255);
					}
			default:
				return null;
		}
		return out;
	}

	/** Encode straight RGBA rows as an 8-bit RGBA PNG. */
	public static function encodePng(rgba:Bytes, width:Int, height:Int):Bytes {
		var raw = Bytes.alloc((width * 4 + 1) * height);
		var stride = width * 4;
		for (y in 0...height) {
			// Filter type 0 (None) keeps the encoder simple; zlib still compresses
			// the flat areas sprite sheets are mostly made of.
			raw.set(y * (stride + 1), 0);
			raw.blit(y * (stride + 1) + 1, rgba, y * stride, stride);
		}
		var output = new haxe.io.BytesOutput();
		output.bigEndian = true;
		for (b in [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
			output.writeByte(b);
		var ihdr = Bytes.alloc(13);
		writeBigEndian(ihdr, 0, width);
		writeBigEndian(ihdr, 4, height);
		ihdr.set(8, 8);
		ihdr.set(9, 6);
		ihdr.set(10, 0);
		ihdr.set(11, 0);
		ihdr.set(12, 0);
		writeChunk(output, 'IHDR', ihdr);
		writeChunk(output, 'IDAT', haxe.zip.Compress.run(raw, 6));
		writeChunk(output, 'IEND', Bytes.alloc(0));
		return output.getBytes();
	}

	#if sys
	/** Convert one DDS file to a PNG at `destination`, leaving no partial file. */
	public static function decodeFile(source:String, destination:String):DdsTextureDecodeResult {
		var header:DdsTextureHeader = null;
		try {
			var bytes = File.getBytes(source);
			header = parseHeader(bytes);
			if (!header.valid)
				return {success: false, message: 'DDS texture ' + source + ' cannot be converted: ' + header.error};
			var rgba = decodeRgba(bytes, header);
			if (rgba == null)
				return {success: false, message: 'DDS texture ' + source + ' cannot be converted: unsupported ' + header.format};
			var temporary = destination + '.dds-convert.tmp';
			File.saveBytes(temporary, encodePng(rgba, header.width, header.height));
			if (FileSystem.exists(destination))
				FileSystem.deleteFile(destination);
			FileSystem.rename(temporary, destination);
			return {success: true, message: ''};
		} catch (error:Dynamic) {
			try {
				if (FileSystem.exists(destination + '.dds-convert.tmp'))
					FileSystem.deleteFile(destination + '.dds-convert.tmp');
			} catch (_:Dynamic) {}
			return {success: false, message: 'DDS texture ' + source + ' cannot be converted: ' + Std.string(error)};
		}
	}

	/** Header facts of a DDS file on disk, reading only the header bytes. */
	public static function inspectFile(path:String):DdsTextureHeader {
		try {
			var input = File.read(path, true);
			var length = FileSystem.stat(path).size;
			var head = Bytes.alloc(Std.int(Math.min(length, HEADER_BYTES + DX10_HEADER_BYTES)));
			input.readFullBytes(head, 0, head.length);
			input.close();
			return parseHeaderFields(head, length);
		} catch (error:Dynamic) {
			return invalid(Std.string(error));
		}
	}
	#end

	/** True when the extension names a DDS texture. */
	public static function isDdsPath(path:String):Bool {
		return path != null && StringTools.endsWith(path.toLowerCase(), '.dds');
	}

	static function payloadBytes(format:String, width:Int, height:Int, rowPitch:Int):Int {
		var blocks = ((width + 3) >> 2) * ((height + 3) >> 2);
		return switch (format) {
			case 'BC1': blocks * 8;
			case 'BC2' | 'BC3': blocks * 16;
			case 'RGB24': rowPitch * height;
			default: width * height * 4;
		};
	}

	/** Fill `colors` with the four ARGB colours of one BC1 colour block. */
	static function readBlockColors(bytes:Bytes, at:Int, colors:haxe.ds.Vector<Int>, allowTransparent:Bool):Void {
		var c0 = bytes.getUInt16(at);
		var c1 = bytes.getUInt16(at + 2);
		var r0 = expand5(c0 >> 11), g0 = expand6((c0 >> 5) & 63), b0 = expand5(c0 & 31);
		var r1 = expand5(c1 >> 11), g1 = expand6((c1 >> 5) & 63), b1 = expand5(c1 & 31);
		colors[0] = argb(255, r0, g0, b0);
		colors[1] = argb(255, r1, g1, b1);
		// DXT3 and DXT5 always use the four-colour mode; only DXT1 has the
		// three-colour plus transparent mode when c0 <= c1.
		if (c0 > c1 || !allowTransparent) {
			colors[2] = argb(255, Std.int((2 * r0 + r1) / 3), Std.int((2 * g0 + g1) / 3), Std.int((2 * b0 + b1) / 3));
			colors[3] = argb(255, Std.int((r0 + 2 * r1) / 3), Std.int((g0 + 2 * g1) / 3), Std.int((b0 + 2 * b1) / 3));
		} else {
			colors[2] = argb(255, (r0 + r1) >> 1, (g0 + g1) >> 1, (b0 + b1) >> 1);
			colors[3] = 0;
		}
	}

	/** Fill `alphas` with the sixteen alpha values of one BC3 alpha block. */
	static function readInterpolatedAlpha(bytes:Bytes, at:Int, alphas:haxe.ds.Vector<Int>):Void {
		var a0 = bytes.get(at);
		var a1 = bytes.get(at + 1);
		// 48 bits of 3-bit indices, read as two 24-bit halves so no 64-bit math is needed.
		var low = bytes.get(at + 2) | (bytes.get(at + 3) << 8) | (bytes.get(at + 4) << 16);
		var high = bytes.get(at + 5) | (bytes.get(at + 6) << 8) | (bytes.get(at + 7) << 16);
		for (i in 0...16) {
			var code = i < 8 ? (low >> (i * 3)) & 7 : (high >> ((i - 8) * 3)) & 7;
			alphas[i] = if (code == 0) a0 else if (code == 1) a1 else if (a0 > a1)
				Std.int(((8 - code) * a0 + (code - 1) * a1) / 7)
			else if (code == 6) 0 else if (code == 7) 255 else
				Std.int(((6 - code) * a0 + (code - 1) * a1) / 5);
		}
	}

	static inline function expand5(value:Int):Int
		return (value << 3) | (value >> 2);

	static inline function expand6(value:Int):Int
		return (value << 2) | (value >> 4);

	static inline function argb(a:Int, r:Int, g:Int, b:Int):Int
		return (a << 24) | (r << 16) | (g << 8) | b;

	static function writeBigEndian(bytes:Bytes, at:Int, value:Int):Void {
		bytes.set(at, (value >>> 24) & 0xFF);
		bytes.set(at + 1, (value >>> 16) & 0xFF);
		bytes.set(at + 2, (value >>> 8) & 0xFF);
		bytes.set(at + 3, value & 0xFF);
	}

	static function writeChunk(output:haxe.io.BytesOutput, type:String, data:Bytes):Void {
		output.writeInt32(data.length);
		var typed = Bytes.alloc(4 + data.length);
		typed.blit(0, Bytes.ofString(type), 0, 4);
		typed.blit(4, data, 0, data.length);
		output.writeFullBytes(typed, 0, typed.length);
		output.writeInt32(haxe.crypto.Crc32.make(typed));
	}

	static function invalid(error:String):DdsTextureHeader {
		return {valid: false, width: 0, height: 0, format: '', dataOffset: 0, rowPitch: 0, error: error};
	}
}
