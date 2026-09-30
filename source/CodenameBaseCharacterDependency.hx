package;

import haxe.crypto.Sha256;
import haxe.Json;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef CodenameBaseCharacterAsset = {
	var source:String;
	var sourceRelative:String;
	var destinationRelative:String;
	var digest:String;
}

typedef CodenameBaseCharacterDependencyPlan = {
	var fallbackId:String;
	var sprite:String;
	var xmlText:String;
	var files:Array<CodenameBaseCharacterAsset>;
	var diagnostic:Null<String>;
}

typedef CodenameBaseCharacterDependencyResult = {
	var copied:Int;
	var skipped:Int;
	var failed:Bool;
	var diagnostic:Null<String>;
}

typedef CodenameBaseCharacterDependencyResolution = {
	var definitionId:String;
	var xmlText:String;
	var assetRoot:String;
	var assetFiles:Array<String>;
	var diagnostic:Null<String>;
}

typedef CodenameBaseCharacterReceiptFile = {
	var sourceRelative:String;
	var destinationRelative:String;
	var digest:String;
}

typedef CodenameBaseCharacterReceipt = {
	var version:Int;
	var ownerNamespace:String;
	var fallbackId:String;
	var sprite:String;
	var files:Array<CodenameBaseCharacterReceiptFile>;
}

/**
	A narrowly scoped copy of Codename's trusted installation DEFAULT_CHARACTER.
	The caller may supply an engine asset root only when import discovery found it
	as part of the selected compiled installation. The dependency is materialized
	under that song owner's namespace; it never searches sibling mod owners.
*/
class CodenameBaseCharacterDependency {
	public static inline var RELATIVE_ROOT:String = 'compat-engine-base';
	public static inline var RECEIPT_NAME:String = 'character-dependency.json';
	static inline var VERSION:Int = 2;

	public static function plan(engineAssetRoot:String, fallbackId:String):CodenameBaseCharacterDependencyPlan {
		var result:CodenameBaseCharacterDependencyPlan = {
			fallbackId:fallbackId, sprite:fallbackId, xmlText:null, files:[], diagnostic:null
		};
		#if sys
		if (engineAssetRoot == null || !FileSystem.isDirectory(engineAssetRoot))
			return failPlan(result, 'selected Codename installation asset root is unavailable');
		if (!CodenameScriptDiscovery.safeRelativeName(fallbackId))
			return failPlan(result, 'unsafe Codename DEFAULT_CHARACTER id: ' + Std.string(fallbackId));
		var xmlRelative = CodenameScriptDiscovery.resolveScopedRelative(engineAssetRoot,
			'data/characters/' + fallbackId + '.xml');
		if (xmlRelative == null)
			return failPlan(result, 'installation DEFAULT_CHARACTER XML is unavailable: ' + fallbackId);
		var xmlPath = Path.join([engineAssetRoot, xmlRelative]);
		try result.xmlText = File.getContent(xmlPath) catch (error:Dynamic)
			return failPlan(result, 'installation DEFAULT_CHARACTER XML could not be read: '
				+ xmlRelative + ' (' + Std.string(error) + ')');
		var document:Xml;
		try document = Xml.parse(result.xmlText).firstElement() catch (_:Dynamic)
			return failPlan(result, 'installation DEFAULT_CHARACTER XML is invalid: ' + xmlRelative);
		if (document == null || document.nodeType != Xml.Element || document.nodeName != 'character')
			return failPlan(result, 'installation DEFAULT_CHARACTER XML has no character root: ' + xmlRelative);
		var sprite = document.get('sprite');
		if (sprite == null || StringTools.trim(sprite) == '') sprite = fallbackId;
		if (!CodenameScriptDiscovery.safeRelativeName(sprite))
			return failPlan(result, 'installation DEFAULT_CHARACTER has an unsafe sprite key: ' + sprite);
		result.sprite = sprite;
		var atlas = planAtlas(engineAssetRoot, sprite);
		if (atlas.diagnostic != null)
			return failPlan(result, atlas.diagnostic);
		result.files.push(makeAsset(engineAssetRoot, xmlRelative,
			'data/characters/' + fallbackId + '.xml'));
		for (relative in atlas.relatives)
			result.files.push(makeAsset(engineAssetRoot, relative, relative));
		for (asset in result.files)
			if (asset.digest == null || asset.digest.length != 64)
				return failPlan(result, 'installation DEFAULT_CHARACTER asset could not be hashed: '
					+ asset.sourceRelative);
		if (result.files.length < 2)
			return failPlan(result, 'installation DEFAULT_CHARACTER has no supported atlas: ' + sprite);
		#else
		return failPlan(result, 'Codename engine-base dependencies require a filesystem target');
		#end
		return result;
	}

	/**
		Copy into an empty owner dependency. Existing files are accepted only when
		a matching receipt already owns every byte; collisions fail closed. This
		function never refreshes, replaces, or removes an installed import file.
	*/
	public static function materialize(engineAssetRoot:String, selectedOwnerSourceRoot:String,
		ownerNamespace:String, fallbackId:String):CodenameBaseCharacterDependencyResult {
		var result:CodenameBaseCharacterDependencyResult = {copied:0, skipped:0, failed:false, diagnostic:null};
		#if sys
		if (selectedOwnerSourceRoot != null && FileSystem.isDirectory(selectedOwnerSourceRoot)
			&& CodenameScriptDiscovery.resolveScopedRelative(selectedOwnerSourceRoot,
				'data/characters/' + fallbackId + '.xml') != null) {
			result.skipped++;
			return result;
		}
		if (!validOwnerNamespace(ownerNamespace) || !safeOwnerRoot(ownerNamespace))
			return failResult(result, 'Codename dependency owner namespace is invalid');
		var planned = plan(engineAssetRoot, fallbackId);
		if (planned.diagnostic != null)
			return failResult(result, planned.diagnostic);
		var dependencyRoot = Path.normalize(Path.join([ownerNamespace, RELATIVE_ROOT]));
		var receiptPath = Path.join([dependencyRoot, RECEIPT_NAME]);
		if (FileSystem.exists(receiptPath)) {
			if (validReceipt(ownerNamespace, dependencyRoot, planned, true)) {
				result.skipped++;
				return result;
			}
			return failResult(result, 'Codename dependency receipt collision; existing import was left unchanged');
		}
		for (asset in planned.files) {
			var destination = safeDestination(dependencyRoot, asset.destinationRelative);
			if (destination == null)
				return failResult(result, 'Codename dependency destination escaped its owner namespace');
			if (FileSystem.exists(destination))
				return failResult(result, 'Codename dependency file collision; existing import was left unchanged: '
					+ Path.join([RELATIVE_ROOT, asset.destinationRelative]));
		}
		var copied:Array<String> = [];
		try {
			for (asset in planned.files) {
				var destination = safeDestination(dependencyRoot, asset.destinationRelative);
				if (destination == null) throw 'unsafe dependency destination';
				ensureDirectory(Path.directory(destination));
				File.copy(asset.source, destination);
				copied.push(destination);
				result.copied++;
			}
			var receipt = makeReceipt(ownerNamespace, fallbackId, planned.sprite, planned.files);
			ensureDirectory(dependencyRoot);
			File.saveContent(receiptPath, Json.stringify(receipt));
			if (!validReceipt(ownerNamespace, dependencyRoot, planned, true))
				throw 'written receipt failed verification';
		} catch (error:Dynamic) {
			for (path in copied)
				try if (FileSystem.exists(path)) FileSystem.deleteFile(path) catch (_:Dynamic) {}
			if (FileSystem.exists(receiptPath))
				try FileSystem.deleteFile(receiptPath) catch (_:Dynamic) {}
			result.copied = 0;
			return failResult(result, 'Codename dependency copy failed: ' + Std.string(error));
		}
		#else
		return failResult(result, 'Codename engine-base dependencies require a filesystem target');
		#end
		return result;
	}

	/** Resolve only a receipt-verified dependency nested under this exact owner. */
	public static function resolveImported(ownerNamespace:String, fallbackId:String):Null<CodenameBaseCharacterDependencyResolution> {
		#if sys
		if (!validOwnerNamespace(ownerNamespace) || !safeOwnerRoot(ownerNamespace)
			|| !CodenameScriptDiscovery.safeRelativeName(fallbackId))
			return null;
		var dependencyRoot = Path.normalize(Path.join([ownerNamespace, RELATIVE_ROOT]));
		var receiptPath = Path.join([dependencyRoot, RECEIPT_NAME]);
		if (!FileSystem.exists(receiptPath) || !CodenameScriptDiscovery.withinRoot(ownerNamespace, receiptPath))
			return null;
		var receipt:CodenameBaseCharacterReceipt;
		try receipt = cast Json.parse(File.getContent(receiptPath)) catch (_:Dynamic) return null;
		if (!validReceiptShape(ownerNamespace, receipt) || receipt.fallbackId != fallbackId
			|| !verifyReceiptBytes(dependencyRoot, receipt))
			return null;
		var xmlRelative = 'data/characters/' + fallbackId + '.xml';
		var xmlPath = safeDestination(dependencyRoot, xmlRelative);
		if (xmlPath == null || !FileSystem.exists(xmlPath)) return null;
		var xmlText:String;
		try xmlText = File.getContent(xmlPath) catch (_:Dynamic) return null;
		var document:Xml;
		try document = Xml.parse(xmlText).firstElement() catch (_:Dynamic) return null;
		if (document == null || document.nodeName != 'character') return null;
		var sprite = document.get('sprite');
		if (sprite == null || StringTools.trim(sprite) == '') sprite = fallbackId;
		if (!CodenameScriptDiscovery.safeRelativeName(sprite) || receipt.sprite != sprite
			|| !receiptAtlasMatches(receipt.files, sprite)) return null;
		var assetFiles:Array<String> = [];
		for (file in receipt.files) assetFiles.push(file.destinationRelative);
		return {definitionId:fallbackId, xmlText:xmlText, assetRoot:dependencyRoot,
			assetFiles:assetFiles, diagnostic:null};
		#else
		return null;
		#end
	}

	#if sys
	static function planAtlas(root:String, sprite:String):{relatives:Array<String>, diagnostic:Null<String>} {
		var stem = 'images/characters/' + sprite;
		var animate = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/Animation.json');
		if (animate != null) {
			var relatives = [animate];
			var atlasDirectory = Path.join([root, stem]);
			var entries:Array<String>;
			try entries = FileSystem.readDirectory(atlasDirectory) catch (_:Dynamic)
				return {relatives:[], diagnostic:'installation Animate atlas directory is unreadable: ' + sprite};
			var pages:Map<Int, {png:Null<String>, json:Null<String>}> = new Map();
			var pagePattern = new EReg('^spritemap([0-9]+)\\.(png|json)$', 'i');
			for (entry in entries) {
				if (!pagePattern.match(entry)) continue;
				var page = Std.parseInt(pagePattern.matched(1));
				if (page == null || page < 1) continue;
				var pair = pages.get(page);
				if (pair == null) pair = {png:null, json:null};
				var relative = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/' + entry);
				if (relative == null)
					return {relatives:[], diagnostic:'unsafe installation Animate atlas page: ' + sprite + '/' + entry};
				if (entry.toLowerCase().endsWith('.png')) pair.png = relative else pair.json = relative;
				pages.set(page, pair);
			}
			var pageNumbers:Array<Int> = [];
			for (page in pages.keys()) pageNumbers.push(page);
			pageNumbers.sort(Reflect.compare);
			if (pageNumbers.length == 0 || pageNumbers[0] != 1)
				return {relatives:[], diagnostic:'installation Animate atlas has no spritemap1 pair: ' + sprite};
			for (page in pageNumbers) {
				var pair = pages.get(page);
				if (pair == null || pair.png == null || pair.json == null)
					return {relatives:[], diagnostic:'incomplete installation Animate atlas page: ' + sprite + '/' + page};
				relatives.push(pair.json);
				relatives.push(pair.png);
			}
			return {relatives:relatives, diagnostic:null};
		}
		var relatives:Array<String> = [];
		var firstPng = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/1.png');
		var firstXml = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/1.xml');
		if (firstPng != null || firstXml != null) {
			var page = 1;
			while (true) {
				var png = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/' + page + '.png');
				var xml = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '/' + page + '.xml');
				if (png == null && xml == null) break;
				if (png == null || xml == null)
					return {relatives:[], diagnostic:'incomplete installation Sparrow atlas: ' + sprite + '/' + page};
				relatives.push(png);
				relatives.push(xml);
				page++;
			}
			return {relatives:relatives, diagnostic:null};
		}
		var png = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '.png');
		var xml = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '.xml');
		var txt = CodenameScriptDiscovery.resolveScopedRelative(root, stem + '.txt');
		if (png != null && xml != null) return {relatives:[png, xml], diagnostic:null};
		if (png != null && txt != null) return {relatives:[png, txt], diagnostic:null};
		if (png != null) return {relatives:[png], diagnostic:null};
		return {relatives:[], diagnostic:'installation DEFAULT_CHARACTER has no supported atlas: ' + sprite};
	}

	static function makeAsset(root:String, sourceRelative:String,
		destinationRelative:String):CodenameBaseCharacterAsset {
		var source = Path.join([root, sourceRelative]);
		var digest = '';
		try digest = Sha256.make(File.getBytes(source)).toHex() catch (_:Dynamic) {}
		return {source:source, sourceRelative:sourceRelative,
			destinationRelative:destinationRelative, digest:digest};
	}
	#end

	static function makeReceipt(owner:String, fallbackId:String, sprite:String,
		assets:Array<CodenameBaseCharacterAsset>):CodenameBaseCharacterReceipt {
		var files:Array<CodenameBaseCharacterReceiptFile> = [];
		for (asset in assets) files.push({sourceRelative:asset.sourceRelative,
			destinationRelative:asset.destinationRelative, digest:asset.digest});
		return {version:VERSION, ownerNamespace:owner, fallbackId:fallbackId,
			sprite:sprite, files:files};
	}

	static function validReceipt(owner:String, dependencyRoot:String,
		planned:CodenameBaseCharacterDependencyPlan, verifyBytes:Bool):Bool {
		#if sys
		var path = Path.join([dependencyRoot, RECEIPT_NAME]);
		if (!FileSystem.exists(path)) return false;
		var receipt:CodenameBaseCharacterReceipt;
		try receipt = cast Json.parse(File.getContent(path)) catch (_:Dynamic) return false;
		if (!validReceiptShape(owner, receipt) || receipt.fallbackId != planned.fallbackId
			|| receipt.sprite != planned.sprite || receipt.files.length != planned.files.length)
			return false;
		for (index in 0...planned.files.length) {
			var expected = planned.files[index];
			var entry = receipt.files[index];
			if (entry.sourceRelative != expected.sourceRelative
				|| entry.destinationRelative != expected.destinationRelative
				|| entry.digest != expected.digest) return false;
			if (verifyBytes) {
				var destination = safeDestination(dependencyRoot, entry.destinationRelative);
				if (destination == null || !FileSystem.exists(destination)) return false;
				var digest = '';
				try digest = Sha256.make(File.getBytes(destination)).toHex() catch (_:Dynamic) return false;
				if (digest != entry.digest) return false;
			}
		}
		return true;
		#else
		return false;
		#end
	}

	static function validReceiptShape(owner:String, receipt:CodenameBaseCharacterReceipt):Bool {
		if (receipt == null || receipt.version != VERSION || receipt.ownerNamespace != owner
			|| !CodenameScriptDiscovery.safeRelativeName(receipt.fallbackId)
			|| !CodenameScriptDiscovery.safeRelativeName(receipt.sprite)
			|| receipt.files == null || receipt.files.length < 2)
			return false;
		var seen:Map<String, Bool> = new Map();
		var hasXml = false;
		for (entry in receipt.files) {
			if (entry == null || !safeRelative(entry.destinationRelative)
				|| !safeRelative(entry.sourceRelative) || entry.digest == null || entry.digest.length != 64
				|| seen.exists(entry.destinationRelative)) return false;
			if (!new EReg('^[0-9a-fA-F]{64}$', '').match(entry.digest)) return false;
			seen.set(entry.destinationRelative, true);
			if (entry.destinationRelative == 'data/characters/' + receipt.fallbackId + '.xml'
				&& StringTools.startsWith(entry.sourceRelative, 'data/characters/')
				&& Path.extension(entry.sourceRelative).toLowerCase() == 'xml')
				hasXml = true;
		}
		return hasXml && receiptAtlasMatches(receipt.files, receipt.sprite);
	}

	static function receiptAtlasMatches(files:Array<CodenameBaseCharacterReceiptFile>, sprite:String):Bool {
		if (files == null) return false;
		var paths:Array<String> = [];
		for (entry in files)
			if (entry.destinationRelative != null && StringTools.startsWith(entry.destinationRelative, 'images/characters/'))
				paths.push(entry.destinationRelative);
		var stem = 'images/characters/' + sprite;
		if (paths.indexOf(stem + '/Animation.json') >= 0) {
			var pages:Map<Int, {png:Bool, json:Bool}> = new Map();
			for (path in paths) {
				if (path == stem + '/Animation.json') continue;
				var pattern = new EReg('^' + EReg.escape(stem + '/spritemap') + '([0-9]+)\\.(png|json)$', 'i');
				if (!pattern.match(path)) return false;
				var page = Std.parseInt(pattern.matched(1));
				if (page == null || page < 1) return false;
				var pair = pages.get(page);
				if (pair == null) pair = {png:false, json:false};
				if (path.toLowerCase().endsWith('.png')) pair.png = true else pair.json = true;
				pages.set(page, pair);
			}
			var pageNumbers:Array<Int> = [];
			for (page in pages.keys()) pageNumbers.push(page);
			pageNumbers.sort(Reflect.compare);
			if (pageNumbers.length == 0 || pageNumbers[0] != 1) return false;
			for (page in pageNumbers) {
				var pair = pages.get(page);
				if (pair == null || !pair.png || !pair.json) return false;
			}
			return true;
		}
		var paged:Array<String> = [];
		var page = 1;
		while (true) {
			var png = stem + '/' + page + '.png';
			var xml = stem + '/' + page + '.xml';
			var hasPng = paths.indexOf(png) >= 0;
			var hasXml = paths.indexOf(xml) >= 0;
			if (!hasPng && !hasXml) break;
			if (!hasPng || !hasXml) return false;
			paged.push(png);
			paged.push(xml);
			page++;
		}
		if (paged.length > 0 && samePathSet(paths, paged)) return true;
		return samePathSet(paths, [stem + '.png', stem + '.xml'])
			|| samePathSet(paths, [stem + '.png', stem + '.txt'])
			|| samePathSet(paths, [stem + '.png']);
	}

	static function samePathSet(left:Array<String>, right:Array<String>):Bool {
		if (left == null || right == null || left.length != right.length) return false;
		for (path in right) if (left.indexOf(path) < 0) return false;
		return true;
	}

	static function validOwnerNamespace(owner:String):Bool {
		if (owner == null || owner == '') return false;
		var clean = StringTools.replace(owner, '\\', '/');
		if (!StringTools.startsWith(clean, 'assets/imported_mods/')) return false;
		var parts = clean.split('/');
		return parts.length == 3 && parts[0] == 'assets' && parts[1] == 'imported_mods'
			&& clean == owner && Path.normalize(clean) == clean && safeRelative(clean);
	}

	static function safeRelative(path:String):Bool {
		return path != null && path != '' && !StringTools.startsWith(path, '/')
			&& path.indexOf(':') < 0 && path.indexOf('\\') < 0
			&& CodenameScriptDiscovery.safeRelativeName(path);
	}

	#if sys
	static function safeDestination(root:String, relative:String):Null<String> {
		var owner = ownerForDependencyRoot(root);
		if (!validDependencyRoot(root) || !safeOwnerRoot(owner)
			|| !safeRelative(relative)) return null;
		var path = Path.normalize(Path.join([root, relative]));
		var expectedRoot = Path.normalize(Path.join([prospectiveRealPath(owner), RELATIVE_ROOT]));
		var canonicalRoot = prospectiveRealPath(root);
		var canonicalPath = prospectiveRealPath(path);
		if (expectedRoot == null || canonicalRoot == null || canonicalRoot != expectedRoot
			|| canonicalPath == null) return null;
		return canonicalPath == canonicalRoot || StringTools.startsWith(canonicalPath, canonicalRoot + '/')
			? path : null;
	}

	static function validDependencyRoot(root:String):Bool {
		if (root == null) return false;
		var clean = StringTools.replace(root, '\\', '/');
		var parts = clean.split('/');
		return parts.length == 4 && parts[0] == 'assets' && parts[1] == 'imported_mods'
			&& parts[3] == RELATIVE_ROOT && Path.normalize(clean) == clean;
	}

	static function ownerForDependencyRoot(root:String):String {
		var parts = StringTools.replace(root, '\\', '/').split('/');
		return parts.length == 4 ? parts[0] + '/' + parts[1] + '/' + parts[2] : '';
	}

	static function safeOwnerRoot(owner:String):Bool {
		if (!validOwnerNamespace(owner)) return false;
		var parent = Path.directory(owner);
		var parentReal = prospectiveRealPath(parent);
		if (parentReal == null) return false;
		var expected = Path.normalize(Path.join([parentReal, Path.withoutDirectory(owner)]));
		if (!FileSystem.exists(owner)) return true;
		if (!FileSystem.isDirectory(owner)) return false;
		try return Path.normalize(FileSystem.fullPath(owner)) == expected catch (_:Dynamic) return false;
	}

	static function prospectiveRealPath(path:String):Null<String> {
		if (path == null || path == '') return null;
		var probe = path;
		var suffix:Array<String> = [];
		while (!FileSystem.exists(probe)) {
			var parent = Path.directory(probe);
			if (parent == null || parent == '' || parent == probe) return null;
			suffix.unshift(Path.withoutDirectory(probe));
			probe = parent;
		}
		var resolved:String;
		try resolved = Path.normalize(FileSystem.fullPath(probe)) catch (_:Dynamic) return null;
		for (part in suffix) resolved = Path.normalize(Path.join([resolved, part]));
		return resolved;
	}

	static function verifyReceiptBytes(dependencyRoot:String,
		receipt:CodenameBaseCharacterReceipt):Bool {
		#if sys
		for (entry in receipt.files) {
			var destination = safeDestination(dependencyRoot, entry.destinationRelative);
			if (destination == null || !FileSystem.exists(destination) || FileSystem.isDirectory(destination)) return false;
			var digest = '';
			try digest = Sha256.make(File.getBytes(destination)).toHex() catch (_:Dynamic) return false;
			if (digest != entry.digest) return false;
		}
		return true;
		#else
		return false;
		#end
	}

	static function ensureDirectory(path:String):Void {
		if (path == null || path == '' || FileSystem.exists(path)) return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path && !FileSystem.exists(parent))
			ensureDirectory(parent);
		if (!FileSystem.exists(path)) FileSystem.createDirectory(path);
	}
	#end

	static function failPlan(plan:CodenameBaseCharacterDependencyPlan,
		diagnostic:String):CodenameBaseCharacterDependencyPlan {
		plan.diagnostic = diagnostic;
		plan.files = [];
		return plan;
	}

	static function failResult(result:CodenameBaseCharacterDependencyResult,
		diagnostic:String):CodenameBaseCharacterDependencyResult {
		result.failed = true;
		result.diagnostic = diagnostic;
		return result;
	}
}
