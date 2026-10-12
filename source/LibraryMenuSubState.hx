package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;

typedef LibraryMenuAction = {var label:String; var run:Void->Void;}

/** Bounded, shared action presentation for host library management. */
class LibraryMenuSubState extends MusicBeatSubstate {
	var openingInputFrame:Int = -1;
	var actions:Array<LibraryMenuAction> = [];
	var selected:Int = 0;
	var rows:Array<FlxText> = [];
	var heading:FlxText;
	var status:FlxText;
	var backAction:Void->Void;

	public function new() { super(); backAction = function() close(); }
	override function create():Void {
		openingInputFrame = FlxG.game.inputFrame;
		super.create();
		add(new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xFF101522));
		heading = new FlxText(40, 35, FlxG.width - 80, '', 28);
		heading.setFormat('assets/fonts/vcr.ttf', 28, 0xFFFFFFFF, CENTER); add(heading);
		for (i in 0...7) {
			var row = new FlxText(60, 118 + i * 55, FlxG.width - 120, '', 22);
			row.setFormat('assets/fonts/vcr.ttf', 22, 0xFFFFFFFF, LEFT);
			row.wordWrap = false;
			rows.push(row); add(row);
		}
		status = new FlxText(60, FlxG.height - 150, FlxG.width - 120, '', 18);
		status.setFormat('assets/fonts/vcr.ttf', 18, 0xFFFFC86A, LEFT); add(status);
		var hint = new FlxText(40, FlxG.height - 45, FlxG.width - 80,
			'Up/Down: choose   Accept: select   Back: return', 18);
		hint.setFormat('assets/fonts/vcr.ttf', 18, 0xFFCCCCCC, CENTER); add(hint);
	}
	function showActions(title:String, entries:Array<LibraryMenuAction>, reset:Bool = true):Void {
		heading.text = title;
		actions = entries;
		if (reset || selected >= actions.length) selected = 0;
		render();
	}
	function render():Void {
		var first = Std.int(Math.max(0, Math.min(selected - 3, actions.length - rows.length)));
		for (slot in 0...rows.length) {
			var index = first + slot;
			rows[slot].visible = index < actions.length;
			if (index >= actions.length) continue;
			var label = actions[index].label;
			if (label.length > 76) label = label.substr(0, 73) + '...';
			rows[slot].text = (index == selected ? '> ' : '  ') + label;
			rows[slot].color = index == selected ? 0xFFFFD76A : 0xFFFFFFFF;
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
