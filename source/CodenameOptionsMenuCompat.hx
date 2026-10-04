package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/**
	Host for the shared menu exposed to Codename scripts as
	funkin.options.OptionsMenu. It maps donor category navigation onto native
	settings while keeping the currently selected imported owner active.
*/
class CodenameOptionsMenuCompat extends MusicBeatState {
	static var reportedOptionGaps:Map<String, Bool> = new Map();
	static inline var ROW_HEIGHT:Float = 47;
	static inline var FIRST_ROW_Y:Float = 118;
	static inline var VISIBLE_ROWS:Int = 10;
	static inline var ROW_SCALE:Float = 0.85;
	static inline var ROW_MOTION_RATE:Float = 2;

	var categoryIndex:Int = 0;
	var rowIndex:Int = 0;
	var inCategory:Bool = false;
	var onExitCallback:Dynamic;
	var returnOwnerRoot:String = '';
	var returnScriptPath:String = '';
	var ownerMenus:Array<Dynamic> = [];
	var ownerOptionsSave:CodenameOwnerSaveData;
	var workingOptions:Dynamic;
	var optionsDirty:Bool = false;
	var hasExited:Bool = false;
	var heading:FlxText;
	var help:FlxText;
	var rowGroup:FlxTypedGroup<FlxText>;
	var rowMotionTargetYs:Array<Float> = [];
	var rowMotionActive:Bool = false;
	var rowMotionDirection:Int = 0;

	public function new(?onExitCallback:Dynamic, categoryIndex:Int = 0, rowIndex:Int = 0,
		?returnOwnerRoot:String, ?returnScriptPath:String) {
		super();
		this.onExitCallback = onExitCallback;
		this.categoryIndex = categoryIndex;
		this.rowIndex = rowIndex;
		if (returnOwnerRoot != null && returnScriptPath != null) {
			this.returnOwnerRoot = returnOwnerRoot;
			this.returnScriptPath = returnScriptPath;
		} else if (Std.isOfType(FlxG.state, CodenameImportedState)) {
			var source:CodenameImportedState = cast FlxG.state;
			this.returnOwnerRoot = source.ownerRoot;
			this.returnScriptPath = source.scriptPath;
		}
	}

	override public function create():Void {
		super.create();
		workingOptions = CodenameOptionsMenuModel.copyOptions(OptionsHandler.options);
		loadOwnerOptions();
		reportUnsupportedSourceOptions();

		var background = new FlxSprite(-80).loadGraphic('assets/images/menuBG.png');
		background.scrollFactor.set(0, 0.18);
		background.setGraphicSize(Std.int(background.width * 1.2));
		background.updateHitbox();
		background.screenCenter();
		background.color = 0xFF7194FC;
		background.antialiasing = true;
		add(background);

		heading = new FlxText(40, 28, FlxG.width - 80, '', 32);
		heading.setFormat(null, 32, FlxColor.WHITE, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		heading.scrollFactor.set();
		add(heading);

		rowGroup = new FlxTypedGroup<FlxText>();
		add(rowGroup);

		help = new FlxText(34, FlxG.height - 34, FlxG.width - 68, '', 15);
		help.setFormat(null, 15, 0xFFE0E0E0, CENTER, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		help.scrollFactor.set();
		add(help);
		refreshRows();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		updateRowMotion(elapsed);
		if (controls.BACK || FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE) {
			if (inCategory) {
				inCategory = false;
				rowIndex = 0;
				refreshRows();
			} else {
				exit();
			}
			return;
		}

		var up = controls.UP_MENU || FlxG.keys.justPressed.UP;
		var down = controls.DOWN_MENU || FlxG.keys.justPressed.DOWN;
		if (up || down) {
			var count = inCategory ? currentRows().length : menuLabels().length;
			if (count > 0)
				rowIndex = up ? (rowIndex <= 0 ? count - 1 : rowIndex - 1) : (rowIndex + 1) % count;
			refreshRows(up ? -1 : 1);
			return;
		}

		var left = controls.LEFT_MENU || FlxG.keys.justPressed.LEFT;
		var right = controls.RIGHT_MENU || FlxG.keys.justPressed.RIGHT;
		if (inCategory && (left || right)) {
			adjustSelected(right ? 1 : -1);
			return;
		}

		if (controls.ACCEPT || FlxG.keys.justPressed.ENTER || FlxG.keys.justPressed.SPACE)
			acceptSelected();
	}

	function acceptSelected():Void {
		if (!inCategory) {
			var categories = menuLabels();
			if (rowIndex < 0 || rowIndex >= categories.length) return;
			categoryIndex = rowIndex;
			if (!isOwnerOptionsCategory() && currentCategory() == 'Controls') {
				// ControlsState normally returns to SaveDataState. Pass a concrete
				// options screen so this nested Codename route returns to its caller.
				openControls();
				return;
			}
			inCategory = true;
			rowIndex = 0;
			refreshRows();
			return;
		}

		var rows = currentRows();
		if (rowIndex < 0 || rowIndex >= rows.length) return;
		var row = rows[rowIndex];
		if (!isOwnerOptionsCategory() && Reflect.field(row, 'kind') == 'action'
			&& Reflect.field(row, 'field') == 'controls') {
			openControls();
			return;
		}
		if (isOwnerOptionsCategory()) toggleOwnerOption(row);
		else if (Reflect.field(row, 'kind') == 'toggle') adjustSelected(1);
	}

	function openControls():Void {
		commitOptions();
		var returnState:FlxState = new CodenameOptionsMenuCompat(onExitCallback,
			categoryIndex, rowIndex, returnOwnerRoot, returnScriptPath);
		LoadingState.loadAndSwitchState(new ControlsState(returnState));
	}

	function adjustSelected(direction:Int):Void {
		var rows = currentRows();
		if (rowIndex < 0 || rowIndex >= rows.length) return;
		if (isOwnerOptionsCategory()) {
			toggleOwnerOption(rows[rowIndex]);
			return;
		}
		if (CodenameOptionsMenuModel.adjust(workingOptions, rows[rowIndex], direction, FlxG.keys.pressed.SHIFT)) {
			optionsDirty = true;
			refreshRows();
		}
	}

	function currentCategory():String {
		if (isOwnerOptionsCategory()) {
			var menu = ownerMenus[categoryIndex - CodenameOptionsMenuModel.categories().length];
			return menu == null ? '' : Std.string(Reflect.field(menu, 'name'));
		}
		var categories = CodenameOptionsMenuModel.categories();
		return categoryIndex < 0 || categoryIndex >= categories.length ? '' : categories[categoryIndex];
	}

	function isOwnerOptionsCategory():Bool {
		var nativeCount = CodenameOptionsMenuModel.categories().length;
		return categoryIndex >= nativeCount && categoryIndex < nativeCount + ownerMenus.length;
	}

	function menuLabels():Array<String> {
		var labels = CodenameOptionsMenuModel.categories();
		for (menu in ownerMenus) labels.push(Std.string(Reflect.field(menu, 'name')));
		return labels;
	}

	function currentRows():Array<Dynamic> {
		if (!isOwnerOptionsCategory()) return CodenameOptionsMenuModel.rows(currentCategory());
		var menu:Dynamic = ownerMenus[categoryIndex - CodenameOptionsMenuModel.categories().length];
		var rows:Dynamic = menu == null ? null : Reflect.field(menu, 'options');
		return Std.isOfType(rows, Array) ? cast rows : [];
	}

	function refreshRows(motionDirection:Int = 0):Void {
		if (heading == null || rowGroup == null) return;
		rowMotionDirection = motionDirection;
		rowMotionTargetYs.resize(0);
		rowMotionActive = false;
		for (oldRow in rowGroup.members)
			if (oldRow != null) oldRow.destroy();
		rowGroup.clear();
		if (!inCategory) {
			heading.text = 'Options';
			var categories = menuLabels();
			for (index in 0...categories.length)
				addRow((index == rowIndex ? '> ' : '  ') + categories[index], index == rowIndex, index);
			help.text = 'Up/Down: choose   Enter: open   Backspace: return';
			return;
		}

		var category = currentCategory();
		heading.text = category;
		var rows = currentRows();
		var first = Std.int(Math.max(0, rowIndex - VISIBLE_ROWS + 1));
		for (index in first...Std.int(Math.min(rows.length, first + VISIBLE_ROWS))) {
			var row = rows[index];
			var label:String = Reflect.field(row, 'label');
			var customLocked = !isOwnerOptionsCategory()
				&& CodenameOptionsQualityCompat.isLocked(workingOptions, Reflect.field(row, 'field'));
			var value = isOwnerOptionsCategory()
				? (CodenameOwnerOptionsCompat.value(ownerOptionsSave, row) ? 'On' : 'Off')
				: CodenameOptionsMenuModel.valueText(workingOptions, row);
			if (customLocked) label += ' (locked)';
			addRow((index == rowIndex ? '> ' : '  ') + label + ': ' + value,
				index == rowIndex, index - first, customLocked);
		}
		if (isOwnerOptionsCategory()) {
			var ownerMenu:Dynamic = ownerMenus[categoryIndex - CodenameOptionsMenuModel.categories().length];
			var description = ownerMenu == null ? '' : Std.string(Reflect.field(ownerMenu, 'desc'));
			help.text = (description == 'null' ? '' : description + '   ')
				+ 'Up/Down: choose   Left/Right or Enter: toggle   Backspace: categories';
		} else help.text = 'Up/Down: choose   Left/Right: change   Enter: toggle   Backspace: categories'
			+ ((category == 'Appearance' || category == 'Graphics & Performance')
				? '   Quality locks advanced choices unless CUSTOM.' : '')
			+ ((category == 'Gameplay' || category == 'Controls & Timing')
				? '   Offset: Shift + Left/Right changes 20 ms.' : '');
	}

	function loadOwnerOptions():Void {
		var owner = CodenameModRuntime.activeRoot();
		if (owner == null || owner == '') return;
		var loaded = CodenameOwnerOptionsCompat.load(owner);
		ownerMenus = loaded.menus;
		var diagnostics:Array<String> = cast loaded.diagnostics;
		for (diagnostic in diagnostics) trace(diagnostic);
		if (ownerMenus.length == 0) return;
		try ownerOptionsSave = new CodenameOwnerSaveData(owner) catch (error:Dynamic)
			trace('[codename-options-save] Could not access selected-owner options: ' + Std.string(error));
	}

	function toggleOwnerOption(option:Dynamic):Void {
		if (ownerOptionsSave == null) {
			trace('[codename-options-save] Owner-defined options are unavailable because no private owner save is active.');
			return;
		}
		if (CodenameOwnerOptionsCompat.toggle(ownerOptionsSave, option)) refreshRows();
	}

	function addRow(text:String, selected:Bool, visibleIndex:Int, locked:Bool = false):Void {
		var targetY = FIRST_ROW_Y + visibleIndex * ROW_HEIGHT;
		var startOffset = selected ? rowMotionDirection * ROW_HEIGHT * 0.3 : 0;
		var row = new FlxText(78, targetY + startOffset,
			FlxG.width - 156, text, 22);
		row.setFormat(null, 22, selected ? FlxColor.YELLOW : (locked ? 0xFFAAAAAA : FlxColor.WHITE),
			LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		row.scale.set(ROW_SCALE, ROW_SCALE);
		row.scrollFactor.set();
		rowGroup.add(row);
		rowMotionTargetYs.push(targetY);
		if (startOffset != 0)
			rowMotionActive = true;
	}

	/** Move only the newly selected row; the shared host otherwise keeps its
		existing immediate refresh behavior for value and category changes. */
	function updateRowMotion(elapsed:Float):Void {
		if (!rowMotionActive || rowGroup == null) return;
		var amount = CoolUtil.timeAdjustedLerpAlpha(0.16, elapsed * ROW_MOTION_RATE);
		var stillMoving = false;
		var members = rowGroup.members;
		var index = 0;
		while (index < members.length) {
			var row = members[index];
			if (row != null && index < rowMotionTargetYs.length) {
				var targetY = rowMotionTargetYs[index];
				var distance = targetY - row.y;
				if (Math.abs(distance) < 0.1)
					row.y = targetY;
				else {
					row.y += distance * amount;
					stillMoving = true;
				}
			}
			index++;
		}
		rowMotionActive = stillMoving;
	}

	function commitOptions():Void {
		if (!optionsDirty || workingOptions == null) return;
		OptionsHandler.options = cast workingOptions;
		OptionsHandler.applyDisplayOptions(cast workingOptions);
		if (Main.fpsCounter != null) Main.fpsCounter.visible = Reflect.field(workingOptions, 'showFPS') == true;
		if (Main.memoryCounter != null) Main.memoryCounter.visible = Reflect.field(workingOptions, 'showMemory') == true;
		FlxG.autoPause = Reflect.field(workingOptions, 'autoPause') == true;
		optionsDirty = false;
	}

	function returnToOwnerMenu():Void {
		commitOptions();
		if (onExitCallback != null && Reflect.isFunction(onExitCallback)) {
			Reflect.callMethod(null, onExitCallback, [this]);
			return;
		}
		if (returnOwnerRoot != '' && returnScriptPath != ''
			&& CodenameModRuntime.isActiveOwner(returnOwnerRoot)) {
			var source = CodenameModRuntime.stateInit(returnOwnerRoot, returnScriptPath);
			if (Std.isOfType(source, FlxState)) {
				LoadingState.loadAndSwitchState(cast source);
				return;
			}
		}
		// Keep CodenameModRuntime's selected owner intact. Its global
		// session remains available when no imported-state caller was captured.
		LoadingState.loadAndSwitchState(new MainMenuState());
	}

	function reportUnsupportedSourceOptions():Void {
		var owner = CodenameModRuntime.activeRoot();
		var key = owner == null || owner == '' ? '<no-selected-owner>' : owner;
		if (reportedOptionGaps.exists(key)) return;
		reportedOptionGaps.set(key, true);
		trace('[codename-options-unsupported] The shared options host maps and persists quality and '
			+ 'week6PixelPerfect values; pixel-camera effects from imported scripts remain unverified. '
			+ 'LOW/HIGH gameplayShaders and lowMemoryMode values are available to owner scripts, but '
			+ 'engine-wide shader and memory effects remain unverified. Developer/config surfaces '
			+ '(devMode, allowConfigWarning, developer menu/console/reload actions, beta update controls, '
			+ 'and language selection) are not implemented'
			+ (ownerMenus.length == 0 ? '.' : '; selected-owner checkbox XML rows are available as menu categories.'));
	}

	/** Public Codename-compatible exit hook used by its menu base class. */
	@:keep public function exit():Void {
		if (hasExited) return;
		hasExited = true;
		returnToOwnerMenu();
	}
}
