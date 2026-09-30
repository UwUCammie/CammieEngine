package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

typedef NightmareVisionDifficultyMetadata = {
	var names:Array<String>;
	@:optional var sourceNames:Array<String>;
	var declared:Bool;
	var source:String;
	var diagnostic:String;
}

typedef NightmareVisionProvenanceUpgrade = {
	var status:String;
	var backup:String;
	var diagnostic:String;
}

/** Read the bounded, literal Freeplay difficulty list from a selected NMV
	owner. This metadata gates destination Freeplay support without deleting
	chart files that the source scripts may load directly. */
class NightmareVisionDifficultyCompat {
	static inline var MAX_MENU_SCRIPT_BYTES:Int = 262144;
	static inline var MAX_PROVENANCE_BYTES:Int = 262144;

	public static function defaults():Array<String> {
		return ['easy', 'normal', 'hard'];
	}

	public static function fromSourceRoot(sourceRoot:String):NightmareVisionDifficultyMetadata {
		#if sys
		if (sourceRoot != null && FileSystem.isDirectory(sourceRoot)) {
			var script = Path.join([sourceRoot, 'scripts', 'states', 'FreeplayState.hx']);
			if (FileSystem.exists(script) && !FileSystem.isDirectory(script)) {
				try {
					if (FileSystem.stat(script).size <= MAX_MENU_SCRIPT_BYTES)
						return parseMenuScript(File.getContent(script), script);
				} catch (_:Dynamic) {}
			}
		}
		#end
		return fallback(sourceRoot, 'no bounded FreeplayState.hx declaration was found');
	}

	public static function parseMenuScript(contents:String, ?source:String):NightmareVisionDifficultyMetadata {
		if (contents == null || contents.length == 0)
			return fallback(source, 'the Freeplay script was empty');
		var declarations:Array<String> = [];
		var assignment = new EReg('^[ \\t]*Difficulty[ \\t]*\\.[ \\t]*difficulties[ \\t]*=[ \\t]*\\[([^\\]]*)\\]', 'gim');
		var offset = 0;
		while (offset <= contents.length && assignment.matchSub(contents, offset)) {
			var match = assignment.matchedPos();
			declarations.push(assignment.matched(1));
			offset = match.pos + match.len;
			if (match.len == 0)
				break;
		}
		if (declarations.length != 1)
			return fallback(source, declarations.length == 0
				? 'no literal Difficulty.difficulties list was found'
				: 'multiple Difficulty.difficulties assignments were found');

		var names:Array<String> = [];
		var sourceNames:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var parts = declarations[0].split(',');
		for (index in 0...parts.length) {
			var value = StringTools.trim(parts[index]);
			if (value == '' && index == parts.length - 1)
				continue;
			if (value.length < 2)
				return fallback(source, 'Difficulty.difficulties was not a literal string list');
			var quote = value.charAt(0);
			if ((quote != '\'' && quote != '"') || value.charAt(value.length - 1) != quote)
				return fallback(source, 'Difficulty.difficulties was not a literal string list');
			var name = StringTools.trim(value.substr(1, value.length - 2));
			if (!validName(name))
				return fallback(source, 'Difficulty.difficulties contained an unsafe or empty name');
			var key = name.toLowerCase();
			if (!seen.exists(key)) {
				seen.set(key, true);
				names.push(key);
				sourceNames.push(name);
			}
		}
		if (names.length == 0)
			return fallback(source, 'Difficulty.difficulties was empty');
		return {names:names, sourceNames:sourceNames, declared:true, source:source, diagnostic:null};
	}

	public static function allows(names:Array<String>, difficulty:String):Bool {
		if (names == null)
			return true;
		if (difficulty == null)
			return false;
		var wanted = StringTools.trim(difficulty).toLowerCase();
		for (name in names)
			if (name != null && StringTools.trim(name).toLowerCase() == wanted)
				return true;
		return false;
	}

	/** Return true only for an existing, exact-owner NMV receipt that lacks the
		selectable-difficulty declaration. */
	public static function needsProvenanceUpgrade(receiptPath:String, expectedOwner:String,
		destinationFolder:String, selectable:Array<String>, unsupported:Array<String>):Bool {
		#if sys
		if (!validUpgradeInputs(receiptPath, expectedOwner, destinationFolder, selectable, unsupported)
			|| !FileSystem.exists(receiptPath) || FileSystem.isDirectory(receiptPath))
			return false;
		try {
			if (FileSystem.stat(receiptPath).size > MAX_PROVENANCE_BYTES)
				return false;
			var record:Dynamic = haxe.Json.parse(File.getContent(receiptPath));
			return matchesOwnerReceipt(record, expectedOwner, destinationFolder)
				&& (missingSelectable(record, selectable) || missingUnsupported(record, unsupported));
		} catch (_:Dynamic) {}
		#end
		return false;
	}

	/** Add only the missing menu declaration to an exact-owner NMV receipt. The
		old bytes are preserved under the supplied tmp backup root before the
		receipt is atomically replaced. Existing declarations and foreign receipts
		are never rewritten. */
	public static function upgradeProvenance(receiptPath:String, backupRoot:String,
		expectedOwner:String, destinationFolder:String,
		selectable:Array<String>, unsupported:Array<String>):NightmareVisionProvenanceUpgrade {
		var untouched:NightmareVisionProvenanceUpgrade = {status:'not-needed', backup:null, diagnostic:null};
		#if sys
		if (!validUpgradeInputs(receiptPath, expectedOwner, destinationFolder, selectable, unsupported)
			|| backupRoot == null || StringTools.trim(backupRoot) == '')
			return untouched;
		if (!FileSystem.exists(receiptPath) || FileSystem.isDirectory(receiptPath))
			return untouched;
		var original:String;
		var record:Dynamic;
		try {
			if (FileSystem.stat(receiptPath).size > MAX_PROVENANCE_BYTES)
				return untouched;
			original = File.getContent(receiptPath);
			record = haxe.Json.parse(original);
		} catch (error:Dynamic) {
			return {status:'failed', backup:null,
				diagnostic:'could not read existing importProvenance.json: ' + Std.string(error)};
		}
		if (!matchesOwnerReceipt(record, expectedOwner, destinationFolder))
			return untouched;
		var declared = normalizedSelectable(selectable);
		var blocked = normalizedUnsupported(unsupported);
		var addSelectable = !Reflect.hasField(record, 'sourceSelectableDifficulties') && declared != null;
		var addUnsupported = !Reflect.hasField(record, 'sourceUnsupportedDifficulties') && blocked != null;
		if (!addSelectable && !addUnsupported)
			return untouched;
		if (addSelectable)
			Reflect.setField(record, 'sourceSelectableDifficulties', declared);
		if (addUnsupported)
			Reflect.setField(record, 'sourceUnsupportedDifficulties', blocked);
		var upgraded:String;
		try upgraded = haxe.Json.stringify(record, null, '\t') catch (error:Dynamic)
			return {status:'failed', backup:null,
				diagnostic:'could not encode upgraded importProvenance.json: ' + Std.string(error)};

		var backupPath = Path.join([backupRoot, destinationFolder + '.json']);
		try {
			ensureDirectory(Path.directory(backupPath));
			if (FileSystem.exists(backupPath)) {
				if (FileSystem.isDirectory(backupPath) || File.getContent(backupPath) != original)
					return {status:'failed', backup:backupPath,
						diagnostic:'existing NMV provenance backup differs from the current receipt; left both unchanged'};
			} else {
				File.saveContent(backupPath, original);
				if (!FileSystem.exists(backupPath) || File.getContent(backupPath) != original)
					return {status:'failed', backup:backupPath,
						diagnostic:'could not verify the original NMV provenance backup'};
			}
		} catch (error:Dynamic) {
			return {status:'failed', backup:backupPath,
				diagnostic:'could not preserve the original NMV provenance: ' + Std.string(error)};
		}

		var temporary = Path.join([Path.directory(receiptPath), '.importProvenance.nmv-menu-upgrade.tmp']);
		try {
			if (FileSystem.exists(temporary))
				return {status:'failed', backup:backupPath,
					diagnostic:'NMV provenance upgrade temp file already exists; left it and the receipt unchanged'};
			File.saveContent(temporary, upgraded);
			if (!FileSystem.exists(temporary) || File.getContent(temporary) != upgraded)
				return {status:'failed', backup:backupPath,
					diagnostic:'could not verify the staged NMV provenance upgrade'};
			FileSystem.rename(temporary, receiptPath);
			if (!FileSystem.exists(receiptPath) || File.getContent(receiptPath) != upgraded)
				return {status:'failed', backup:backupPath,
					diagnostic:'could not verify the upgraded NMV provenance receipt'};
			return {status:'upgraded', backup:backupPath,
				diagnostic:'[nmv-provenance-upgraded] added sourceSelectableDifficulties; original receipt backed up'};
		} catch (error:Dynamic) {
			return {status:'failed', backup:backupPath,
				diagnostic:'could not install upgraded NMV provenance: ' + Std.string(error)};
		}
		#end
		return untouched;
	}

	static function matchesOwnerReceipt(record:Dynamic, expectedOwner:String,
		destinationFolder:String):Bool {
		if (record == null || !Reflect.isObject(record) || Std.isOfType(record, Array)
			)
			return false;
		return Reflect.field(record, 'sourceEngine') == 'Nightmare Vision'
			&& Reflect.field(record, 'sourceOwner') == expectedOwner
			&& Reflect.field(record, 'destinationFolder') == destinationFolder;
	}

	static function missingSelectable(record:Dynamic, selectable:Array<String>):Bool {
		return !Reflect.hasField(record, 'sourceSelectableDifficulties')
			&& normalizedSelectable(selectable) != null;
	}

	static function missingUnsupported(record:Dynamic, unsupported:Array<String>):Bool {
		return !Reflect.hasField(record, 'sourceUnsupportedDifficulties')
			&& normalizedUnsupported(unsupported) != null;
	}

	static function validUpgradeInputs(receiptPath:String, expectedOwner:String,
		destinationFolder:String, selectable:Array<String>, unsupported:Array<String>):Bool {
		return receiptPath != null && StringTools.trim(receiptPath) != ''
			&& expectedOwner != null && StringTools.trim(expectedOwner) != ''
			&& validName(destinationFolder) && normalizedSelectable(selectable) != null
			&& normalizedUnsupported(unsupported) != null;
	}

	static function normalizedSelectable(selectable:Array<String>):Array<String> {
		if (selectable == null || selectable.length == 0)
			return null;
		var names:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (value in selectable) {
			if (!validName(value))
				return null;
			var name = StringTools.trim(value).toLowerCase();
			if (!seen.exists(name)) {
				seen.set(name, true);
				names.push(name);
			}
		}
		return names.length == 0 ? null : names;
	}

	static function normalizedUnsupported(unsupported:Array<String>):Array<String> {
		if (unsupported == null)
			return null;
		var names:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (value in unsupported) {
			if (!validName(value))
				return null;
			var name = StringTools.trim(value).toLowerCase();
			if (!seen.exists(name)) {
				seen.set(name, true);
				names.push(name);
			}
		}
		return names;
	}

	#if sys
	static function ensureDirectory(path:String):Void {
		if (path == null || StringTools.trim(path) == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		FileSystem.createDirectory(path);
	}
	#end

	static function validName(name:String):Bool {
		return name != null && StringTools.trim(name) != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf('\u0000') < 0 && name.indexOf('"') < 0 && name.indexOf('\'') < 0;
	}

	static function fallback(source:String, reason:String):NightmareVisionDifficultyMetadata {
		return {
			names:defaults(),
			declared:false,
			source:source,
			diagnostic:'[nightmare-vision-difficulty-menu-fallback] ' + reason
				+ '; using the NMV defaults Easy, Normal, Hard.'
		};
	}
}
