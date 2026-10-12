package;

class LibraryActionsSubState extends LibraryMenuSubState {
	var chartKey:String;
	var allowSorting:Bool;
	var onlyFavorites:Bool;
	var setFilter:Bool->Void;
	var owner:String;
	var categoryFilters:Array<String>;
	var setCategories:Array<String>->Void;

	public function new(key:String, favoritesOnly:Bool, filter:Bool->Void,
		?selectedOwner:String, ?categories:Array<String>, ?categoryFilter:Array<String>->Void, allowSorting:Bool = false) {
		super(); this.allowSorting = allowSorting; chartKey = key; onlyFavorites = favoritesOnly; setFilter = filter;
		owner = selectedOwner == null ? '' : selectedOwner;
		categoryFilters = categories == null ? [] : categories.copy();
		setCategories = categoryFilter;
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
		if (allowSorting) entries.push({label:'Grouping and sorting', run:function() {
			var child = new LibrarySortingSubState(); child.cameras = cameras;
			child.closeCallback = refresh; openSubState(child);
		}});
		entries.push({label:'Return', run:function() close()});
		showActions('Library actions', entries, false);
	}
}
