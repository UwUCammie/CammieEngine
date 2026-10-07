package;

import Strumline.StrumNote;
using StringTools;

typedef NightmareVisionSustainSplashOwner = {
	var skinForID:Int->NightmareVisionNoteSkin;
	var noteSplashType:Void->String;
	@:optional var spriteOwner:Null<NightmareVisionSpriteOwner>;
}

/** The source tail-driven effect, independent of the native V-Slice hold-cover timer. */
@:keep
class NightmareVisionSustainSplash extends NightmareVisionSplashSprite {
	public var rgbGraphics:NightmareVisionRGBGraphics = new NightmareVisionRGBGraphics();
	public var noteData:Int = 0;
	public var data(get, set):Int;
	function get_data():Int return noteData;
	function set_data(value:Int):Int return noteData = value;
	public var player:Int = 0;
	public var completed:Bool = false;
	public var _textureLoaded:Null<String>;
	public var skin:NightmareVisionNoteSkin;
	var owner:NightmareVisionSustainSplashOwner;
	var _note:Note;
	var _strum:StrumNote;
	var __tail:Note;
	var __isPlayer:Bool = false;

	public function new(x:Float = 0, y:Float = 0, noteData:Int = 0, player:Int = 0,
		?owner:NightmareVisionSustainSplashOwner) {
		super(x, y);
		if (owner == null) throw '[nightmare-vision-sustain-splash] Missing selected owner';
		this.owner = owner;
		NightmareVisionSpriteMethods.bind(this, owner.spriteOwner);
		// Source uses the argument to select constructor frames, without storing either argument.
		addAnims(owner.skinForID(player));
	}

	function addAnims(selected:NightmareVisionNoteSkin):Void {
		frames = selected.loadSustainSplashFrames();
		var direction = -1;
		for (group in selected.susSplashAnims) {
			direction++;
			for (anim in group) {
				var name = '${anim.anim}$direction';
				animation.addByPrefix(name, anim.xmlName, anim.fps, anim.looping);
				addOffset(name, anim.offsets[0], anim.offsets[1]);
			}
		}
		// Source installs a new listener on each setup, including recycled instances.
		animation.onFinish.add(function(anim:String) {
			if (anim.indexOf('start') >= 0) playAnim('loop$data', false);
			if (anim.indexOf('end') >= 0) kill();
		});
	}

	public function setColors(?colors:Array<Int>):Void {
		if (colors == null || skin == null) return;
		rgbGraphics.enabled = skin.inEngineColoring;
		rgbGraphics.setColors(colors);
	}

	public function setupSplash(strum:StrumNote, ?note:Note, time:Float = 0.5,
		isPlayer:Bool = false, ?graphicsInput:NightmareVisionRGBGraphics, ?field:NightmareVisionPlayFieldView):Void {
		_note = note;
		_strum = strum;
		data = note.noteData;
		visible = true;
		angle = 0;
		alpha = 1;
		player = field == null ? 0 : field.player;
		skin = owner.skinForID(player);
		antialiasing = skin.antialiasing;
		scale.set(skin.susSplashScale, skin.susSplashScale);
		baseScale.copyFrom(scale);
		addAnims(skin);
		updateHitbox();
		playAnim('start$data', true);
		setColors(graphicsInput == null ? null : graphicsInput.getColors());
		updatePosition();
		findTail(note);
		__isPlayer = isPlayer;
	}

	function findTail(note:Null<Note>):Void {
		__tail = note;
		if (__tail != null && __tail.tail.length > 0) __tail = __tail.tail[__tail.tail.length - 1];
	}
	function watchTail():Void {
		if (__tail == null || __tail.garbage) { kill(); return; }
		if (__tail.wasGoodHit) completed = true;
		if (!__tail.alive && !getAnimName().startsWith('end')) {
			completed = true;
			var preference = owner.noteSplashType();
			if (__isPlayer && (preference == 'Both' || preference == 'Hold Covers')) playAnim('end$data', true);
			else kill();
		}
	}
	function updatePosition():Void {
		if (_strum == null) return;
		var selected = owner.skinForID(player);
		var offsets = selected.sustainSplashOffsets == null ? null : selected.sustainSplashOffsets[data];
		setPosition(_strum.x + (_strum.width - width) * 0.5, _strum.y + (_strum.height - height) * 0.5);
		spriteOffset.set(offsets == null ? 0 : offsets.x, offsets == null ? 0 : offsets.y);
	}
	override public function update(elapsed:Float):Void { super.update(elapsed); watchTail(); }
	override public function draw():Void { rgbGraphics.apply(this); super.draw(); }

	override public function destroy():Void {
		owner = null; _note = null; _strum = null; __tail = null; skin = null;
		rgbGraphics = null;
		super.destroy();
	}
}
