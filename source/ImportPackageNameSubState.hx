package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxSubState;
import flixel.addons.ui.FlxUIButton;
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
	var nextButton:FlxUIButton;
	var cancelButton:FlxUIButton;
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
		var shade = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, 0xB0000000);
		add(shade);
		add(new FlxSprite(x, y).makeGraphic(width, height, 0xFF20242B));

		var title = new FlxText(x + 24, y + 18, width - 48, 'Name this imported mod', 28);
		title.setFormat('assets/fonts/vcr.ttf', 28, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(title);

		progressText = new FlxText(x + 28, y + 67, width - 56, '', 16);
		progressText.setFormat('assets/fonts/vcr.ttf', 16, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		add(progressText);

		var explanation = new FlxText(x + 30, y + 102, width - 60,
			'This package has no authored mod name. Enter a Freeplay label to recognize it on future imports.', 17);
		explanation.setFormat('assets/fonts/vcr.ttf', 17, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		explanation.wordWrap = true;
		add(explanation);

		nameInput = new FlxUIInputText(x + 42, y + 169, width - 84, '', 22);
		nameInput.maxLength = 80;
		nameInput.background = true;
		nameInput.backgroundColor = FlxColor.WHITE;
		nameInput.color = FlxColor.BLACK;
		nameInput.caretColor = FlxColor.BLACK;
		nameInput.hasFocus = true;
		add(nameInput);

		statusText = new FlxText(x + 24, y + 207, width - 48, '', 15);
		statusText.setFormat('assets/fonts/vcr.ttf', 15, FlxColor.YELLOW, CENTER, OUTLINE, FlxColor.BLACK);
		add(statusText);

		nextButton = new FlxUIButton(x + width - 250, y + height - 58, 'Continue', function():Void submitCurrent());
		add(nextButton);
		cancelButton = new FlxUIButton(x + 28, y + height - 58, 'Cancel', function():Void cancelPrompt());
		add(cancelButton);
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
