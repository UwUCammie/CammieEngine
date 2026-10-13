package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;

typedef LibraryMenuAction = {var label:String; var run:Void->Void;}

/** Bounded, shared action presentation for host library management: a
 * centred popup over the dimmed menu behind it, with the chart it acts on
 * shown as a card above the choices. */
class LibraryMenuSubState extends MusicBeatSubstate {
	public static inline var PANEL_WIDTH:Int = LibraryMenuLayout.PANEL_WIDTH;
	public static inline var PANEL_HEIGHT:Int = LibraryMenuLayout.PANEL_HEIGHT;
	public static inline var ROW_PITCH:Int = LibraryMenuLayout.ROW_PITCH;
	public static inline var VISIBLE_ROWS:Int = LibraryMenuLayout.VISIBLE_ROWS;

	/** Shown as a card above the choices when set before create(). */
	public var cardTitle:String = '';
	public var cardCaption:String = '';
	var openingInputFrame:Int = -1;
	var actions:Array<LibraryMenuAction> = [];
	var selected:Int = 0;
	var rows:Array<FlxText> = [];
	var heading:FlxText;
	var status:FlxText;
	var highlight:FlxSprite;
	var marker:FlxSprite;
	var panelX:Float = 0;
	var panelY:Float = 0;
	var rowsY:Float = 0;
	var backAction:Void->Void;

	public function new() { super(); backAction = function() close(); }

	/** Dim the screen, then a translucent panel with a border, shadow and accent. */
	public static function buildPanel(state:flixel.group.FlxGroup, x:Float, y:Float, width:Int, height:Int):Void {
		var dim = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF05080F); dim.alpha = 0.58; state.add(dim);
		var shadow = new FlxSprite(x + 10, y + 12).makeGraphic(width, height, 0xFF000000); shadow.alpha = 0.35; state.add(shadow);
		var border = new FlxSprite(x - 2, y - 2).makeGraphic(width + 4, height + 4, 0xFF80E3D0); border.alpha = 0.55; state.add(border);
		var body = new FlxSprite(x, y).makeGraphic(width, height, 0xFF141C2C); body.alpha = 0.93; state.add(body);
		state.add(new FlxSprite(x, y).makeGraphic(width, 4, 0xFFFF66B7));
	}

	override function create():Void {
		openingInputFrame = FlxG.game.inputFrame;
		super.create();
		// A menu opened from this one draws its own panel in the same place.
		persistentDraw = false;
		panelX = Std.int((FlxG.width - PANEL_WIDTH) / 2); panelY = Std.int((FlxG.height - PANEL_HEIGHT) / 2);
		buildPanel(this, panelX, panelY, PANEL_WIDTH, PANEL_HEIGHT);
		heading = new FlxText(panelX + 28, panelY + 20, PANEL_WIDTH - 56, '', 24);
		heading.setFormat('assets/fonts/vcr.ttf', 24, 0xFFFFF4DC, LEFT); add(heading);
		var hasCard = cardTitle != '';
		if (hasCard) {
			// The same look as the selected card in the song list.
			var card = new FlxSprite(panelX + 24, panelY + 62).makeGraphic(PANEL_WIDTH - 48, 54, 0xFF354963); add(card);
			add(new FlxSprite(panelX + 24, panelY + 62).makeGraphic(5, 54, 0xFFFF66B7));
			var title = new FlxText(panelX + 44, panelY + 75, PANEL_WIDTH - 340, FreeplayBrowserLayout.label(cardTitle, 30), 22);
			title.setFormat('assets/fonts/vcr.ttf', 22, 0xFFFFF4DC, LEFT); title.wordWrap = false; add(title);
			var caption = new FlxText(panelX + PANEL_WIDTH - 300, panelY + 81, 260, FreeplayBrowserLayout.label(cardCaption.toUpperCase(), 26), 14);
			caption.setFormat('assets/fonts/vcr.ttf', 14, 0xFFCFD8E5, RIGHT); caption.wordWrap = false; add(caption);
		}
		rowsY = panelY + LibraryMenuLayout.rowsTop(hasCard);
		highlight = new FlxSprite(panelX + 16, rowsY).makeGraphic(PANEL_WIDTH - 32, ROW_PITCH - 6, 0xFF2B3C57); add(highlight);
		marker = new FlxSprite(panelX + 16, rowsY).makeGraphic(4, ROW_PITCH - 6, 0xFFFFD166); add(marker);
		for (i in 0...VISIBLE_ROWS) {
			var row = new FlxText(panelX + 32, rowsY + i * ROW_PITCH + 4, PANEL_WIDTH - 64, '', 20);
			row.setFormat('assets/fonts/vcr.ttf', 20, 0xFFFFFFFF, LEFT);
			row.wordWrap = false;
			rows.push(row); add(row);
		}
		status = new FlxText(panelX + 28, panelY + PANEL_HEIGHT - 92, PANEL_WIDTH - 56, '', 14);
		status.setFormat('assets/fonts/vcr.ttf', 14, 0xFFFFC86A, LEFT); add(status);
		add(new FlxSprite(panelX + 24, panelY + PANEL_HEIGHT - 42).makeGraphic(PANEL_WIDTH - 48, 1, 0xFF3A4A66));
		var hint = new FlxText(panelX + 28, panelY + PANEL_HEIGHT - 32, PANEL_WIDTH - 56,
			'UP/DOWN choose    ACCEPT select    BACK return', 14);
		hint.setFormat('assets/fonts/vcr.ttf', 14, 0xFF9DB2CC, CENTER); add(hint);
	}
	function showActions(title:String, entries:Array<LibraryMenuAction>, reset:Bool = true):Void {
		heading.text = title;
		actions = entries;
		if (reset || selected >= actions.length) selected = 0;
		render();
	}
	function render():Void {
		var first = LibraryMenuLayout.firstVisible(selected, actions.length, rows.length);
		highlight.visible = marker.visible = actions.length > 0;
		for (slot in 0...rows.length) {
			var index = first + slot;
			rows[slot].visible = index < actions.length;
			if (index >= actions.length) continue;
			var label = actions[index].label;
			if (label.length > 56) label = label.substr(0, 53) + '...';
			rows[slot].text = label;
			rows[slot].color = index == selected ? 0xFFFFD76A : 0xFFCFD8E5;
			if (index == selected) { highlight.y = rowsY + slot * ROW_PITCH; marker.y = highlight.y; }
		}
		status.text = UserLibrary.error != '' ? UserLibrary.error
			: (actions.length > 0 ? actions[selected].label + '\n' + (selected + 1) + ' / ' + actions.length : '');
	}
	override function update(elapsed:Float):Void {
		super.update(elapsed);
		// A parent may have cached Accept before Flixel resets input for its new child.
		if (FlxG.game.inputFrame == openingInputFrame) return;
		if (nativeControls.BACK) { backAction(); return; }
		if (actions.length == 0) return;
		if (nativeControls.UP_MENU) { selected = (selected + actions.length - 1) % actions.length; render(); }
		if (nativeControls.DOWN_MENU) { selected = (selected + 1) % actions.length; render(); }
		if (nativeControls.ACCEPT) actions[selected].run();
	}
}
