package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxSubState;
import flixel.addons.ui.FlxUIInputText;
import flixel.text.FlxText;
import flixel.util.FlxColor;
import haxe.io.Path;
import ImportPackageNamePrompt.ImportPackageNameRequest;

/** Collect explicit display names for imported packages without authored
 * package metadata. Each root is shown separately so a multi-mod selection
 * never derives identity from an arbitrary archive or parent folder name. */
class ImportPackageNameSubState extends FlxSubState {
	var requests:Array<ImportPackageNameRequest>;
	var onComplete:Map<String, String>->Void;
	var index:Int = 0;
	var entered:Array<String> = [];
	var nameInput:FlxUIInputText;
	var progressText:FlxText;
	var statusText:FlxText;
	var nextButton:MenuButton;
	var cancelButton:MenuButton;
	var finished:Bool = false;

	public function new(requests:Array<ImportPackageNameRequest>,
		onComplete:Map<String, String>->Void) {
		super();
		this.requests = requests == null ? [] : requests.copy();
		this.onComplete = onComplete;
		bgColor = 0x00000000;
		for (_ in this.requests)
			entered.push('');
	}

	override public function create():Void {
		super.create();
		var width = Std.int(Math.min(680, FlxG.width - 48));
		var height = 310;
		var x = (FlxG.width - width) * 0.5;
		var y = (FlxG.height - height) * 0.5;
		// The same popup panel as the library menus: dimmed menu, shadow, teal
		// border and a pink cap.
		MenuWidgets.panel(this, x, y, width, height);

		var title = MenuWidgets.text(x + 28, y + 20, width - 56, 'Name this imported mod', 24, MenuStyle.CREAM);
		add(title);

		progressText = MenuWidgets.text(x + 28, y + 58, width - 56, '', MenuStyle.SMALL_SIZE, MenuStyle.TEAL);
		add(progressText);

		var explanation = MenuWidgets.text(x + 28, y + 92, width - 56,
			'This package has no authored mod name. Enter a Freeplay label to recognize it on future imports.', 16, MenuStyle.TEXT);
		explanation.wordWrap = true;
		add(explanation);

		nameInput = new FlxUIInputText(x + 28, y + 160, width - 56, '', 22);
		nameInput.maxLength = 80;
		nameInput.background = true;
		nameInput.backgroundColor = MenuStyle.CARD_SELECTED;
		nameInput.color = MenuStyle.WHITE;
		nameInput.caretColor = MenuStyle.GOLD;
		nameInput.hasFocus = true;
		add(nameInput);

		statusText = MenuWidgets.text(x + 28, y + 204, width - 56, '', 15, MenuStyle.AMBER);
		add(statusText);

		nextButton = new MenuButton('Continue', 190, 44, function():Void submitCurrent());
		nextButton.setPosition(x + width - 218, y + height - 66);
		nextButton.setLook(true, true);
		add(nextButton);
		cancelButton = new MenuButton('Cancel', 190, 44, function():Void cancelPrompt());
		cancelButton.setPosition(x + 28, y + height - 66);
		add(cancelButton);
		add(MenuWidgets.text(x + 222, y + height - 50, width - 444, 'ENTER continue   ESC cancel', 12, MenuStyle.MUTED, flixel.text.FlxText.FlxTextAlign.CENTER));
		showRequest();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (FlxG.keys.justPressed.ESCAPE)
			cancelPrompt();
		else if (FlxG.keys.justPressed.ENTER)
			submitCurrent();
	}

	function showRequest():Void {
		if (requests == null || index < 0 || index >= requests.length) {
			finishPrompt();
			return;
		}
		var request = requests[index];
		progressText.text = 'Package ' + (index + 1) + ' of ' + requests.length + '  ·  '
			+ Path.withoutDirectory(request.root);
		nameInput.text = entered[index] == '' ? (request.suggestedName == null ? '' : request.suggestedName) : entered[index];
		nameInput.caretIndex = nameInput.text.length;
		nameInput.hasFocus = true;
		statusText.text = '';
		nextButton.label.text = index + 1 == requests.length ? 'Import' : 'Continue';
	}

	function submitCurrent():Void {
		if (finished || nameInput == null || index >= requests.length)
			return;
		var value = StringTools.trim(nameInput.text);
		if (!ImportPackageNamePrompt.validName(value)) {
			statusText.text = 'Enter a single-line name with at most 80 characters.';
			nameInput.hasFocus = true;
			return;
		}
		entered[index] = value;
		index++;
		if (index >= requests.length)
			finishPrompt();
		else
			showRequest();
	}

	function finishPrompt():Void {
		if (finished)
			return;
		var overrides = ImportPackageNamePrompt.createOverrides(requests, entered);
		if (overrides == null) {
			statusText.text = 'A valid name is required for every package.';
			index = 0;
			showRequest();
			return;
		}
		finished = true;
		nameInput.hasFocus = false;
		var callback = onComplete;
		onComplete = null;
		if (callback != null)
			callback(overrides);
		close();
	}

	function cancelPrompt():Void {
		if (finished)
			return;
		finished = true;
		if (nameInput != null)
			nameInput.hasFocus = false;
		var callback = onComplete;
		onComplete = null;
		if (callback != null)
			callback(null);
		close();
	}
}
