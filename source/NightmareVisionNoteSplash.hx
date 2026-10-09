package;

import Strumline.StrumNote;

typedef NightmareVisionNoteSplashOwner = NightmareVisionSustainSplash.NightmareVisionSustainSplashOwner;

/** The source tap sprite has its own texture cache and setup contract. */
@:keep
class NightmareVisionNoteSplash extends NightmareVisionSplashSprite {
	public var rgbGraphics:NightmareVisionRGBGraphics = new NightmareVisionRGBGraphics();
	public var colorSwap:NightmareVisionHSLColorSwap;
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
		NightmareVisionSpriteMethods.bind(this, owner.spriteOwner);
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
		rgbGraphics.legacyHSL = null;
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

	/** Historical PlayField uses HSL splash values captured after note-type setup. */
	public function setupLegacyNoteSplash(strum:StrumNote, note:Note, texture:String,
		field:NightmareVisionPlayFieldView):Void {
		_note = note; _strum = strum; data = note.noteData; player = field.player;
		skin = owner.skinForID(player);
		if (colorSwap == null) colorSwap = new NightmareVisionHSLColorSwap();
		rgbGraphics.legacyHSL = colorSwap;
		if (_textureLoaded != texture || animation.getByName('note0-1') == null) {
			frames = skin.loadNoteSplashFrames(texture);
			var prefixes = ['note splash purple 1', 'note splash blue 1', 'note splash green 1',
				'note splash red 1', 'note splash purple 1', 'LSLAMSPLASH', 'RSLAMSPLASH'];
			for (lane in 0...prefixes.length) for (variant in 1...3)
				animation.addByPrefix('note' + lane + '-' + variant, prefixes[lane], lane >= 5 ? 12 : 24, false);
			_textureLoaded = texture;
		}
		setPosition(strum.x - field.swagWidth * 0.95, strum.y - field.swagWidth * 0.95);
		scale.set(scale.x * field.scale, scale.y * field.scale); baseScale.copyFrom(scale);
		alpha = 1; antialiasing = true;
		colorSwap.hue = note.noteSplashHue;
		colorSwap.saturation = note.noteSplashSat;
		colorSwap.lightness = note.noteSplashBrt;
		animation.play('note' + data + '-' + flixel.FlxG.random.int(1, 2), true);
		offset.set(-20, -20);
		if (animation.curAnim != null) animation.curAnim.frameRate = 24 + flixel.FlxG.random.int(-2, 2);
		rgbGraphics.apply(this);
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
		owner = null; colorSwap = null; _note = null; _strum = null; skin = null; rgbGraphics = null;
		super.destroy();
	}
}
