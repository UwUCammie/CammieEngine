package;

/** Freeplay management for the selected chart and its mod: hide, show, rename
 * and remove. A chart can only be hidden; its files leave with its mod. */
class LibraryManageSubState extends LibraryMenuSubState {
	var chartKey:String;
	var owner:String;
	var chartTitle:String;
	var ownerTitle:String;
	var showHidden:Bool;
	var setShowHidden:Bool->Void;
	var namesChanged:Void->Void;

	public function new(chartKey:String, owner:String, chartTitle:String, ownerTitle:String,
		showHidden:Bool, setShowHidden:Bool->Void, namesChanged:Void->Void) {
		super();
		this.chartKey = chartKey == null ? '' : chartKey; this.owner = owner == null ? '' : owner;
		this.chartTitle = chartTitle == null ? '' : chartTitle; this.ownerTitle = ownerTitle == null ? '' : ownerTitle;
		this.showHidden = showHidden; this.setShowHidden = setShowHidden; this.namesChanged = namesChanged;
	}
	override function create():Void { super.create(); refresh(); }

	/** Rows offered for a selection. Kept free of display objects for checks. */
	public static function labels(chartKey:String, owner:String, chartTitle:String, ownerTitle:String,
		chartHidden:Bool, modHidden:Bool, renamed:Bool, removable:Bool, showHidden:Bool):Array<String> {
		var rows:Array<String> = [];
		var hasMod = UserLibraryData.ownerKey(owner) != '';
		if (chartKey != '') rows.push((chartHidden ? 'Show chart: ' : 'Hide chart: ') + chartTitle);
		if (hasMod) {
			rows.push((modHidden ? 'Show mod: ' : 'Hide mod: ') + ownerTitle);
			rows.push('Rename mod: ' + ownerTitle);
			if (renamed) rows.push("Restore the mod's original name");
			if (removable) rows.push('Delete mod and all of its charts...');
		}
		rows.push(showHidden ? 'Stop listing hidden charts and mods' : 'List hidden charts and mods');
		rows.push('Return');
		return rows;
	}

	function refresh():Void {
		var data = UserLibrary.data();
		var hasMod = UserLibraryData.ownerKey(owner) != '';
		var chartHidden = chartKey != '' && data.isChartHidden(chartKey);
		var modHidden = hasMod && data.isModHidden(owner);
		var renamed = hasMod && data.modName(owner) != '';
		var removable = hasMod && LibraryRemovalPresentation.eligible(owner);
		var title = renamed ? data.modName(owner) : ownerTitle;
		var rows = labels(chartKey, owner, chartTitle, title, chartHidden, modHidden, renamed, removable, showHidden);
		var entries:Array<LibraryMenuSubState.LibraryMenuAction> = [];
		var next = 0;
		if (chartKey != '') entries.push({label:rows[next++], run:function() {
			UserLibrary.change(function(data) data.setChartHidden(chartKey, !chartHidden)); refresh();
		}});
		if (hasMod) {
			entries.push({label:rows[next++], run:function() {
				UserLibrary.change(function(data) data.setModHidden(owner, !modHidden)); refresh();
			}});
			entries.push({label:rows[next++], run:function() {
				var child = new LibraryNameSubState('Rename mod', title, function(value:String):Bool {
					if (StringTools.trim(value) == '') return false;
					var saved = UserLibrary.change(function(data) data.setModName(owner, value));
					if (saved && namesChanged != null) namesChanged();
					return saved;
				});
				child.cameras = cameras; child.closeCallback = refresh; openSubState(child);
			}});
			if (renamed) entries.push({label:rows[next++], run:function() {
				if (UserLibrary.change(function(data) data.setModName(owner, '')) && namesChanged != null) namesChanged();
				refresh();
			}});
			if (removable) entries.push({label:rows[next++], run:function() {
				// A mod with a live script session must be released by a neutral state first.
				if (Std.isOfType(flixel.FlxG.state, FreeplayState)
					&& ImportedFreeplayCaller.ownerForFreeplay(CodenameModRuntime.activeRoot()) == ''
					&& HxcFreeplayRuntime.activeOwnerRoots().indexOf(owner) >= 0) {
					LoadingState.loadAndSwitchState(new LibraryRemovalState(owner, title)); return;
				}
				var child = new LibraryRemovalSubState(owner, function() close(), title); child.cameras = cameras;
				openSubState(child);
			}});
		}
		entries.push({label:rows[next++], run:function() {
			showHidden = !showHidden; if (setShowHidden != null) setShowHidden(showHidden); refresh();
		}});
		entries.push({label:rows[next++], run:function() close()});
		showActions('Manage library', entries, false);
	}
}
