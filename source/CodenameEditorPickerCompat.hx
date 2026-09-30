package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxSubState;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.ui.FlxButton;

/**
	Shared-runtime replacement for Codename's EditorPicker substate.

	The native project has a chart editor but does not ship Codename's character,
	stage, alphabet, or UI debug editors. Keep those source choices visible and
	report the missing adapters when selected instead of silently dropping them.
*/
@:keep
class CodenameEditorPickerCompat extends FlxSubState {
	static inline var WIKI_URL:String = 'https://codename-engine.com/';
	static inline var PANEL_WIDTH:Int = 460;
	static inline var PANEL_HEIGHT:Int = 480;
	static inline var ROW_HEIGHT:Int = 48;

	public var options:Array<Dynamic> = [];
	public var choiceButtons:Array<FlxButton> = [];
	public var backButton:FlxButton;
	public var curSelected:Int = 0;

	var initialized:Bool = false;

	public function new() {
		super();
		options = [
			{name:'Chart Editor', id:'chart', state:ChartingState,
				support:'partial', reason:'Codename CharterSelection song browsing is unavailable; this opens the native ChartingState.'},
			{name:'Character Editor', id:'character', state:null,
				support:'unsupported', reason:'No native Codename CharacterSelection or CharacterEditor adapter is available.'},
			{name:'Stage Editor', id:'stage', state:null,
				support:'unsupported', reason:'No native Codename StageSelection or stage editor adapter is available.'},
			{name:'Alphabet Editor', id:'alphabet', state:null,
				support:'unsupported', reason:'This project has no Codename AlphabetSelection editor.'}
		];
		#if (debug || debug_ui)
		options.push({name:'UI Debug State', id:'uiDebug', state:null,
			support:'unsupported', reason:'This project has no Codename UI debug state.'});
		#end
		options.push({name:'Wiki', id:'wiki', state:null, support:'supported',
			onClick:function():Void openWiki()});
	}

	override public function create():Void {
		super.create();
		if (initialized) return;
		initialized = true;

		var panelX = (FlxG.width - PANEL_WIDTH) * 0.5;
		var panelY = (FlxG.height - PANEL_HEIGHT) * 0.5;
		var shade = new FlxSprite(0, 0).makeGraphic(FlxG.width, FlxG.height, 0xB0000000);
		add(shade);
		add(new FlxSprite(panelX, panelY).makeGraphic(PANEL_WIDTH, PANEL_HEIGHT, 0xFF25252D));

		var title = new FlxText(panelX + 24, panelY + 18, PANEL_WIDTH - 48, 'Editor Picker', 24);
		title.alignment = FlxTextAlign.CENTER;
		add(title);
		var note = new FlxText(panelX + 24, panelY + 53, PANEL_WIDTH - 48,
			'Choices without a native editor remain listed and report their compatibility gap.', 12);
		note.alignment = FlxTextAlign.CENTER;
		add(note);

		var rowY = panelY + 92;
		for (index in 0...options.length) {
			var capturedIndex = index;
			var option:Dynamic = options[index];
			var buttonText = Std.string(Reflect.field(option, 'name'));
			var support = Reflect.field(option, 'support');
			if (support == 'partial') buttonText += '  (limited)';
			else if (support == 'unsupported') buttonText += '  (unavailable)';
			var button = new FlxButton(panelX + 56, rowY + index * ROW_HEIGHT, buttonText,
				function():Void choose(capturedIndex));
			styleButtonLabel(button);
			choiceButtons.push(button);
			add(button);
		}

		backButton = new FlxButton(panelX + 56, panelY + PANEL_HEIGHT - 62, 'Back', function():Void close());
		styleButtonLabel(backButton);
		add(backButton);
	}

	function styleButtonLabel(button:FlxButton):Void {
		var buttonWidth = PANEL_WIDTH - 112;
		button.setGraphicSize(buttonWidth, ROW_HEIGHT - 4);
		button.updateHitbox();
		if (button.label == null) return;

		// FlxButton starts with an 80px label field even when its graphic is
		// resized. Match the field to the hitbox and center it in every state.
		button.label.fieldWidth = buttonWidth;
		button.label.setFormat(null, 16, 0x333333, FlxTextAlign.CENTER);
		button.label.updateHitbox();
		var labelY = (ROW_HEIGHT - 4 - button.label.height) * 0.5;
		for (offset in button.labelOffsets) {
			offset.x = 0;
			offset.y = labelY;
		}
		button.label.x = button.x;
		button.label.y = button.y + labelY;
	}

	public function choose(index:Int):Void {
		if (index < 0 || index >= options.length) return;
		curSelected = index;
		var option:Dynamic = options[index];
		var support:String = Std.string(Reflect.field(option, 'support'));
		if (support == 'unsupported') {
			trace('[codename-editor-picker-unsupported] ' + Reflect.field(option, 'name') + ': '
				+ Reflect.field(option, 'reason'));
			return;
		}
		if (support == 'partial') {
			trace('[codename-editor-picker-partial] ' + Reflect.field(option, 'name') + ': '
				+ Reflect.field(option, 'reason'));
			LoadingState.loadAndSwitchState(new ChartingState());
			return;
		}
		var onClick:Dynamic = Reflect.field(option, 'onClick');
		if (onClick != null && Reflect.isFunction(onClick))
			Reflect.callMethod(option, onClick, []);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (FlxG.keys.justPressed.ESCAPE || FlxG.keys.justPressed.BACKSPACE)
			close();
		else if (FlxG.keys.justPressed.UP)
			curSelected = (curSelected + options.length - 1) % options.length;
		else if (FlxG.keys.justPressed.DOWN)
			curSelected = (curSelected + 1) % options.length;
		else if (FlxG.keys.justPressed.ENTER || FlxG.keys.justPressed.SPACE)
			choose(curSelected);
	}

	function openWiki():Void {
		CodenameOpenURLCompat.open(WIKI_URL, function(url:String):Void FlxG.openURL(url));
	}
}
