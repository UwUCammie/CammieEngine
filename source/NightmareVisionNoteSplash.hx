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
	public var historical(default, null):Bool = false;
	@:keep public var textureLoaded:Null<String>;
	var owner:NightmareVisionNoteSplashOwner;
	var _note:Note;
	var _strum:StrumNote;

	public function new(x:Float = 0, y:Float = 0, noteData:Int = 0, player:Int = 0,
		?owner:NightmareVisionNoteSplashOwner, historical:Bool = false) {
		super(x, y);
		if (owner == null) throw '[nightmare-vision-note-splash] Missing selected owner';
		this.owner = owner;
		this.historical = historical;
		NightmareVisionSpriteMethods.bind(this, owner.spriteOwner);
		data = noteData;
		this.player = player;
		if (historical) {
			skin = owner.skinForID(player);
			loadLegacyAnims(legacyTexture());
			colorSwap = new NightmareVisionHSLColorSwap();
			rgbGraphics.legacyHSL = colorSwap;
			setupLegacyCoordinates(x, y, noteData);
			antialiasing = owner.legacyAntialiasing == null ? true : owner.legacyAntialiasing();
			return;
		}
		loadAnims(owner.skinForID(player).splashTexture);
		var selected = owner.skinForID(player);
		if (selected != null) {
			scale.set(selected.splashScale, selected.splashScale);
			baseScale.copyFrom(scale);
		}
	}

	function loadAnims(texture:String):Void {
		if (historical) { loadLegacyAnims(texture); return; }
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

	/** Both source signatures share the native sprite and dispatch by source class identity. */
	public function setupNoteSplash(first:Dynamic, ?second:Dynamic, ?third:Dynamic,
		?fourth:Dynamic, ?fifth:Dynamic, saturation:Float = 0, brightness:Float = 0,
		?legacyField:NightmareVisionPlayFieldView):Void {
		if (historical) {
			setupLegacyCoordinates(first, second, third == null ? 0 : third, fourth,
				fifth == null ? 0 : fifth, saturation, brightness, legacyField);
			return;
		}
		var strum:StrumNote = cast first;
		var note:Note = cast second;
		var texture:String = cast third;
		var graphicsInput:NightmareVisionRGBGraphics = cast fourth;
		var field:NightmareVisionPlayFieldView = cast fifth;
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

	function legacyTexture():String {
		var texture = owner.legacySplashTexture == null ? null : owner.legacySplashTexture();
		return texture == null || texture.length == 0 ? 'noteSplashes' : texture;
	}

	function loadLegacyAnims(texture:String):Void {
		frames = owner.skinForID(player).loadNoteSplashFrames(texture);
		var prefixes = ['note splash purple 1', 'note splash blue 1', 'note splash green 1',
			'note splash red 1', 'note splash purple 1', 'LSLAMSPLASH', 'RSLAMSPLASH'];
		for (lane in 0...prefixes.length) for (variant in 1...3)
			animation.addByPrefix('note' + lane + '-' + variant, prefixes[lane], lane >= 5 ? 12 : 24, false);
		// The pinned historical loadAnims never assigns textureLoaded: repeated setup reloads.
	}

	public function setupLegacyCoordinates(x:Float, y:Float, lane:Int = 0, ?texture:String,
		hue:Float = 0, saturation:Float = 0, brightness:Float = 0, ?field:NightmareVisionPlayFieldView):Void {
		data = lane;
		if (field != null) {
			var spacing:Float = Reflect.getProperty(field.members[lane], 'swagWidth');
			setPosition(x - spacing * 0.95, y - spacing * 0.95);
		} else setPosition(x - Note.swagWidth * 0.95, y - Note.swagWidth);
		if (texture == null) texture = legacyTexture();
		if (textureLoaded != texture) loadLegacyAnims(texture);
		if (field != null) scale.set(scale.x * field.scale, scale.y * field.scale);
		baseScale.copyFrom(scale);
		if (colorSwap == null) colorSwap = new NightmareVisionHSLColorSwap();
		rgbGraphics.legacyHSL = colorSwap;
		alpha = 1; antialiasing = true;
		colorSwap.hue = hue; colorSwap.saturation = saturation; colorSwap.lightness = brightness;
		animation.play('note' + lane + '-' + flixel.FlxG.random.int(1, 2), true);
		offset.set(-20, -20);
		if (animation.curAnim == null) throw '[nightmare-vision-note-splash] Missing historical animation for lane ' + lane + ' in ' + texture;
		animation.curAnim.frameRate = 24 + flixel.FlxG.random.int(-2, 2);
		rgbGraphics.apply(this);
	}

	/** Existing native callers delegate to the same historical coordinate setup. */
	public function setupLegacyNoteSplash(strum:StrumNote, note:Note, texture:String,
		field:NightmareVisionPlayFieldView):Void {
		_note = note; _strum = strum; player = field.player; skin = owner.skinForID(player);
		setupLegacyCoordinates(strum.x, strum.y, note.noteData, texture,
			note.noteSplashHue, note.noteSplashSat, note.noteSplashBrt, field);
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
