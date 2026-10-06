package;

import Strumline.StrumNote;

typedef NightmareVisionNoteSplashOwner = NightmareVisionSustainSplash.NightmareVisionSustainSplashOwner;

/** The source tap sprite has its own texture cache and setup contract. */
@:keep
class NightmareVisionNoteSplash extends NightmareVisionSplashSprite {
	public var rgbGraphics:NightmareVisionRGBGraphics = new NightmareVisionRGBGraphics();
	public var noteData:Int = 0;
	public var data(get, set):Int;
	function get_data():Int return noteData;
	function set_data(value:Int):Int return noteData = value;
	public var player:Int = 0;
	public var skin:NightmareVisionNoteSkin;
	public var _textureLoaded:Null<String>;
	var owner:NightmareVisionNoteSplashOwner;
	var _note:Note;
	var _strum:StrumNote;

	public function new(x:Float = 0, y:Float = 0, noteData:Int = 0, player:Int = 0,
		?owner:NightmareVisionNoteSplashOwner) {
		super(x, y);
		if (owner == null) throw '[nightmare-vision-note-splash] Missing selected owner';
		this.owner = owner;
		data = noteData;
		this.player = player;
		loadAnims(owner.skinForID(player).splashTexture);
		var selected = owner.skinForID(player);
		if (selected != null) {
			scale.set(selected.splashScale, selected.splashScale);
			baseScale.copyFrom(scale);
		}
	}

	function loadAnims(texture:String):Void {
		var selected = owner.skinForID(player);
		frames = selected.loadNoteSplashFrames(texture);
		var metadata = selected.splashAnims;
		if (metadata == null) {
			var defaults:Dynamic = {};
			NightmareVisionNoteSkin.resolveData(defaults);
			metadata = cast defaults.noteSplashAnimations;
		}
		for (direction in 0...selected.keys) {
			var entry = metadata[direction];
			if (entry == null || entry.anim == null || entry.xmlName == null) continue;
			animation.addByPrefix(entry.anim, entry.xmlName, 24, false);
			addOffset(entry.anim, entry.offsets[0], entry.offsets[1]);
		}
		_textureLoaded = texture;
	}

	public function setupNoteSplash(strum:StrumNote, ?note:Note, ?texture:String,
		?graphicsInput:NightmareVisionRGBGraphics, ?field:NightmareVisionPlayFieldView):Void {
		_note = note;
		_strum = strum;
		data = note == null ? 0 : note.noteData;
		player = field == null ? 0 : field.player;
		skin = owner.skinForID(player);
		antialiasing = skin.antialiasing;
		if (texture == null) texture = 'noteSplashes';
		if (_textureLoaded != texture) loadAnims(texture);
		updateHitbox();
		playAnim('note$data', true);
		setColors(graphicsInput == null ? null : graphicsInput.getColors());
		if (!field.trackNoteSplashes) positionOnReceptor();
	}

	public function setColors(?colors:Array<Int>):Void {
		if (colors == null) return;
		rgbGraphics.enabled = skin.inEngineColoring;
		rgbGraphics.setColors(colors);
	}

	function positionOnReceptor():Void {
		if (_strum == null) return;
		var selected = owner.skinForID(player);
		var offsets = selected.splashOffsets == null ? null : selected.splashOffsets[data];
		setPosition(_strum.x + (_strum.width - width) * 0.5, _strum.y + (_strum.height - height) * 0.5);
		spriteOffset.set(offsets == null ? 0 : offsets.x, offsets == null ? 0 : offsets.y);
	}

	override public function update(elapsed:Float):Void {
		if (animation.curAnim != null && animation.curAnim.finished) kill();
		super.update(elapsed);
	}
	override public function draw():Void { rgbGraphics.apply(this); super.draw(); }
	override public function destroy():Void {
		owner = null; _note = null; _strum = null; skin = null; rgbGraphics = null;
		super.destroy();
	}
}
