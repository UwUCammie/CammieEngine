package;

class LibraryActionsSubState extends LibraryMenuSubState {
	var chartKey:String;
	var allowSorting:Bool;
	var onlyFavorites:Bool;
	var setFilter:Bool->Void;
	var owner:String;
	var ownerTitle:String;
	var categoryFilters:Array<String>;
	var setCategories:Array<String>->Void;
	var collection:String;
	var setCollection:String->Void;

	public function new(key:String, favoritesOnly:Bool, filter:Bool->Void,
		?selectedOwner:String, ?categories:Array<String>, ?categoryFilter:Array<String>->Void, allowSorting:Bool = false, collection:String = 'All', ?collectionFilter:String->Void, ownerTitle:String = '', chartTitle:String = '') {
		super(); this.allowSorting = allowSorting; chartKey = key; onlyFavorites = favoritesOnly; setFilter = filter;
		this.ownerTitle = ownerTitle; owner = selectedOwner == null ? '' : selectedOwner;
		cardTitle = chartTitle; cardCaption = ownerTitle;
		categoryFilters = categories == null ? [] : categories.copy();
		setCategories = categoryFilter; this.collection = collection; setCollection = collectionFilter;
	}
	override function create():Void { super.create(); refresh(); }
	function refresh():Void {
		var entries:Array<LibraryMenuSubState.LibraryMenuAction> = [
			{label:chartKey == '' ? 'Select an installed chart to favorite'
				: (UserLibrary.data().isFavorite(chartKey) ? 'Remove favorite' : 'Add favorite'), run:function() {
				if (chartKey != '') {
					var enabled = !UserLibrary.data().isFavorite(chartKey);
					UserLibrary.change(function(data) data.setFavorite(chartKey, enabled)); refresh();
				}
			}},
			{label:onlyFavorites ? 'Show all songs in this view' : 'Show favorites in this view', run:function() {
				onlyFavorites = !onlyFavorites; setFilter(onlyFavorites); close();
			}},
			{label:'Categories (' + categoryFilters.length + ' filters active)', run:function() {
				var child = new LibraryCategoriesSubState(owner, categoryFilters, function(value) {
					categoryFilters = value.copy(); if (setCategories != null) setCategories(value.copy());
				});
				child.cameras = cameras; child.closeCallback = refresh; openSubState(child);
			}},
		];
		if (setCollection != null) entries.push({label:'Song collection: ' + collection, run:function() {
			var child = new LibraryCollectionsSubState(collection, setCollection); child.cameras = cameras;
			openSubState(child);
		}});
		if (allowSorting) entries.push({label:'Grouping and sorting', run:function() {
			var child = new LibrarySortingSubState(); child.cameras = cameras;
			child.closeCallback = refresh; openSubState(child);
		}});
		#if sys
		var removal = ImportRemovalManager.poll();
		if (!removal.busy && (removal.phase == 'conflict' || removal.phase == 'cleanup-pending')) entries.push({label:'Recover interrupted mod removal', run:function() {
			if (Std.isOfType(flixel.FlxG.state, FreeplayState)
				&& ImportedFreeplayCaller.ownerForFreeplay(CodenameModRuntime.activeRoot()) == '') {
				LoadingState.loadAndSwitchState(new LibraryRemovalState('')); return;
			}
			var child = new LibraryRemovalSubState(''); child.cameras = cameras; child.closeCallback = refresh; openSubState(child);
		}});
		#end
		if (LibraryRemovalPresentation.eligible(owner)) entries.push({label:'Remove installed mod (preserve saved history)', run:function() {
			// Removal can take linked packages too, and any of them may be held by a
			// Freeplay module, a mod menu or a mod session started from Freeplay; the
			// neutral state releases all of those before it looks at ownership.
			if (Std.isOfType(flixel.FlxG.state, FreeplayState)) {
				LoadingState.loadAndSwitchState(new LibraryRemovalState(owner,ownerTitle)); return;
			}
			var child = new LibraryRemovalSubState(owner, function() close(), ownerTitle); child.cameras = cameras;
			openSubState(child);
		}});
		entries.push({label:'Return', run:function() close()});
		showActions('Library actions', entries, false);
	}
}
