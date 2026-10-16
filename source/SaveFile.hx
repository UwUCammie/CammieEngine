package;

import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;

/** One save slot as a card in the Freeplay style: the slot's character icon,
 * its name, and once opened a LOAD or DELETE choice with a confirmation before
 * anything is erased. The slot state the options screen drives
 * (`beingSelected`, `askingToConfirm`, `selectingLoad`) is unchanged. */
class SaveFile extends MenuCard {
	static final characters:Array<String> = ['bf', 'bf-old', 'bf-pixel', 'spooky', 'dad', 'pico', 'mom', 'gf', 'monster', 'senpai'];
	static final names:Array<String> = ['Boyfriend', 'Classic Boyfriend', 'Pixel Boyfriend', 'Spooky Kids', 'Daddy Dearest',
		'Pico', 'Mommy Mearest', 'Girlfriend', 'Monster', 'Senpai'];

	public var slot(default, null):Int;
	public var playerIcon:HealthIcon;
	public var beingSelected:Bool = false;
	public var askingToConfirm:Bool = false;
	public var selectingLoad:Bool = true;
	public var isCurrent:Bool = false;
	var loadChip:FlxSprite;
	var deleteChip:FlxSprite;
	var loadLabel:FlxText;
	var deleteLabel:FlxText;

	public function new(saveNum:Int = 0, width:Int = 795) {
		super('Save ' + (saveNum + 1), width, 82, {idle: 52, selected: 100, titleSize: 22, selectedTitleSize: 26,
			titleTop: 14, titleLift: 4, captionTop: 58, captionSize: 14});
		slot = saveNum;
		selectingLoad = true;
		playerIcon = new HealthIcon(characters[saveNum % characters.length], false);
		setIcon(playerIcon);
		loadChip = MenuWidgets.rect(0, 0, 84, 26, MenuStyle.WHITE);
		deleteChip = MenuWidgets.rect(0, 0, 84, 26, MenuStyle.WHITE);
		loadLabel = MenuWidgets.text(0, 0, 84, 'LOAD', MenuStyle.SMALL_SIZE, MenuStyle.MUTED, FlxTextAlign.CENTER);
		deleteLabel = MenuWidgets.text(0, 0, 84, 'DELETE', MenuStyle.SMALL_SIZE, MenuStyle.MUTED, FlxTextAlign.CENTER);
		add(loadChip); add(deleteChip); add(loadLabel); add(deleteLabel);
		refreshState();
	}

	public function characterName():String return names[slot % names.length];

	public function setActive(on:Bool):Void {
		isCurrent = on;
		refreshState();
	}

	public function askToConfirm(?turnOn:Bool = true) {
		askingToConfirm = turnOn;
		if (playerIcon.animation.curAnim != null)
			playerIcon.animation.curAnim.curFrame = turnOn ? 1 : 0;
		refreshState();
	}

	public function beSelected(?selected:Bool = true) {
		beingSelected = selected;
		refreshState();
	}

	public function changeSelection() {
		selectingLoad = !selectingLoad;
		refreshState();
	}

	/** Text and colours for the slot's current step. */
	public function refreshState():Void {
		if (askingToConfirm) {
			setCaption('Erase this save for good?   ACCEPT: erase   BACK: keep it');
			caption.color = MenuStyle.PINK;
		} else if (beingSelected) {
			setCaption('Choose LOAD or DELETE, then confirm');
			caption.color = MenuStyle.MUTED;
		} else {
			setCaption(characterName() + (isCurrent ? '   Current save' : '') + '   ACCEPT: open');
			caption.color = MenuStyle.MUTED;
		}
		if (beingSelected) clearValue();
		else setValue(isCurrent ? 'CURRENT' : '', MenuStyle.TEAL, 120);
		var loadFocus = selectingLoad;
		loadChip.color = loadFocus ? MenuStyle.GOLD : MenuStyle.CHIP_OFF;
		deleteChip.color = !loadFocus ? (askingToConfirm ? MenuStyle.PINK : MenuStyle.GOLD) : MenuStyle.CHIP_OFF;
		loadLabel.color = loadFocus ? MenuStyle.BAR : MenuStyle.MUTED;
		deleteLabel.color = !loadFocus ? MenuStyle.BAR : MenuStyle.MUTED;
		drawPresentation(true);
	}

	override function drawPresentation(force:Bool):Void {
		super.drawPresentation(force);
		if (loadChip == null) return;
		var focus = motion.focus;
		var showChips = beingSelected && selected;
		loadChip.visible = deleteChip.visible = loadLabel.visible = deleteLabel.visible = showChips;
		var right = x + cardWidth - 16;
		deleteChip.setPosition(right - 84, y + 14 + focus * 4);
		loadChip.setPosition(deleteChip.x - 94, deleteChip.y);
		loadLabel.setPosition(loadChip.x, loadChip.y + 4);
		deleteLabel.setPosition(deleteChip.x, deleteChip.y + 4);
	}
}
