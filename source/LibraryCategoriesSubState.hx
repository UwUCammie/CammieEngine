package;

import LibraryMenuSubState.LibraryMenuAction;
import ImportedModDiscovery.ImportedModPackage;

/** Categories reference retained owner identities; installed content is never moved. */
class LibraryCategoriesSubState extends LibraryMenuSubState {
	var owner:String;
	var filters:Array<String>;
	var setFilters:Array<String>->Void;
	var packages:Array<ImportedModPackage>;
	var discoveryMessage:String = '';

	public function new(owner:String, filters:Array<String>, changed:Array<String>->Void) {
		super(); this.owner = UserLibraryData.ownerKey(owner);
		this.filters = filters.copy(); setFilters = changed;
	}
	override function create():Void { super.create(); root(); }
	function publishFilters():Void { if (setFilters != null) setFilters(filters.copy()); }
	function root():Void {
		backAction = function() close();
		var entries:Array<LibraryMenuAction> = [
			{label:'Create category', run:function() {
				nameEditor('Create category', '', function(name) return UserLibrary.change(function(data) data.createCategory(name)), root);
			}},
			{label:'Clear category filters (' + filters.length + ' active)', run:function() { filters = []; publishFilters(); root(); }}
		];
		for (category in UserLibrary.data().categoryList()) {
			var id = category.id;
			entries.push({label:(filters.indexOf(id) >= 0 ? '[FILTER] ' : '') + category.name + ' (' + category.mods.length + ' mods)',
				run:function() detail(id)});
		}
		entries.push({label:'Return to library actions', run:function() close()});
		showActions('Categories', entries);
	}
	function detail(id:String):Void {
		var category = findCategory(id);
		if (category == null) { root(); return; }
		backAction = root;
		var entries:Array<LibraryMenuAction> = [
			{label:filters.indexOf(id) >= 0 ? 'Remove this category filter' : 'Include this category in the view', run:function() {
				if (filters.indexOf(id) >= 0) filters.remove(id); else filters.push(id);
				publishFilters(); detail(id);
			}},
			{label:owner == '' ? 'Select an imported song to add its mod'
				: (UserLibrary.data().hasMod(id, owner) ? 'Remove selected mod from category' : 'Add selected mod to category'), run:function() {
				if (owner != '') UserLibrary.change(function(data) data.setMembership(id, owner, !data.hasMod(id, owner)));
				detail(id);
			}},
			{label:'Manage included mods', run:function() manage(id)},
			{label:'Rename category', run:function() {
				nameEditor('Rename category', category.name, function(name) return UserLibrary.change(function(data) data.renameCategory(id, name)), function() detail(id));
			}},
			{label:'Delete category', run:function() confirmDelete(id)},
			{label:'Back to categories', run:root}
		];
		showActions(category.name, entries);
	}
	function findCategory(id:String):UserLibraryData.UserLibraryCategory {
		for (category in UserLibrary.data().categoryList()) if (category.id == id) return category;
		return null;
	}
	function nameEditor(title:String, value:String, commit:String->Bool, after:Void->Void):Void {
		var child = new LibraryNameSubState(title, value, commit);
		child.cameras = cameras; child.closeCallback = after; openSubState(child);
	}
	function confirmDelete(id:String):Void {
		backAction = function() detail(id);
		showActions('Delete category only? Mods and favorites are kept.', [
			{label:'Cancel', run:backAction},
			{label:'Delete category', run:function() {
				if (UserLibrary.change(function(data) data.deleteCategory(id))) {
					filters.remove(id); publishFilters(); root();
				} else render();
			}}
		]);
	}
	function manage(id:String, reset:Bool = true):Void {
		var category = findCategory(id);
		if (category == null) { root(); return; }
		// Reuse package discovery, once per management session, only when requested.
		if (packages == null) {
			var catalog = '';
			if (FNFAssets.exists(CodenameModCatalog.PATH)) try catalog = FNFAssets.getText(CodenameModCatalog.PATH)
			catch (error:Dynamic) discoveryMessage = Std.string(error);
			var discovery = ImportedModDiscovery.discover('assets/data', catalog);
			packages = discovery.packages;
			if (discovery.diagnostics.length > 0) discoveryMessage = discovery.diagnostics.join(' / ');
		}
		backAction = function() detail(id);
		var entries:Array<LibraryMenuAction> = [];
		var seen:Map<String, Bool> = new Map();
		for (entry in packages) {
			var root = UserLibraryData.ownerKey(entry.root); seen.set(root, true);
			entries.push(memberAction(id, root, LibraryPackageLabel.caption(root, entry.title + ' [' + entry.engine + ']')));
		}
		for (root in category.mods) if (!seen.exists(root)) entries.push(memberAction(id, root, LibraryPackageLabel.caption(root, 'Not installed: ' + root)));
		if (discoveryMessage != '') entries.push({label:'Some packages could not be listed: ' + discoveryMessage, run:function() {}});
		entries.push({label:'Back to category', run:backAction});
		showActions('Included mods: ' + category.name, entries, reset);
	}
	function memberAction(id:String, root:String, label:String):LibraryMenuAction {
		return {label:(UserLibrary.data().hasMod(id, root) ? '[x] ' : '[ ] ') + label, run:function() {
			UserLibrary.change(function(data) data.setMembership(id, root, !data.hasMod(id, root)));
			manage(id, false);
		}};
	}
}
