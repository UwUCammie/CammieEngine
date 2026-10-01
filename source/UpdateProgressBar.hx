package;

#if (sys && windows)
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/** Browsing-only view of the update helper's persistent job. */
class UpdateProgressBar extends FlxSpriteGroup {
	var label:FlxText;
	var fill:FlxSprite;
	var lastWidth:Int = -1;
	var pollTimer:Float = 0;

	public function new() {
		super(FlxG.width - 520, 8);
		var background = new FlxSprite(0, 0).makeGraphic(508, 56, FlxColor.fromRGB(12, 16, 25, 232));
		background.scrollFactor.set();
		add(background);
		label = new FlxText(12, 6, 484, '', 16);
		label.setFormat('assets/fonts/vcr.ttf', 16, FlxColor.WHITE);
		label.scrollFactor.set();
		add(label);
		var track = new FlxSprite(12, 37).makeGraphic(484, 10, FlxColor.fromRGB(55, 60, 69));
		track.scrollFactor.set();
		add(track);
		fill = new FlxSprite(12, 37).makeGraphic(484, 10, FlxColor.fromRGB(76, 220, 139));
		fill.scrollFactor.set();
		add(fill);
		visible = false;
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		pollTimer -= elapsed;
		if (pollTimer > 0) return;
		pollTimer = 0.1;
		var progress = UpdateChecker.installProgress();
		visible = progress != null;
		if (progress == null) return;
		label.text = progress.label;
		var width = Std.int(Math.max(0, Math.min(1, progress.fraction)) * 484);
		if (width != lastWidth) {
			lastWidth = width;
			fill.visible = width > 0;
			if (width > 0) {
				fill.setGraphicSize(width, 10);
				fill.updateHitbox();
			}
		}
	}
}
#end
