package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import ModifierMenuRows.ModifierRow;

/**
	The modifiers panel in the Freeplay look: a centred popup with the modifiers
	in sections (Rules, Visual, Health, Play style), each with its switch or
	amount on the right, a description of the selected one, and the score
	multiplier they make. Opened over Freeplay and Story mode, and as the song
	setup screen, where it also has a Start song line.

	A modifier that clashes with one that is on stays visible but dimmed, and
	selecting it says which one to turn off; nothing is switched off behind the
	player's back.
**/
class ModifierMenuSubState extends MusicBeatSubstate {
	static inline var PANEL_WIDTH:Int = 760;
	static inline var PANEL_HEIGHT:Int = 620;
	static inline var ROW_PITCH:Int = 30;
	static inline var VISIBLE_ROWS:Int = 13;

	public var onStart:Void->Void;
	/** When set, a Choose characters line calls it. */
	public var onCharacters:Void->Void;
	public var onBack:Void->Void;

	var withStart:Bool;
	var rows:Array<ModifierRow> = [];
	var selected:Int = 0;
	var openingInputFrame:Int = -1;
	var panelX:Float = 0;
	var panelY:Float = 0;
	var rowsY:Float = 0;
	var labels:Array<FlxText> = [];
	var values:Array<FlxText> = [];
	var highlight:FlxSprite;
	var marker:FlxSprite;
	var scoreLine:FlxText;
	var description:FlxText;
	var status:FlxText;

	public function new(withStart:Bool = false) {
		super();
		this.withStart = withStart;
	}

	override function create():Void {
		openingInputFrame = FlxG.game.inputFrame;
		super.create();
		ModifierState.init();
		var groups:Array<String> = [];
		var ids:Array<String> = [];
		for (modifier in ModifierState.modifiers) {
			groups.push(modifier.group);
			ids.push(modifier.internName);
		}
		rows = ModifierMenuRows.build(withStart, onCharacters != null, ModifierState.GROUPS, groups, ids);
		selected = ModifierMenuRows.first(rows);

		panelX = Std.int((FlxG.width - PANEL_WIDTH) / 2);
		panelY = Std.int((FlxG.height - PANEL_HEIGHT) / 2);
		MenuWidgets.panel(this, panelX, panelY, PANEL_WIDTH, PANEL_HEIGHT);
		add(MenuWidgets.text(panelX + 28, panelY + 18, 360, 'Modifiers', 24, MenuStyle.CREAM));
		scoreLine = MenuWidgets.text(panelX + 300, panelY + 24, PANEL_WIDTH - 328, '', MenuStyle.BODY_SIZE, MenuStyle.GOLD, RIGHT);
		add(scoreLine);
		add(MenuWidgets.rect(panelX + 24, panelY + 58, PANEL_WIDTH - 48, 1, MenuStyle.PANEL_RULE));

		rowsY = panelY + 70;
		highlight = MenuWidgets.rect(panelX + 16, rowsY, PANEL_WIDTH - 32, ROW_PITCH - 4, MenuStyle.PANEL_ROW);
		add(highlight);
		marker = MenuWidgets.rect(panelX + 16, rowsY, 6, ROW_PITCH - 4, MenuStyle.WHITE);
		add(marker);
		for (slot in 0...VISIBLE_ROWS) {
			var label = MenuWidgets.text(panelX + 34, rowsY + slot * ROW_PITCH + 4, PANEL_WIDTH - 260, '', MenuStyle.BODY_SIZE, MenuStyle.TEXT);
			label.wordWrap = false;
			labels.push(label);
			add(label);
			var value = MenuWidgets.text(panelX + PANEL_WIDTH - 230, rowsY + slot * ROW_PITCH + 4, 196, '', MenuStyle.BODY_SIZE, MenuStyle.MUTED, RIGHT);
			value.wordWrap = false;
			values.push(value);
			add(value);
		}

		var detailTop = rowsY + VISIBLE_ROWS * ROW_PITCH + 8;
		add(MenuWidgets.rect(panelX + 24, detailTop, PANEL_WIDTH - 48, 1, MenuStyle.PANEL_RULE));
		description = MenuWidgets.text(panelX + 28, detailTop + 10, PANEL_WIDTH - 56, '', MenuStyle.SMALL_SIZE + 2, MenuStyle.TEXT);
		add(description);
		status = MenuWidgets.text(panelX + 28, detailTop + 50, PANEL_WIDTH - 56, '', MenuStyle.SMALL_SIZE, MenuStyle.AMBER);
		add(status);
		add(MenuWidgets.rect(panelX + 24, panelY + PANEL_HEIGHT - 42, PANEL_WIDTH - 48, 1, MenuStyle.PANEL_RULE));
		add(MenuWidgets.text(panelX + 28, panelY + PANEL_HEIGHT - 32, PANEL_WIDTH - 56,
			'UP/DOWN choose    ENTER toggle    LEFT/RIGHT amount    ESC ' + (withStart ? 'back' : 'done'),
			MenuStyle.SMALL_SIZE, MenuStyle.MUTED, CENTER));
		render();
	}

	function render():Void {
		var top = ModifierMenuRows.firstVisible(selected, rows.length, VISIBLE_ROWS);
		for (slot in 0...VISIBLE_ROWS) {
			var index = top + slot;
			var label = labels[slot];
			var value = values[slot];
			label.visible = value.visible = index < rows.length;
			if (index >= rows.length)
				continue;
			var row = rows[index];
			var isSelected = index == selected;
			value.text = '';
			label.x = panelX + 34;
			switch (row.kind) {
				case 'header':
					label.text = row.id.toUpperCase();
					label.size = MenuStyle.SECTION_SIZE;
					label.color = MenuStyle.TEAL;
					label.x = panelX + 28;
				case 'start':
					label.text = 'Start song';
					label.size = MenuStyle.BODY_SIZE;
					label.color = isSelected ? MenuStyle.CHOICE : MenuStyle.CREAM;
				case 'characters':
					label.text = 'Choose characters';
					label.size = MenuStyle.BODY_SIZE;
					label.color = isSelected ? MenuStyle.CHOICE : MenuStyle.CREAM;
				case 'reset':
					label.text = 'Turn everything off';
					label.size = MenuStyle.BODY_SIZE;
					label.color = isSelected ? MenuStyle.CHOICE : MenuStyle.TEXT;
				default:
					var modifier = ModifierState.find(row.id);
					var blocked = !modifier.value && ModifierState.blockedBy(row.id) != null;
					label.text = modifier.name;
					label.size = MenuStyle.BODY_SIZE;
					label.color = blocked ? MenuStyle.DISABLED : (isSelected ? MenuStyle.CHOICE : MenuStyle.TEXT);
					value.text = blocked ? 'UNAVAILABLE' : ModifierMenuRows.valueLabel(modifier.value, modifier.amount, modifier.defAmount, modifier.precision);
					value.color = blocked ? MenuStyle.DISABLED : MenuStyle.switchColor(modifier.value);
			}
			label.y = rowsY + slot * ROW_PITCH + (row.kind == 'header' ? 10 : 4);
			if (isSelected) {
				highlight.y = marker.y = rowsY + slot * ROW_PITCH;
				marker.color = MenuStyle.GOLD;
			}
		}
		scoreLine.text = ModifierState.multiplierLabel();
		scoreLine.color = ModifierState.unrankedActive() ? MenuStyle.AMBER : MenuStyle.GOLD;
		var row = rows[selected];
		switch (row.kind) {
			case 'start':
				description.text = 'Play the song with these modifiers.';
			case 'characters':
				description.text = 'Pick who sings for you and the opponent in the selected song (F3).';
			case 'reset':
				description.text = 'Switch every modifier off and set every amount back to normal.';
			default:
				var modifier = ModifierState.find(row.id);
				description.text = modifier.desc;
				var blocker = modifier.value ? null : ModifierState.blockedBy(row.id);
				if (blocker != null)
					status.text = 'Turn off ' + blocker + ' to use this.';
		}
	}

	override function update(elapsed:Float):Void {
		super.update(elapsed);
		// The key that opened this panel must not also act inside it.
		if (FlxG.game.inputFrame == openingInputFrame)
			return;
		if (nativeControls.BACK) {
			FlxG.sound.play('assets/sounds/cancelMenu' + TitleState.soundExt);
			close();
			if (onBack != null)
				onBack();
			return;
		}
		if (nativeControls.UP_MENU)
			moveBy(-1);
		if (nativeControls.DOWN_MENU)
			moveBy(1);
		if (nativeControls.LEFT_MENU)
			adjust(false);
		if (nativeControls.RIGHT_MENU)
			adjust(true);
		if (nativeControls.ACCEPT)
			activate();
	}

	function moveBy(step:Int):Void {
		selected = ModifierMenuRows.move(rows, selected, step);
		status.text = '';
		FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);
		render();
	}

	function adjust(increase:Bool):Void {
		var row = rows[selected];
		if (row.kind != 'modifier' || ModifierState.find(row.id).amount == null)
			return;
		if (ModifierState.changeAmount(row.id, increase))
			FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.4);
		else
			explainBlocked(row.id);
		render();
	}

	function activate():Void {
		var row = rows[selected];
		switch (row.kind) {
			case 'start':
				FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt);
				if (onStart != null)
					onStart();
				return;
			case 'characters':
				FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt);
				close();
				onCharacters();
				return;
			case 'reset':
				ModifierState.resetAll();
				status.text = 'Every modifier is off.';
				FlxG.sound.play('assets/sounds/confirmMenu' + TitleState.soundExt, 0.6);
			case 'modifier':
				var modifier = ModifierState.find(row.id);
				if (ModifierState.setOn(row.id, !modifier.value)) {
					status.text = '';
					FlxG.sound.play('assets/sounds/scrollMenu' + TitleState.soundExt, 0.6);
				} else
					explainBlocked(row.id);
			default:
		}
		render();
	}

	function explainBlocked(id:String):Void {
		var blocker = ModifierState.blockedBy(id);
		if (blocker == null)
			return;
		status.text = 'Turn off ' + blocker + ' to use this.';
		FlxG.sound.play('assets/sounds/cancelMenu' + TitleState.soundExt, 0.5);
	}
}
