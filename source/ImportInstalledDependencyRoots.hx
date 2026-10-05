package;

import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
import ImportFileSystem as FileSystem;
import ImportFile as File;

typedef ImportInstalledDependencyProvider = {var root:String; var owner:String; var engine:String;}
typedef ImportInstalledDependencyResolution = {
	var providers:Array<ImportInstalledDependencyProvider>;
	var diagnostics:Array<String>;
}

/** Read-only relationship inference from committed retained imports. Matching
 * an entire distinctive cast and missing stage is required; siblings and
 * unrelated installed namespaces are never searched as fallback libraries. */
class ImportInstalledDependencyRoots {
	static inline var MAX_RECORDS:Int = 256;
	static inline var MAX_METADATA_BYTES:Int = 16 * 1024 * 1024;
	var metadataRemaining:Int = 64 * 1024 * 1024;
	function new() {}

	public static function resolve(sourceRoot:String, engine:String, chart:Dynamic):ImportInstalledDependencyResolution {
		return new ImportInstalledDependencyRoots().scan(sourceRoot, engine, chart);
	}

	function scan(sourceRoot:String, engine:String, chart:Dynamic):ImportInstalledDependencyResolution {
		var result:ImportInstalledDependencyResolution = {providers:[], diagnostics:[]};
		var dialect = ImportRevision.normalizeEngine(engine);
		if (dialect != ImportEngine.PSYCH && dialect != ImportEngine.NIGHTMARE_VISION) return result;
		var song = chart == null ? null : Reflect.field(chart, 'song');
		if (song == null || Std.isOfType(song, String)) song = chart;
		if (song == null || sourceRoot == null) return result;
		var stage = stringField(song, 'stage');
		if (!safeRelative(stage, false)) return result;
		var actors:Array<String> = [];
		var girlfriend = stringField(song, 'gfVersion');
		if (girlfriend == '' && dialect == ImportEngine.NIGHTMARE_VISION) girlfriend = stringField(song, 'player3');
		if (girlfriend == '') girlfriend = stringField(song, 'gf');
		for (actor in [stringField(song, 'player1'), stringField(song, 'player2'), girlfriend]) {
			if (actor == '' || builtin(actor)) continue;
			if (!safeRelative(actor, false)) return result;
			if (actors.indexOf(actor) < 0) actors.push(actor);
		}
		if (actors.length == 0 || stageImplemented(sourceRoot, stage, dialect)) return result;
		var context = ImportIO.current();
		var install = context == null ? Sys.getCwd() : context.installRoot;
		try {
			install = canonical(install);
			var currentSource = canonical(sourceRoot);
			var currentOwner = CompatScriptManifest.destinationRoot(sourceRoot, dialect);
			var cache = safeChild(install, 'import-cache');
			var records = safeChild(cache, 'records');
			if (!FileSystem.exists(records) || !FileSystem.isDirectory(records)) return result;
			var entries = FileSystem.readDirectory(records);
			entries.sort(Reflect.compare);
			if (entries.length > MAX_RECORDS) {
				result.diagnostics.push('[installed-dependency-limit] Retained record bound exceeded; no provider selected.');
				return result;
			}
			var seen:Map<String, Bool> = new Map();
			for (entry in entries) {
				if (!~/^[a-f0-9]{64}\.json$/.match(entry)) continue;
				try {
					var pointer = readJson(safeChild(records, entry));
					var id = stringField(pointer, 'id');
					if (id + '.json' != entry) continue;
					var manifestRoot = safeChild(cache, 'state/' + digest('retained-import:' + id));
					var manifestPath = safeChild(manifestRoot, 'manifest.json');
					var manifestText = readText(manifestPath);
					var manifest:Dynamic = haxe.Json.parse(manifestText);
					var ownerId = 'retained-import:' + id;
					if (Reflect.field(manifest, 'schemaVersion') != 1 || stringField(manifest, 'owner') != ownerId) continue;
					var transaction = stringField(manifest, 'transactionId');
					if (!safeRelative(transaction, false) || transaction.indexOf('/') >= 0) continue;
					var commit = readJson(safeChild(manifestRoot, 'transactions/' + transaction + '/receipt.json'));
					if (stringField(commit, 'status') != 'applied' || stringField(commit, 'owner') != ownerId
						|| stringField(commit, 'transactionId') != transaction
						|| stringField(commit, 'manifestSha256') != digest(manifestText)) continue;
					var revision = Reflect.field(manifest, 'revision');
					var record = revision == null ? null : Reflect.field(revision, 'importRecord');
					var snapshot = stringField(record, 'snapshotId');
					if (stringField(record, 'id') != id || !~/^[a-f0-9]{64}$/.match(snapshot)
						|| stringField(record, 'source') != 'sources/' + snapshot + '/content') continue;
					var snapshotRoot = safeChild(cache, 'sources/' + snapshot);
					var snapshotReceipt = readJson(safeChild(snapshotRoot, 'receipt.json'));
					var reasons:Dynamic = Reflect.field(snapshotReceipt, 'incompleteReasons');
					if (Reflect.field(snapshotReceipt, 'snapshotSchemaVersion') != 2
						|| stringField(snapshotReceipt, 'snapshotId') != snapshot
						|| !Std.isOfType(reasons, Array) || (cast reasons:Array<Dynamic>).length != 0) continue;
					var content = safeChild(snapshotRoot, 'content');
					var roots:Dynamic = Reflect.field(record, 'roots');
					if (!Std.isOfType(roots, Array) || (cast roots:Array<Dynamic>).length > MAX_RECORDS) continue;
					for (declared in (cast roots:Array<Dynamic>)) {
						if (ImportRevision.normalizeEngine(stringField(declared, 'engine')) != dialect) continue;
						var relative = stringField(declared, 'relative');
						var namespace = stringField(declared, 'namespace');
						if (!safeRelative(relative, true) || !safeRelative(namespace, false) || namespace.indexOf('/') >= 0) continue;
						var root = relative == '' ? content : safeChild(content, relative);
						var owner = 'assets/imported_mods/' + namespace;
						if (same(root, currentSource) || same(owner, currentOwner)) continue;
						var installedOwner = safeChild(install, owner);
						if (!FileSystem.isDirectory(root) || !FileSystem.isDirectory(installedOwner)
							|| !stageImplemented(root, stage, dialect) || !stageImplemented(installedOwner, stage, dialect)) continue;
						var suppliesAll = true;
						for (actor in actors) if (!definesCharacter(root, actor, dialect)
							|| !definesCharacter(installedOwner, actor, dialect)) {suppliesAll = false; break;}
						if (!suppliesAll || seen.exists(owner)) continue;
						seen.set(owner, true);
						result.providers.push({root:root, owner:owner, engine:dialect});
					}
				} catch (_:Dynamic) {}
			}
			if (metadataRemaining < 0) {
				result.providers = [];
				result.diagnostics.push('[installed-dependency-limit] Metadata budget exceeded; no provider selected.');
			} else if (result.providers.length > 1) {
				result.providers = [];
				result.diagnostics.push('[installed-dependency-ambiguous] Multiple committed owners supply the entire cast and stage; no provider selected.');
			}
		} catch (_:Dynamic) {
			result.providers = [];
			result.diagnostics.push('[installed-dependency-unavailable] Retained dependency metadata could not be safely inspected.');
		}
		return result;
	}

	function definesCharacter(root:String, actor:String, engine:String):Bool {
		for (prefix in (engine == ImportEngine.PSYCH ? ['characters/'] : ['data/characters/', 'characters/']))
			try {
				var definition = readJson(safeChild(root, prefix + actor + '.json'));
				if (definition != null && stringField(definition, 'image') != ''
					&& Std.isOfType(Reflect.field(definition, 'animations'), Array)) return true;
			} catch (_:Dynamic) {}
		return false;
	}

	function stageImplemented(root:String, stage:String, engine:String):Bool {
		if (!safeRelative(stage, false)) return false;
		var paths = engine == ImportEngine.PSYCH ? ['stages/' + stage + '.lua', 'stages/' + stage + '.hx']
			: ['data/stages/' + stage + '/script.hx', 'stages/' + stage + '.hx'];
		for (relative in paths) try {
			if (StringTools.trim(readText(safeChild(root, relative))) != '') return true;
		} catch (_:Dynamic) {}
		return false;
	}

	static function builtin(name:String):Bool {
		return ['bf','boyfriend','dad','daddy','gf','girlfriend','no-gf','nogf','no_gf',
			'bf-car','bf-christmas','bf-pixel','bf-pixel-dead','bf-dead','gf-car','gf-christmas','gf-pixel','gf-tankmen',
			'spooky','pico','mom','mom-car','parents-christmas','monster','monster-christmas','senpai','senpai-angry','spirit','tankman']
			.indexOf(name.toLowerCase()) >= 0;
	}
	function readJson(path:String):Dynamic return haxe.Json.parse(readText(path));
	function readText(path:String):String {
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_METADATA_BYTES) throw 'Invalid metadata';
		var size = FileSystem.stat(path).size;
		if (size > metadataRemaining) {metadataRemaining = -1; throw 'Dependency metadata budget exceeded';}
		metadataRemaining -= size;
		return File.getContent(path);
	}
	static function stringField(value:Dynamic, name:String):String {
		var field = value == null ? null : Reflect.field(value, name);
		return Std.isOfType(field, String) ? StringTools.trim(cast field) : '';
	}
	static function digest(text:String):String return Sha256.make(Bytes.ofString(text)).toHex();
	static function safeRelative(path:String, allowEmpty:Bool):Bool {
		if (path == '') return allowEmpty;
		if (Path.isAbsolute(path) || path.indexOf(':') >= 0 || path.indexOf('\\') >= 0 || path.indexOf('\x00') >= 0) return false;
		for (part in path.split('/')) if (part == '' || part == '.' || part == '..') return false;
		return true;
	}
	static function canonical(path:String):String return Path.normalize(StringTools.replace(FileSystem.fullPath(path), '\\', '/'));
	static function same(a:String, b:String):Bool {
		#if windows
		return a.toLowerCase() == b.toLowerCase();
		#else
		return a == b;
		#end
	}
	static function safeChild(root:String, relative:String):String {
		if (!safeRelative(relative, false)) throw 'Unsafe relative path';
		var current = root;
		for (part in relative.split('/')) {
			current = Path.join([current, part]);
			if (!FileSystem.exists(current)) continue;
			var expected = Path.normalize(StringTools.replace(FileSystem.absolutePath(current), '\\', '/'));
			if (!same(canonical(current), expected)) throw 'Symlink or redirected dependency path';
			var context = ImportIO.current();
			// Resolve only the existing physical read target. Virtual output paths
			// remain lexical, so staged removals and missing destinations stay hidden.
			var physical = context == null ? current : context.readPath(current);
			var absolute = Path.normalize(StringTools.replace(sys.FileSystem.absolutePath(physical), '\\', '/'));
			var resolved = CompatCanonicalPath.resolve(physical);
			if (resolved == null || !same(absolute, resolved)) throw 'Symlink dependency read target';
			if ((FileSystem.stat(current).mode & 0xF000) == 0xA000) throw 'Symlink dependency path';
		}
		return current;
	}
}
