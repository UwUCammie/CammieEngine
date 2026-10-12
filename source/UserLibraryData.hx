package;

import haxe.Json;

typedef UserLibraryCategory = {
	var id:String;
	var name:String;
	var mods:Array<String>;
}

/** Host-owned metadata. Import refresh never writes this document. */
class UserLibraryData {
	static inline var VERSION:Int = 1;
	var categories:Array<UserLibraryCategory> = [];
	var favorites:Map<String, Bool> = new Map();
	var difficulties:Map<String, String> = new Map();
	var nextCategory:Int = 1;
	var plays = new LibraryHistoryData(false);
	var imports = new LibraryHistoryData(true);

	/** Unknown imported ownership must never alias a base-game library record. */
	public static function resolvedChartKey(owner:String, folder:String, source:String, hasReceipt:Bool):String {
		if (ownerKey(owner) == '' && hasReceipt) return '';
		return chartKey(owner, source == null || source == '' ? folder : source);
	}
	public function lastPlayed(key:String):Float return plays.time(key);
	public function playOrder(key:String):Float return plays.order(key);
	public function recordPlay(key:String, at:Float):Void plays.record([key], at);
	public function lastImported(owner:String):Float return imports.time(ownerKey(owner));
	public function importOrder(owner:String):Float return imports.order(ownerKey(owner));
	public function recordImports(owners:Array<String>, at:Float):Void {
		var keys:Array<String> = [];
		if (owners != null) for (owner in owners) {
			var key = ownerKey(owner);
			if (key == '') throw 'Invalid imported owner.';
			if (keys.indexOf(key) < 0) keys.push(key);
		}
		imports.record(keys, at);
	}
	var grouping:String = 'flat';
	var groupOrder:String = 'default';
	var chartOrder:String = 'az';
	var comparisonDifficulty:String = 'normal';

	public function sorting():{grouping:String, groups:String, charts:String, difficulty:String}
		return {grouping:grouping, groups:groupOrder, charts:chartOrder, difficulty:comparisonDifficulty};
	public function setSorting(grouping:String, groups:String, charts:String):Void {
		if (['flat', 'mod', 'engine'].indexOf(grouping) < 0
			|| ['default', 'az', 'za', 'engine', 'imported'].indexOf(groups) < 0
			|| ['default', 'az', 'za', 'favorites', 'recent', 'scoreHigh', 'scoreLow', 'ratingLow', 'ratingHigh', 'npsHigh', 'npsLow'].indexOf(charts) < 0) throw 'Invalid library sorting.';
		this.grouping = grouping; groupOrder = groups; chartOrder = charts;
	}

	public function setComparisonDifficulty(value:String):Void {
		if (value == null || StringTools.trim(value) == '' || value.length > 128 || ~/[\x00-\x1F\x7F]/.match(value))
			throw 'Invalid comparison difficulty.';
		comparisonDifficulty = StringTools.trim(value).toLowerCase();
	}

	public function new() {}

	public static function ownerKey(owner:String):String {
		var root = owner == null ? '' : StringTools.replace(StringTools.trim(owner), '\\', '/');
		while (StringTools.endsWith(root, '/')) root = root.substr(0, root.length - 1);
		#if windows
		root = root.toLowerCase();
		#end
		return root;
	}

	/** Use the importer's retained owner namespace, not a display name or source path. */
	public static function chartKey(owner:String, sourceFolder:String):String {
		if (sourceFolder == null || StringTools.trim(sourceFolder) == '') return '';
		var folder = StringTools.replace(StringTools.trim(sourceFolder), '\\', '/');
		var root = ownerKey(owner);
		#if windows
		folder = folder.toLowerCase();
		#end
		return Json.stringify([root == '' ? '@base' : root, folder]);
	}

	public function isFavorite(key:String):Bool return key != null && key != '' && favorites.exists(key);
	public function setFavorite(key:String, enabled:Bool):Void {
		if (key == null || key == '') throw 'No chart identity is available.';
		if (enabled) favorites.set(key, true); else favorites.remove(key);
	}
	public function lastDifficulty(key:String):String return difficulties.exists(key) ? difficulties.get(key) : '';
	public function setLastDifficulty(key:String, difficulty:String):Void {
		if (key == null || key == '' || difficulty == null || difficulty == '') return;
		difficulties.set(key, difficulty);
	}

	/** Return a detached view so UI code cannot mutate saved memberships. */
	public function categoryList():Array<UserLibraryCategory> {
		return [for (entry in categories) {id:entry.id, name:entry.name, mods:entry.mods.copy()}];
	}
	static function categoryName(value:String):String {
		if (value == null) throw 'Enter a category name.';
		var clean = StringTools.trim(value);
		if (clean == '' || clean.length > 80 || ~/[\x00-\x1F\x7F]/.match(clean))
			throw 'Use a category name between 1 and 80 characters.';
		return clean;
	}
	public function createCategory(name:String):String {
		var clean = categoryName(name);
		var id = 'category-' + nextCategory++;
		categories.push({id:id, name:clean, mods:[]});
		return id;
	}
	function category(id:String):UserLibraryCategory {
		for (entry in categories) if (entry.id == id) return entry;
		throw 'This category no longer exists.';
	}
	public function renameCategory(id:String, name:String):Void category(id).name = categoryName(name);
	public function deleteCategory(id:String):Void categories.remove(category(id));
	public function hasMod(id:String, owner:String):Bool return category(id).mods.indexOf(ownerKey(owner)) >= 0;
	public function setMembership(id:String, owner:String, included:Bool):Void {
		owner = ownerKey(owner);
		if (owner == '') throw 'Select an imported mod first.';
		var members = category(id).mods;
		if (included) { if (members.indexOf(owner) < 0) members.push(owner); }
		else members.remove(owner);
	}
	/** Category filters combine by union, never duplicating a chart. */
	public function matchesCategories(ids:Array<String>, owner:String):Bool {
		if (ids == null || ids.length == 0) return true;
		owner = ownerKey(owner);
		for (entry in categories) if (ids.indexOf(entry.id) >= 0 && entry.mods.indexOf(owner) >= 0) return true;
		return false;
	}

	public function encode():String {
		var starred = [for (key in favorites.keys()) key]; starred.sort(Reflect.compare);
		var keys = [for (key in difficulties.keys()) key]; keys.sort(Reflect.compare);

		return Json.stringify({version:VERSION, nextCategory:nextCategory, categories:categoryList(),
			sorting:sorting(), playSequence:plays.sequence, plays:plays.entries(),
			importSequence:imports.sequence, imports:imports.entries(), favorites:starred, difficulties:[for (key in keys) {key:key, difficulty:difficulties.get(key)}]});
	}

	static function text(value:Dynamic):String {
		if (!Std.isOfType(value, String) || StringTools.trim(cast value) == '') throw 'Invalid library text.';
		return cast value;
	}
	static function list(value:Dynamic):Array<Dynamic> {
		if (!Std.isOfType(value, Array)) throw 'Invalid library list.';
		return cast value;
	}
	/** Reject malformed/future documents rather than overwriting them with defaults. */
	public static function decode(raw:String):UserLibraryData {
		var result = new UserLibraryData();
		if (raw == null) return result;
		var document:Dynamic = Json.parse(raw);
		if (document == null || document.version != VERSION) throw 'Unsupported library save version.';
		if (!Std.isOfType(document.nextCategory, Int) || document.nextCategory < 1) throw 'Invalid category sequence.';
		result.nextCategory = document.nextCategory;
		var ids:Map<String, Bool> = new Map();
		for (entry in list(document.categories)) {
			if (entry == null) throw 'Invalid category.';
			var id = text(entry.id);
			if (!~/^category-[1-9][0-9]*$/.match(id) || ids.exists(id)) throw 'Invalid category identity.';
			var serial = Std.parseInt(id.substr(9));
			if (serial == null || serial < 1 || id != 'category-' + serial || serial >= result.nextCategory) throw 'Invalid category sequence.';
			ids.set(id, true);
			var members:Array<String> = [];
			for (owner in list(entry.mods)) { var key = ownerKey(text(owner)); if (key == '') throw 'Invalid mod identity.'; if (members.indexOf(key) < 0) members.push(key); }
			result.categories.push({id:id, name:categoryName(text(entry.name)), mods:members});
		}
		for (key in list(document.favorites)) result.setFavorite(text(key), true);
		for (entry in list(document.difficulties)) {
			if (entry == null) throw 'Invalid difficulty preference.';
			result.setLastDifficulty(text(entry.key), text(entry.difficulty));
		}
		if (Reflect.hasField(document, 'plays') || Reflect.hasField(document, 'playSequence'))
			result.plays.restore(document.playSequence, document.plays);
		if (Reflect.hasField(document, 'imports') || Reflect.hasField(document, 'importSequence'))
			result.imports.restore(document.importSequence, document.imports);
		if (Reflect.hasField(document, 'sorting')) {
			var order:Dynamic = document.sorting;
			if (order == null) throw 'Invalid library sorting.';
			result.setSorting(text(order.grouping), text(order.groups), text(order.charts));
			if (Reflect.hasField(order, 'difficulty')) result.setComparisonDifficulty(text(order.difficulty));
		}
		return result;
	}
}
