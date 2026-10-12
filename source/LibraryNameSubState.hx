package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.addons.ui.FlxUIInputText;

/** Text entry with a controller-accessible character grid. */
class LibraryNameSubState extends MusicBeatSubstate {
	var openingInputFrame:Int = -1;
	var title:String;
	var initial:String;
	var submit:String->Bool;
	var input:FlxUIInputText;
	var status:FlxText;
	var selected:Int = 0;
	var keys:Array<String>;
	var cells:Array<FlxText> = [];

	public function new(title:String, initial:String, submit:String->Bool) {
		super(); this.title = title; this.initial = initial; this.submit = submit;
		keys = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'.split('');
		keys = keys.concat(['Space', 'Delete', 'Save', 'Cancel']);
	}
	override function create():Void {
		openingInputFrame = FlxG.game.inputFrame;
		super.create(); add(new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF101522));
		var heading = new FlxText(40, 40, FlxG.width - 80, title, 28);
		heading.setFormat('assets/fonts/vcr.ttf', 28, 0xFFFFFFFF, CENTER); add(heading);
		input = new FlxUIInputText(60, 120, FlxG.width - 120, initial, 24, 0xFFFFFFFF, 0xFF30384C);
		input.customFilterPattern = ~/[\x00-\x1F\x7F]/g;
		input.maxLength = 80; input.broadcastToFlxUI = false; input.hasFocus = true;
		input.caretIndex = input.text.length; add(input);
		var cellWidth = (FlxG.width - 120) / 10;
		for (i in 0...keys.length) {
			var cell = new FlxText(60 + (i % 10) * cellWidth, 215 + Std.int(i / 10) * 46, cellWidth - 4, keys[i], 18);
			cell.setFormat('assets/fonts/vcr.ttf', 18, 0xFFFFFFFF, CENTER); cells.push(cell); add(cell);
		}
		status = new FlxText(60, FlxG.height - 145, FlxG.width - 120, '', 18);
		status.setFormat('assets/fonts/vcr.ttf', 18, 0xFFFFC86A, CENTER); add(status);
		var hint = new FlxText(40, FlxG.height - 80, FlxG.width - 80,
			'Type a name, Enter: save, Esc: cancel\nTab: keyboard/grid   Controller: move and Accept a character', 18);
		hint.setFormat('assets/fonts/vcr.ttf', 18, 0xFFCCCCCC, CENTER); add(hint); render();
	}
	function render():Void {
		for (i in 0...cells.length) cells[i].color = !input.hasFocus && i == selected ? 0xFFFFD76A : 0xFFCCCCCC;
		status.text = UserLibrary.error;
	}
	static function verticalSelection(index:Int, direction:Int, count:Int):Int {
		var rowCount = Std.int(Math.ceil(count / 10));
		var row = (Std.int(index / 10) + direction + rowCount) % rowCount;
		return Std.int(Math.min(row * 10 + index % 10, count - 1));
	}
	function save():Void { if (submit(input.text)) close(); else render(); }
	override function update(elapsed:Float):Void {
		super.update(elapsed);
		// A parent may have cached Accept before Flixel resets input for its new child.
		if (FlxG.game.inputFrame == openingInputFrame) return;
		if (FlxG.keys.justPressed.TAB || FlxG.gamepads.anyJustPressed(ANY)) {
			input.hasFocus = FlxG.keys.justPressed.TAB ? !input.hasFocus : false; render();
		}
		if (input.hasFocus) {
			if (FlxG.keys.justPressed.ESCAPE) close();
			else if (FlxG.keys.justPressed.ENTER) save();
			return;
		}
		if (nativeControls.BACK) { close(); return; }
		if (nativeControls.LEFT_MENU) selected = (selected + keys.length - 1) % keys.length;
		if (nativeControls.RIGHT_MENU) selected = (selected + 1) % keys.length;
		if (nativeControls.UP_MENU) selected = verticalSelection(selected, -1, keys.length);
		if (nativeControls.DOWN_MENU) selected = verticalSelection(selected, 1, keys.length);
		if (nativeControls.ACCEPT) switch (keys[selected]) {
			case 'Save': save();
			case 'Cancel': close();
			case 'Delete': input.text = input.text.substr(0, Std.int(Math.max(0, input.text.length - 1)));
			default:
				if (input.text.length < 80) input.text += keys[selected] == 'Space' ? ' ' : keys[selected];
		}
		render();
	}
}
