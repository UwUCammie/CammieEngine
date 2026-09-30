package;

import flixel.FlxG;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import ImportedModDiscovery.ImportedModPackage;

/** Explicit package picker for imported owners; no package is chosen implicitly. */
class CodenameImportedModsState extends MusicBeatState {
	var entries:Array<ImportedModPackage> = [];
	var diagnostics:Array<String> = [];
	var selected:Int = 0;
	var heading:FlxText;
	var rows:Array<FlxText> = [];
	var subtitles:Array<FlxText> = [];
	var details:FlxText;
	var notice:FlxText;

	override function create():Void {
		super.create();
		FlxG.camera.bgColor = FlxColor.fromRGB(12, 12, 18);
		heading = new FlxText(40, 28, FlxG.width - 80, 'Imported Mods', 34);
		heading.setFormat(null, 34, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		add(heading);
		var catalog = '';
		if (FNFAssets.exists(CodenameModCatalog.PATH)) try catalog = FNFAssets.getText(CodenameModCatalog.PATH)
		catch (error:Dynamic) diagnostics.push('[codename-mod-catalog] ' + Std.string(error));
		var discovery = ImportedModDiscovery.discover('assets/data', catalog);
		entries = discovery.packages;
		for (message in discovery.diagnostics) diagnostics.push(message);
		for (index in 0...8) {
			var row = new FlxText(76, 102 + index * 54, FlxG.width - 152, '', 22);
			row.setFormat(null, 22, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
			row.scrollFactor.set();
			rows.push(row);
			add(row);
			var subtitle = new FlxText(102, 127 + index * 54, FlxG.width - 178, '', 14);
			subtitle.setFormat(null, 14, 0xFFB9B9C5, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
			subtitle.scrollFactor.set();
			subtitles.push(subtitle);
			add(subtitle);
		}
		details = new FlxText(76, FlxG.height - 102, FlxG.width - 152, '', 15);
		details.setFormat(null, 15, 0xFFB9B9C5, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		details.wordWrap = true;
		details.fieldHeight = 54;
		add(details);
		notice = new FlxText(40, FlxG.height - 32, FlxG.width - 80,
			'Up/Down: choose package   Enter: open package   Backspace: native menu', 15);
		notice.setFormat(null, 15, 0xFFA0A0A0, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		add(notice);
		refreshRows();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (controls.UP_MENU || FlxG.keys.justPressed.UP) {
			if (entries.length > 0) selected = selected <= 0 ? entries.length - 1 : selected - 1;
			refreshRows();
		}
		if (controls.DOWN_MENU || FlxG.keys.justPressed.DOWN) {
			if (entries.length > 0) selected = (selected + 1) % entries.length;
			refreshRows();
		}
		if (controls.BACK || FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE) {
			CodenameModRuntime.clearActiveOwner();
			LoadingState.loadAndSwitchState(new MainMenuState());
			return;
		}
		if ((controls.ACCEPT || FlxG.keys.justPressed.ENTER) && entries.length > 0)
			launchSelected();
	}

	function refreshRows():Void {
		if (rows == null) return;
		var first = Std.int(Math.max(0, selected - 5));
		if (first + rows.length > entries.length) first = Std.int(Math.max(0, entries.length - rows.length));
		for (index in 0...rows.length) {
			var itemIndex = first + index;
			var row = rows[index];
			var subtitle = subtitles[index];
			if (itemIndex >= entries.length) {
				row.text = '';
				subtitle.text = '';
				continue;
			}
			var item = entries[itemIndex];
			var current = itemIndex == selected;
			row.text = (current ? '> ' : '  ') + item.title;
			row.color = current ? FlxColor.YELLOW : FlxColor.WHITE;
			subtitle.text = '(' + item.engine + ')';
			subtitle.color = current ? FlxColor.YELLOW : 0xFFB9B9C5;
		}
		if (details != null) {
			if (entries.length == 0)
				details.text = diagnostics.length == 0 ? 'No imported packages are available.' : diagnostics.slice(0, 2).join('\n');
			else {
				var item = entries[selected];
				if (item.launchState != '')
					details.text = 'Open the package\'s authored title or intro screen.';
				else if (item.songCount > 0)
					details.text = 'Open native Freeplay for ' + item.songCount + ' imported song'
						+ (item.songCount == 1 ? '.' : 's.');
				else
					details.text = 'No authored title screen or imported Freeplay songs are available.';
				if (diagnostics.length > 0) details.text += '\n' + diagnostics[0];
			}
		}
	}

	function launchSelected():Void {
		var item = entries[selected];
		if (item.launchState != '') {
			if (!CodenameModRuntime.activateOwner(item.root)) {
				diagnostics = CodenameModRuntime.diagnostics();
				if (diagnostics.length == 0) diagnostics.push('The selected package could not be opened.');
				refreshRows();
				return;
			}
			var target:Dynamic = new CodenameImportedState(item.root, item.launchState);
			LoadingState.loadAndSwitchState(cast target);
			return;
		}
		if (item.songCount <= 0) {
			diagnostics = ['This package has no authored title screen or imported Freeplay songs.'];
			refreshRows();
			return;
		}
		var categories:Array<Dynamic> = null;
		try categories = cast FreeplayRegistry.getJson() catch (error:Dynamic)
			trace('[imported-mod-freeplay] ' + Std.string(error));
		var songs = FreeplayDirectEntry.select(categories, item.root,
			function(name:String):String return ImportedModDiscovery.ownerForSong(name, 'assets/data'));
		if (songs.length == 0) {
			diagnostics = ['This package has no songs in the Freeplay registry.'];
			refreshRows();
			return;
		}
		CodenameModRuntime.clearActiveOwner();
		FreeplayState.currentSongList = [];
		ImportedFreeplayCaller.capturePackage(item.root);
		LoadingState.loadAndSwitchState(new FreeplayState());
	}
}
