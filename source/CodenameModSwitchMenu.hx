package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import CodenameModSwitchPlan.CodenameModSwitchEntry;

/** Generic owner-level equivalent of Codename's ModSwitchMenu substate. */
class CodenameModSwitchMenu extends MusicBeatSubstate {
	var entries:Array<CodenameModSwitchEntry> = [];
	var diagnostics:Array<String> = [];
	var selected:Int = 0;
	var rows:Array<FlxText> = [];
	var details:FlxText;

	override function create():Void {
		super.create();
		var shade = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, FlxColor.BLACK);
		shade.alpha = 0.88;
		add(shade);
		var heading = new FlxText(36, 34, FlxG.width - 72, 'Switch Mod', 32);
		heading.setFormat(null, 32, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		add(heading);
		if (FNFAssets.exists(CodenameModCatalog.PATH)) {
			var plan = CodenameModSwitchPlan.fromCatalog(FNFAssets.getText(CodenameModCatalog.PATH),
				CodenameModRuntime.activeRoot());
			entries = plan.entries;
			diagnostics = plan.diagnostics;
		} else entries = CodenameModSwitchPlan.fromCatalog('', CodenameModRuntime.activeRoot()).entries;
		selected = CodenameModSwitchPlan.initialSelection(entries);
		for (index in 0...8) {
			var row = new FlxText(72, 104 + index * 48, FlxG.width - 144, '', 22);
			row.setFormat(null, 22, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
			rows.push(row);
			add(row);
		}
		details = new FlxText(72, FlxG.height - 100, FlxG.width - 144, '', 15);
		details.setFormat(null, 15, 0xFFB9B9C5, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		details.wordWrap = true;
		details.fieldHeight = 46;
		add(details);
		var hint = new FlxText(30, FlxG.height - 30, FlxG.width - 60,
			'Up/Down: choose owner   Enter: switch   Backspace: close', 14);
		hint.setFormat(null, 14, 0xFFA0A0A0, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		add(hint);
		refreshRows();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (controls.BACK || FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE) {
			close();
			return;
		}
		if (entries.length == 0) return;
		if (controls.UP_MENU || FlxG.keys.justPressed.UP) {
			selected = selected <= 0 ? entries.length - 1 : selected - 1;
			refreshRows();
		}
		if (controls.DOWN_MENU || FlxG.keys.justPressed.DOWN) {
			selected = (selected + 1) % entries.length;
			refreshRows();
		}
		if (controls.ACCEPT || FlxG.keys.justPressed.ENTER) switchOwner();
	}

	function refreshRows():Void {
		if (rows == null) return;
		var first = Std.int(Math.max(0, selected - 5));
		if (first + rows.length > entries.length) first = Std.int(Math.max(0, entries.length - rows.length));
		for (index in 0...rows.length) {
			var entryIndex = first + index;
			var row = rows[index];
			if (entryIndex >= entries.length) { row.text = ''; continue; }
			var entry = entries[entryIndex];
			var current = entryIndex == selected;
			row.text = (current ? '> ' : '  ') + (entry.active ? '[Active] ' : '') + entry.label;
			row.color = current ? FlxColor.YELLOW : FlxColor.WHITE;
		}
		if (details == null) return;
		if (entries.length == 0) details.text = 'No installed Codename owners are available.';
		else {
			var entry = entries[selected];
			details.text = entry.disable ? 'Return to the native menu and disable the active imported owner.' : entry.root;
			if (diagnostics.length > 0) details.text += '\n' + diagnostics[0];
		}
	}

	function switchOwner():Void {
		var entry = entries[selected];
		if (entry.disable) CodenameModRuntime.clearActiveOwner();
		else if (!CodenameModRuntime.activateOwner(entry.root)) {
			diagnostics = CodenameModRuntime.diagnostics();
			if (diagnostics.length == 0) diagnostics.push('The selected owner could not be activated.');
			refreshRows();
			return;
		}
		// The active owner's own global preStateSwitch hook redirects this native
		// menu state to its authored menu when one exists. Otherwise MainMenuState
		// remains the safe native fallback.
		FlxG.switchState(new MainMenuState());
	}
}
