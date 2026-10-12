package;

import flixel.FlxG;

/** Opt-in host menu and gameplay-return verification, bound to a private smoke save. */
@:access(FreeplayState)
@:access(CategoryState)
@:access(UserLibrary)
@:access(RuntimeSmokeHarness)
@:access(PauseSubState)
@:access(HealthIcon)
@:access(CodenameImportedModsState)
@:access(LibraryCategoriesSubState)
@:access(LibraryMenuSubState)
class RuntimeLibraryNavigationProbe {
	public static var active(default, null):Bool = false;
	static var phase:Int = -5;
	static var browserSelection:Int = 0;
	static var at:Float = 0;
	static var frames:Int = 0;
	static var held:Int = 0;
	static var original:Dynamic;
	static var initialized:Bool = false;
	static var key:String;
	static var importedKey:String;
	static var owner:String;
	static var category:String;
	static var difficulty:String;
	static var captureName:String = '';
	static var confirmationObserved:Bool = false;
	static var sortExpected:Int = -1;
	static var sortDifficulty:Int = -1;
	static var sortReadiness:Bool = false;
	static var metricFirst:Int = -1;
	static var metricSecond:Int = -1;
	static var originalScores:Map<String, Int>;
	static var refreshOldState:FreeplayState;
	static var refreshOldRow:Dynamic;
	static var refreshOldIcon:Dynamic;
	static var refreshOldStar:Dynamic;
	static var refreshOldCamera:Dynamic;
	static var refreshOldMusic:Dynamic;
	static function swapRefreshTable<T>(values:Array<T>, left:Int, right:Int):Void {
		var value = values[left]; values[left] = values[right]; values[right] = value;
	}
	static var refreshExpectedKey:String;
	static var refreshExpectedSearch:String;
	static var refreshExpectedSave:String;
	static var refreshExpectedDifficulty:String;

	public static function install():Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--verify-library-navigation') < 0) return;
		if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'Navigation probe requires a private save';
		active = true; FlxG.signals.postUpdate.add(update); FlxG.signals.postDraw.add(capture);
		#end
	}
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function event(code:Int, down:Bool):Void {
		FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(down ? openfl.events.KeyboardEvent.KEY_DOWN
			: openfl.events.KeyboardEvent.KEY_UP, true, false, code, code));
	}
	static function press(code:Int):Void { event(code, true); held = code; }
	static function freeplay():FreeplayState {
		check(Std.isOfType(FlxG.state, FreeplayState), 'Expected Freeplay at ' + phase);
		return cast FlxG.state;
	}
	static function openView(id:String):Void {
		check(Std.isOfType(FlxG.state, MainMenuState), 'Expected main menu at ' + phase);
		FreeplayState.openLibraryView(id);
		LoadingState.loadAndSwitchState(new FreeplayState());
	}
	/** Generated private runtime art exercises the real PNG/XML owner loader, never donor files. */
	static function installIconFixture(menu:FreeplayState, index:Int):Void {
		#if sys
		var root = 'tmp/freeplay-icon-fixture';
		for (path in [root, root + '/images', root + '/images/freeplay', root + '/images/freeplay/icons'])
			if (!sys.FileSystem.exists(path)) sys.FileSystem.createDirectory(path);
		var image = new openfl.display.BitmapData(320, 20, true, 0);
		var xml = '<TextureAtlas imagePath="fixturepixel.png">';
		for (i in 0...16) {
			image.fillRect(new openfl.geom.Rectangle(i * 20, 0, 20, 20), i < 2 ? 0xFF36CCA0 : i < 14 ? 0xFFFFC65A : 0xFFB682E6);
			var prefix = i < 2 ? 'idle' : i < 14 ? 'confirm' : 'confirm-hold';
			var number = i < 2 ? i : i < 14 ? i - 2 : i - 14;
			xml += '<SubTexture name="' + prefix + StringTools.lpad(Std.string(number), '0', 4)
				+ '" x="' + (i * 20) + '" y="0" width="20" height="20"/>';
		}
		xml += '</TextureAtlas>';
		var png = root + '/images/freeplay/icons/fixturepixel.png';
		sys.io.File.saveBytes(png, image.encode(image.rect, new openfl.display.PNGEncoderOptions()));
		sys.io.File.saveContent(root + '/images/freeplay/icons/fixturepixel.xml', xml);
		image.dispose();
		menu.buildIconFor(index);
		var icon = menu.iconArray[index];
		check(icon != null, 'Confirmation fixture has no materialized icon');
		icon.iconOwnerRoot = root;
		icon.switchAnim('fixture');
		check(icon.isAnimated && icon.frames.numFrames == 16 && icon.frameWidth == 20, 'Pixel XML was loaded as an entire sheet');
		check(icon.animation.curAnim.name == 'icon' && icon.animation.curAnim.numFrames == 2, 'Browsing did not keep source idle frames');
		icon.confirm(); icon.update(1.3);
		check(icon.animation.curAnim.name == 'confirm-hold', 'Real animation did not advance to authored hold');
		icon.resetConfirmation();
		menu.beginBrowserConfirm(index, FreeplayState.curDifficulty);
		check(menu.browserConfirm.active && icon.animation.curAnim.name == 'confirm', 'Selection did not arm confirmation');
		menu.changeSelection(0, true);
		check(!menu.browserConfirm.active && icon.animation.curAnim.name == 'icon', 'Selection change did not cancel and restore normal');
		icon.setGraphicSize(54,54); icon.updateHitbox(); menu.applyListLayout(); menu.updateBrowserDetails();
		#end
	}

	static function restore():Void {
		if (originalScores != null) { Highscore.songScores = originalScores; originalScores = null; }
		if (!initialized || UserLibrary.storage == null) return;
		Reflect.setField(UserLibrary.storage.data, 'library', original);
		UserLibrary.storage.flush(); UserLibrary.current = null;
	}
	static function update():Void {
		if (!active || RuntimeSmokeHarness.finished) return;
		FlxG.sound.muted = true;
		if (held != 0) { event(held, false); held = 0; }
		if (captureName != '' || ++frames < 3 || haxe.Timer.stamp() - at < 0.35) return;
		try {
			if (!step()) return;
			RuntimeSmokeHarness.emit('library_navigation_step', {phase:phase, state:Type.getClassName(Type.getClass(FlxG.state))});
			phase++; frames = 0; at = haxe.Timer.stamp();
		} catch (error:Dynamic) { restore(); RuntimeSmokeHarness.fail('library-navigation', Std.string(error)); }
	}
	static function step():Bool {
		switch (phase) {
			case -5:
				if (!Std.isOfType(FlxG.state, FreeplayState)) return false;
				var menu = freeplay();
				check(menu.denseBrowser, 'Host browser layout not enabled');
				check(menu.rowSongIndices.length == FreeplayBrowserLayout.centeredPage(menu.orderedVisibleSongs(), FreeplayState.curSelected, FlxG.height, menu.selectedCardHeight()).length, 'Large library did not fill the bounded page');
				for (index in menu.rowSongIndices) {
					var row = menu.songRows[index];
					check(row.x >= 0 && row.y >= FreeplayBrowserLayout.TOP && row.y + 60 < FlxG.height - 68, 'Row escaped browser viewport');
					check(Std.isOfType(row, FreeplayBrowserRow), 'Host row not materialized through shared browser');
				}
				captureName = 'library';
			case -4:
				var menu = freeplay(); var longest = 0;
				for (i in 0...menu.songs.length) if (menu.songs[i].displayTitle.length > menu.songs[longest].displayTitle.length) longest = i;
				FreeplayState.curSelected = longest; menu.changeSelection(0, true);
				browserSelection = longest; captureName = 'long-label';
			case -3: press(40);
			case -2:
				var menu = freeplay();
				check(FreeplayState.curSelected == LibrarySort.select(menu.orderedVisibleSongs(), browserSelection, 1), 'Dense browser down input failed');
				check(menu.rowSongIndices.indexOf(FreeplayState.curSelected) >= 0, 'Keyboard selection scrolled out of page');
				press(38);
			case -1:
				check(FreeplayState.curSelected == browserSelection, 'Dense browser up input failed');
			case 0:
				if (!Std.isOfType(FlxG.state, FreeplayState)) return false;
				var menu = freeplay(); UserLibrary.data(); original = Reflect.field(UserLibrary.storage.data, 'library'); initialized = true;
				Reflect.setField(UserLibrary.storage.data, 'library', null); UserLibrary.storage.flush(); UserLibrary.current = null;
				var base = -1; var imported = -1;
				for (i in 0...menu.songs.length) {
					if (menu.libraryChartKey(i) == '') continue;
					if (menu.libraryOwner(i) != '') { if (imported < 0) imported = i; }
					else if (base < 0 && DifficultyManager.getSupportedDiffs(menu.songs[i].songName).length > 1 && menu.availabilityAllowsSelection(i)) base = i;
				}
				check(base >= 0 && imported >= 0, 'Fixture needs base and imported songs');
				key = menu.libraryChartKey(base); importedKey = menu.libraryChartKey(imported); owner = menu.libraryOwner(imported);
				check(UserLibrary.change(function(data) {
					data.setFavorite(key, true); data.setFavorite(importedKey, true);
					category = data.createCategory('Global import category'); data.setMembership(category, owner, true);
				}), UserLibrary.error);
				FreeplayState.curSelected = base; menu.changeSelection(0, true); menu.changeDiff(1);
				difficulty = DifficultyManager.getDiffName(FreeplayState.curDifficulty);
				check(UserLibrary.data().lastDifficulty(key) == difficulty, 'Manual difficulty not saved'); press(27);
			case 1: openView(FreeplayLibraryView.FAVORITES);
			case 2:
				var menu = freeplay(); var visible = 0; var target = -1;
				for (i in 0...menu.songs.length) if (menu.songMatches(i)) {
					visible++; if (menu.libraryChartKey(i) == key) target = i;
				}
				check(visible == 2 && target >= 0, 'Global favorites lost an owner or duplicated a chart');
				FreeplayState.curSelected = target; menu.changeSelection(0, true);
				check(DifficultyManager.getDiffName(FreeplayState.curDifficulty) == difficulty, 'Menu transition lost difficulty');
				var ratings:Array<Dynamic> = [];
				for (diff in DifficultyManager.getSupportedDiffs(menu.songs[target].songName)) {
					var name = DifficultyManager.getDiffName(diff);
					ratings.push({difficulty:name, value:name == difficulty ? 12 : 3, scale:'fixture'});
				}
				// In-memory menu metadata only: never write fixture ratings into a chart or registry.
				menu.songs[target].authoredDifficultyRatings = FreeplayDifficultyRating.read(ratings);
				menu.updateBrowserDetails();
				check(menu.browserRating.text == 'Authored rating: 12 (fixture)', 'Selected named rating missing');
				menu.changeDiff(1);
				check(menu.browserRating.text == 'Authored rating: 3 (fixture)', 'Difficulty switch retained previous rating');
				menu.changeDiff(-1);
				check(menu.browserRating.text == 'Authored rating: 12 (fixture)', 'Difficulty return lost rating');

				installIconFixture(menu, target);
				check(UserLibrary.data().playOrder(key) == 0, 'Browsing/canceled confirmation recorded a play');
				captureName = 'favorites';
			case 3: press(13);
			case 4:
				if (!confirmationObserved) {
					var menu = freeplay(); var icon = menu.iconArray[FreeplayState.curSelected];
					check(menu.browserConfirm.active && icon.animation.curAnim.name == 'confirm'
						&& icon.animation.curAnim.curFrame > 0, 'Accept did not visibly advance confirmation before launch');
					confirmationObserved = true; captureName = 'confirm'; return false;
				}
				if (!Std.isOfType(FlxG.state, PlayState) || Conductor.songPosition < 1000) return false;
				press(13);
			case 5:
				if (!Std.isOfType(FlxG.state.subState, PauseSubState)) return false;
				(cast FlxG.state.subState:PauseSubState).exitPauseToMenu();
			case 6:
				var menu = freeplay();
				check(menu.libraryChartKey(FreeplayState.curSelected) == key, 'Gameplay return lost selection');
				check(FreeplayState.libraryViewId == FreeplayLibraryView.FAVORITES && menu.anyVisible(), 'Gameplay return lost library view');
				check(DifficultyManager.getDiffName(FreeplayState.curDifficulty) == difficulty, 'Gameplay return lost difficulty');
				check(menu.browserRating.text == 'Authored rating: Unknown', 'Fixture rating leaked across registry reload');
				UserLibrary.current = null; check(UserLibrary.data().lastDifficulty(key) == difficulty, 'Difficulty did not persist');
				check(UserLibrary.data().playOrder(key) == 1 && UserLibrary.data().lastPlayed(key) > 0, 'Successful song start did not persist exactly one play');
				check(UserLibrary.data().playOrder(importedKey) == 0, 'Unplayed imported favorite received history');
				check(UserLibrary.change(function(data) data.setSorting('flat', 'default', 'za')), UserLibrary.error);
				menu.applySearchFilter();
				var reversed = menu.orderedVisibleSongs().copy();
				check(UserLibrary.change(function(data) data.setSorting('flat', 'default', 'recent')), UserLibrary.error);
				menu.applySearchFilter();
				check(menu.libraryChartKey(menu.orderedVisibleSongs()[0]) == key, 'Recent-play order lost played favorite');
				check(reversed.join(',') != menu.orderedVisibleSongs().join(','), 'Recent native fixture needs a different prior order');
				check(menu.libraryChartKey(FreeplayState.curSelected) == key, 'Recent-play order moved selection');
				captureName = 'recently-played';
			case 7:
				UserLibrary.change(function(data) data.setSorting('flat', 'default', 'az')); press(27);
			case 8: openView(category);
			case 9:
				var menu = freeplay(); check(menu.anyVisible(), 'Global category empty');
				for (i in 0...menu.songs.length) if (menu.songMatches(i)) check(UserLibraryData.ownerKey(menu.libraryOwner(i)) == UserLibraryData.ownerKey(owner), 'Global category leaked another mod');
				menu.searchString = 'no-matching-library-fixture'; menu.applySearchFilter();
				check(!menu.anyVisible() && !menu.scoreText.visible && (menu.infoPanel == null || !menu.infoPanel.visible), 'Empty search shows stale details');
				menu.searchString = ''; menu.applySearchFilter();
				check(menu.anyVisible() && menu.diffText.text != 'NO MATCHING SONGS', 'Cleared search retained empty difficulty label');
				var badge = LibraryPackageLabel.badge(owner);
				check(menu.browserSource.text.indexOf(badge) < 0, 'Selected details exposed a raw package badge');
				menu.searchString = badge; menu.applySearchFilter();
				check(menu.anyVisible(), 'Package badge query hid its own category');
				for (i in 0...menu.songs.length) if (menu.songMatches(i))
					check(UserLibraryData.ownerKey(menu.libraryOwner(i)) == UserLibraryData.ownerKey(owner), 'Badge search selected another owner');
				menu.searchString = ''; menu.applySearchFilter();
				captureName = 'category';
			case 10: press(27);
			case 11:
				check(UserLibrary.change(function(data) {data.setFavorite(key, false); data.setFavorite(importedKey, false);}), UserLibrary.error);
				openView(FreeplayLibraryView.FAVORITES);
			case 12:
				var menu = freeplay();
				check(!menu.anyVisible() && menu.diffText.text == 'NO MATCHING FAVORITES', 'Empty global favorites missing');
				check(!menu.scoreText.visible && (menu.infoPanel == null || !menu.infoPanel.visible), 'Empty global favorites retained details');
				captureName = 'empty';
			case 13: press(13);
			case 14:
				freeplay(); LoadingState.loadAndSwitchState(new CodenameImportedModsState());
			case 15:
				if (!Std.isOfType(FlxG.state, CodenameImportedModsState)) return false;
				var picker:CodenameImportedModsState = cast FlxG.state;
				check(picker.entries.length > 0, 'Package picker empty');
				picker.selected = 0; picker.refreshRows();
				for (i in 0...Std.int(Math.min(picker.entries.length, picker.subtitles.length)))
					check(picker.subtitles[i].text.indexOf(LibraryPackageLabel.badge(picker.entries[i].root)) >= 0, 'Picker badge mismatched package');
				captureName = 'package-badges';
			case 16:
				FlxG.state.openSubState(new LibraryCategoriesSubState(owner, [], function(_) {}));
			case 17:
				check(Std.isOfType(FlxG.state.subState, LibraryCategoriesSubState), 'Missing category controls');
				(cast FlxG.state.subState:LibraryCategoriesSubState).manage(category);
			case 18:
				var controls:LibraryCategoriesSubState = cast FlxG.state.subState;
				var found = false;
				for (entry in controls.actions) if (StringTools.startsWith(entry.label, '[x] [' + LibraryPackageLabel.badge(owner) + ']')) found = true;
				check(found, 'Category membership badge mismatched selected owner');
				captureName = 'membership-badges';
			case 19:
				FreeplayState.clearLibraryView(); FreeplayState.curCategory = 'All';
				FreeplayState.currentSongList = []; FreeplayState.curSelected = 0;
				LoadingState.loadAndSwitchState(new FreeplayState());
			case 20:
				var menu = freeplay();
				for (i in 0...menu.songs.length) if (menu.libraryOwner(i) == owner) { FreeplayState.curSelected = i; break; }
				menu.changeSelection(0, true); browserSelection = FreeplayState.curSelected;
				sortDifficulty = FreeplayState.curDifficulty; sortReadiness = menu.availabilityAllowsSelection(browserSelection);
				menu.openLibraryActions();
			case 21:
				var actions:LibraryMenuSubState = cast freeplay().subState;
				check(actions.actions[3].label == 'Grouping and sorting', 'Sort controls missing from host library');
				actions.actions[3].run();
			case 22:
				var controls:LibraryMenuSubState = cast freeplay().subState.subState;
				check(Std.isOfType(controls, LibrarySortingSubState), 'Wrong sorting menu');
				controls.actions[0].run(); controls.actions[1].run(); controls.actions[2].run();
				check(UserLibrary.data().sorting().grouping == 'mod' && UserLibrary.data().sorting().groups == 'az'
					&& UserLibrary.data().sorting().charts == 'za', 'Sort controls not independent');
				captureName = 'sorting-controls';
			case 23:
				freeplay().subState.subState.close(); freeplay().subState.close();
			case 24:
				var menu = freeplay();
				check(FreeplayState.curSelected == browserSelection && FreeplayState.curDifficulty == sortDifficulty, 'Sorting lost chart/difficulty');
				check(menu.availabilityAllowsSelection(browserSelection) == sortReadiness, 'Sorting changed import readiness');
				check(menu.browserGroup.text.indexOf('Mod:') == 0, 'Selected group heading missing');
				var visible = menu.orderedVisibleSongs(); var done:Map<String, Bool> = []; var last = '';
				for (i in visible) {
					var row = menu.libraryOrderRows[i];
					var group = (row.favorite ? 'favorite:' : 'other:') + LibrarySort.group(row, 'mod');
					if (group != last) { check(!done.exists(group), 'Mod group split into noncontiguous rows'); done.set(group, true); last = group; }
				}
				var sawOrdinary = false;
				for (i in visible) {
					if (!menu.libraryOrderRows[i].favorite) sawOrdinary = true;
					else check(!sawOrdinary, 'Favorite sorted below an ordinary chart');
				}
				check(menu.rowSongIndices.length <= FreeplayBrowserLayout.capacity(FlxG.height), 'Sorting defeats row virtualization');
				sortExpected = LibrarySort.select(visible, browserSelection, 1); captureName = 'sorted-mods'; press(40);
			case 25:
				var menu = freeplay(); check(FreeplayState.curSelected == sortExpected, 'Keyboard follows registry instead of sorted view');
				FreeplayState.categoryFilters = [category]; menu.searchString = LibraryPackageLabel.badge(owner); menu.applySearchFilter();
				check(menu.anyVisible(), 'Sorting lost category/badge matches');
				for (i in menu.orderedVisibleSongs()) check(menu.libraryOwner(i) == owner, 'Sort leaked filtered owner');
				captureName = 'sorted-filter';
			case 26:
				UserLibrary.current = null;
				check(UserLibrary.data().sorting().grouping == 'mod' && UserLibrary.data().sorting().charts == 'za', 'Sort preferences did not persist');
				var menu = freeplay(); FreeplayState.categoryFilters = []; menu.searchString = '';
				FreeplayState.curSelected = browserSelection; menu.applySearchFilter(); menu.changeSelection(0, true);
				sortDifficulty = FreeplayState.curDifficulty; sortReadiness = menu.availabilityAllowsSelection(browserSelection);
				// Favorites were verified above; exercise the remaining sort orders without pins.
				check(UserLibrary.change(function(data) { data.setFavorite(key, false); data.setFavorite(importedKey, false); }), UserLibrary.error);
				// Only the opt-in private save is seeded. Real commit boundaries have separate transaction tests.
				LibraryImportHistory.committed([owner]);
				check(UserLibrary.data().importOrder(owner) == 1, 'Import observer did not save private history');
				menu.openLibraryActions();
			case 27:
				var actions:LibraryMenuSubState = cast freeplay().subState; actions.actions[3].run();
			case 28:
				var controls:LibraryMenuSubState = cast freeplay().subState.subState;
				for (i in 0...3) controls.actions[1].run();
				check(UserLibrary.data().sorting().groups == 'imported' && UserLibrary.data().sorting().charts == 'za', 'Recent-import control changed chart sorting');
				captureName = 'recent-import-controls';
			case 29:
				freeplay().subState.subState.close(); freeplay().subState.close();
			case 30:
				var menu = freeplay(); var ordered = menu.orderedVisibleSongs();
				check(FreeplayState.curSelected == browserSelection && FreeplayState.curDifficulty == sortDifficulty, 'Import ordering lost chart/difficulty');
				check(menu.availabilityAllowsSelection(browserSelection) == sortReadiness, 'Import ordering changed readiness');
				var first = -1;
				for (i in ordered) if (!menu.libraryOrderRows[i].random) { first = i; break; }
				check(first >= 0 && menu.libraryOwner(first) == owner, 'Newest imported owner is not first');
				UserLibrary.current = null;
				check(UserLibrary.data().sorting().groups == 'imported' && UserLibrary.data().importOrder(owner) == 1, 'Recent imports did not persist');
				captureName = 'recent-import-mods';
			case 31:
				var menu = freeplay(); var normal = LibraryChartMetric.difficultyIndex('normal', DifficultyManager.getDifficultyNames());
				check(normal >= 0, 'Native metric fixture needs normal difficulty');
				for (i in 0...menu.songs.length) {
					var supported = DifficultyManager.supportedDiff.get(menu.songs[i].songName.toLowerCase());
					if (menu.songs[i].isProvisional || menu.songs[i].songName.toLowerCase() == 'random-song' || menu.libraryOwner(i) != '' || supported == null || supported.indexOf(normal) < 0) continue;
					if (metricFirst < 0) metricFirst = i; else { metricSecond = i; break; }
				}
				check(metricFirst >= 0 && metricSecond >= 0, 'Native metric fixture needs two base songs');
				originalScores = Highscore.songScores; Highscore.songScores = new Map();
				Highscore.songScores.set(Highscore.formatSong(menu.songs[metricFirst].songName, normal, 'best-score'), 100);
				Highscore.songScores.set(Highscore.formatSong(menu.songs[metricSecond].songName, normal, 'best-score'), 900);
				menu.songs[metricFirst].authoredDifficultyRatings = [{difficulty:'normal',value:9,scale:'Fixture stars'}];
				menu.songs[metricSecond].authoredDifficultyRatings = [{difficulty:'normal',value:3,scale:'Fixture stars'}];
				FreeplayState.curSelected = metricFirst; menu.changeSelection(0, true);
				sortDifficulty = FreeplayState.curDifficulty; sortReadiness = menu.availabilityAllowsSelection(metricFirst);
				menu.openLibraryActions();
			case 32:
				var actions:LibraryMenuSubState = cast freeplay().subState; actions.actions[3].run();
			case 33:
				var controls:LibraryMenuSubState = cast freeplay().subState.subState;
				controls.actions[0].run(); controls.actions[0].run();
				for (i in 0...3) controls.actions[2].run();
				check(UserLibrary.data().sorting().grouping == 'flat' && UserLibrary.data().sorting().charts == 'scoreHigh', 'Score ordering control missing');
				captureName = 'score-controls';
			case 34:
				freeplay().subState.subState.close(); freeplay().subState.close();
			case 35:
				var menu = freeplay(); var ordered = menu.orderedVisibleSongs();
				RuntimeSmokeHarness.emit('library_metric_observed', {first:metricFirst, second:metricSecond,
					names:[menu.songs[metricFirst].songName, menu.songs[metricSecond].songName], preference:UserLibrary.data().sorting(),
					rows:[for (i in ordered.slice(0, 5)) menu.libraryOrderRows[i]]});
				var charts = [for (i in ordered) if (!menu.libraryOrderRows[i].random) i];
				check(charts[0] == metricSecond && charts[1] == metricFirst, 'Native score ordering wrong');
				check(FreeplayState.curSelected == metricFirst && FreeplayState.curDifficulty == sortDifficulty, 'Score sort changed launch selection');
				check(menu.browserMetric.text.indexOf('normal') >= 0 && menu.browserMetric.text.indexOf('100') >= 0, 'Comparison value not visible');
				captureName = 'score-order';
			case 36:
				freeplay().openLibraryActions();
			case 37:
				var actions:LibraryMenuSubState = cast freeplay().subState; actions.actions[3].run();
			case 38:
				var controls:LibraryMenuSubState = cast freeplay().subState.subState;
				controls.actions[2].run(); controls.actions[2].run();
				check(UserLibrary.data().sorting().charts == 'ratingLow', 'Rating sort controls missing');
				controls.actions[3].run();
				check(FreeplayState.curDifficulty == sortDifficulty, 'Comparison scope changed play difficulty');
				var limit = DifficultyManager.getDifficultyNames().length + 1;
				while (UserLibrary.data().sorting().difficulty != 'normal' && limit-- > 0) controls.actions[3].run();
				check(UserLibrary.data().sorting().difficulty == 'normal', 'Comparison controls cannot return to normal');
				captureName = 'rating-controls';
			case 39:
				freeplay().subState.subState.close(); freeplay().subState.close();
			case 40:
				var menu = freeplay(); var ordered = menu.orderedVisibleSongs();
				var charts = [for (i in ordered) if (!menu.libraryOrderRows[i].random) i];
				check(charts[0] == metricSecond && charts[1] == metricFirst, 'Native authored rating ordering wrong');
				check(FreeplayState.curSelected == metricFirst && FreeplayState.curDifficulty == sortDifficulty, 'Rating order changed selection');
				check(menu.availabilityAllowsSelection(metricFirst) == sortReadiness, 'Metric sorting changed readiness');
				check(menu.browserMetric.text.indexOf('9') >= 0 && menu.browserMetric.text.indexOf('Fixture stars') >= 0, 'Authored comparison metric not visible');
				UserLibrary.current = null;
				check(UserLibrary.data().sorting().charts == 'ratingLow' && UserLibrary.data().sorting().difficulty == 'normal', 'Metric preferences did not persist');
				captureName = 'rating-order';
			case 41:
				var menu = freeplay();
				menu.songs[metricFirst].authoredFreeplayOrder = 1;
				menu.songs[metricSecond].authoredFreeplayOrder = 0;
				check(UserLibrary.change(function(data) data.setSorting('flat','default','default')), UserLibrary.error);
				menu.libraryOrderKey = ''; menu.applySearchFilter();
			case 42:
				var menu = freeplay(); var ordered = menu.orderedVisibleSongs();
				check(ordered.indexOf(metricSecond) < ordered.indexOf(metricFirst), 'Authored order did not reach native browser');
				check(FreeplayState.curSelected == metricFirst && FreeplayState.curDifficulty == sortDifficulty, 'Authored order lost selection/difficulty');
				check(menu.availabilityAllowsSelection(metricFirst) == sortReadiness, 'Authored order changed readiness');
				captureName = 'authored-order';
			case 43:
				var menu = freeplay();
				check(metricFirst > 0, 'Refresh fixture needs a noninitial registry row');
				refreshExpectedKey = menu.libraryChartKey(metricFirst);
				refreshExpectedSearch = menu.songs[metricFirst].songName;
				refreshExpectedDifficulty = DifficultyManager.getDiffName(FreeplayState.curDifficulty);
				check(UserLibrary.change(function(data) data.setFavorite(refreshExpectedKey,true)), UserLibrary.error);
				refreshExpectedSave = UserLibrary.data().encode();
				menu.searchString = refreshExpectedSearch; menu.applySearchFilter();
				refreshOldRow = menu.songRows[metricFirst]; refreshOldIcon = menu.iconArray[metricFirst];
				refreshOldStar = menu.starArray[metricFirst] == null ? null : menu.starArray[metricFirst][0];
				refreshOldCamera = menu.camUI; refreshOldMusic = FlxG.sound.music;
				// Simulate an older registry order while keeping parallel ownership tables aligned.
				swapRefreshTable(menu.songs, 0, metricFirst); swapRefreshTable(menu.songRows, 0, metricFirst);
				swapRefreshTable(menu.sourceRows, 0, metricFirst); swapRefreshTable(menu.iconArray, 0, metricFirst);
				swapRefreshTable(menu.starArray, 0, metricFirst); swapRefreshTable(menu.hxcCapsuleViews, 0, metricFirst);
				menu.rowSongIndices = [for (index in menu.rowSongIndices) index == 0 ? metricFirst : index == metricFirst ? 0 : index];
				FreeplayState.curSelected = 0;
				refreshOldState = menu; menu.reloadAfterImport();
			case 44:
				var menu = freeplay();
				check(menu == refreshOldState && menu.libraryChartKey(FreeplayState.curSelected) == refreshExpectedKey
					&& FreeplayState.curSelected != 0, 'Refresh restored obsolete row number instead of identity');
				check(menu.songRows[FreeplayState.curSelected] == refreshOldRow && menu.iconArray[FreeplayState.curSelected] == refreshOldIcon, 'Refresh replaced retained visual objects');
				check(refreshOldStar == null || menu.starArray[FreeplayState.curSelected][0] == refreshOldStar, 'Refresh replaced unchanged rating star');
				check(menu.camUI == refreshOldCamera && FlxG.sound.music == refreshOldMusic, 'Refresh recreated camera or menu audio');
				check(menu.searchString == refreshExpectedSearch && menu.searchText.text.indexOf(refreshExpectedSearch) >= 0, 'Refresh dropped visible search');
				check(DifficultyManager.getDiffName(FreeplayState.curDifficulty) == refreshExpectedDifficulty, 'Refresh lost named difficulty');
				check(UserLibrary.data().encode() == refreshExpectedSave, 'Refresh changed library metadata');
				check(menu.availabilityAllowsSelection(FreeplayState.curSelected) == sortReadiness, 'Refresh changed launch readiness');
				captureName = 'refresh-selection';
			case 45:
				restore(); RuntimeSmokeHarness.emit('library_navigation_verified', {globalFavorites:true, category:true, gameplayReturn:true, difficulty:true, emptyView:true, iconConfirmation:confirmationObserved, packageBadges:true, independentSorting:true, recentPlayHistory:true, recentImportHistory:true, metricSorting:true, authoredOrdering:true, refreshContinuity:true}); RuntimeSmokeHarness.succeed();
		}
		return true;
	}
	static function capture():Void {
		#if sys
		if (captureName == '' || haxe.Timer.stamp() - at < 0.5) return;
		var name = captureName; captureName = '';
		try {
			var image = lime.app.Application.current.window.readPixels();
			if (image == null) throw 'Empty library framebuffer';
			sys.io.File.saveBytes(RuntimeSmokeHarness.config().logPath + '.navigation-' + name + '.png', image.encode());
		} catch (error:Dynamic) { restore(); RuntimeSmokeHarness.fail('library-navigation-capture', Std.string(error)); }
		#end
	}
}
