package;

import flixel.FlxSprite;
import flixel.util.FlxColor;
import flixel.util.FlxSignal.FlxTypedSignal;

typedef NightmareVisionPlayFieldHooks = {
	?idChanged:(NightmareVisionPlayFieldView, Int, Int)->Void,
	?destroy:NightmareVisionPlayFieldView->Void,
	?generateReceptors:NightmareVisionPlayFieldView->Void,
	?clearReceptors:NightmareVisionPlayFieldView->Void,
	?addNote:(NightmareVisionPlayFieldView, Dynamic)->Void,
	?removeNote:(NightmareVisionPlayFieldView, Dynamic)->Void,
	?disposeNote:(NightmareVisionPlayFieldView, Dynamic)->Void,
	?hit:(Dynamic, NightmareVisionPlayFieldView)->Void,
	?miss:(Dynamic, NightmareVisionPlayFieldView)->Void,
	?missPress:Int->Void,
	?alpha:(NightmareVisionPlayFieldView, Float)->Void,
	?quants:(NightmareVisionPlayFieldView, Bool)->Void,
	?changeSkin:(NightmareVisionPlayFieldView, NightmareVisionNoteSkin)->Void,
	?fadeIn:(NightmareVisionPlayFieldView, Bool)->Void,
	?spawnSplash:(NightmareVisionPlayFieldView, Dynamic)->Dynamic,
	?spawnSusSplash:(NightmareVisionPlayFieldView, Dynamic, Bool)->Dynamic
}

/** Live source field flags over a native receptor bank. */
@:keep
class NightmareVisionPlayFieldView {
	/** Flixel source fields expose their mutable group ID to scripts. */
	@:keep public var ID(get, set):Int;
	var sourceID:Int = 0;
	/** The native line owns and updates the receptors; this view never copies them. */
	@:keep public var strumline:Strumline;
	/** Source PlayField.members is the live receptor array for this field. */
	@:keep public var members(get, never):Array<Strumline.StrumNote>;
	public var owner(default, set):Dynamic;
	public var singers:Array<Dynamic> = [];
	public var inControl(default, set):Bool = true;
	public var playerControls:Bool;
	public var playAnims:Bool = true;
	public var showRatings:Bool = true;
	public var noteSplashes:Bool = false;
	public var trackSustainSplashes:Bool = true;
	public var trackNoteSplashes:Bool = true;
	/** Actual owner-created Flixel groups. Writable pointers do not rewrite layer children. */
	@:keep public var grpSusSplashes:Dynamic;
	@:keep public var grpNoteSplashes:Dynamic;
	@:keep public var splashLayer:Dynamic;
	@:allow(PlayState) var ownedSplashLayer:Dynamic;
	@:allow(PlayState) var displayedSplashLayer:Dynamic;
	public function spawnSplash(note:Dynamic):Dynamic {
		if (nativeHooks == null || nativeHooks.spawnSplash == null) missingHook('spawnSplash');
		return nativeHooks.spawnSplash(this, note);
	}
	public function spawnSusSplash(note:Dynamic, isPlayer:Bool = false):Dynamic {
		if (nativeHooks == null || nativeHooks.spawnSusSplash == null) missingHook('spawnSusSplash');
		return nativeHooks.spawnSusSplash(this, note, isPlayer);
	}

	public var baseAlpha:Float = 1;
	public var holdDropLeniency:Float = 1 / 3;
	/** Source PlayField's mutable, field-owned FIELD underlay sprite. */
	@:keep public var underlaySpr:FlxSprite;
	@:keep public var underlayAlphaMult:Float = 1;
	public var autoPlayed(get, set):Bool;
	/** Stable live membership array, synchronized by the host when notes enter/leave. */
	public var notes(get, never):Array<Dynamic>;
	var noteMembers:Array<Dynamic> = [];
	public var onNoteHit:FlxTypedSignal<(Dynamic, NightmareVisionPlayFieldView)->Void>;
	public var onNoteMiss:FlxTypedSignal<(Dynamic, NightmareVisionPlayFieldView)->Void>;
	public var onMissPress:FlxTypedSignal<Int->Void>;
	public var baseX:Float = 0;
	public var baseY:Float = 0;
	public var player:Int;
	public var isPlayer:Bool;
	public var keyCount(default, set):Int = 4;
	public var alpha(default, set):Float = 1;
	public var quants(default, set):Bool = false;
	public var _skin:NightmareVisionNoteSkin;
	public var hasChangedSkin:Bool = false;
	var nativeHooks:NightmareVisionPlayFieldHooks;
	var destroyed:Bool = false;
	var autoOverride:Null<Bool>;
	var defaultAuto:Void->Bool;
	public function new(id:Int, defaultAuto:Void->Bool) {
		ID = id;
		// Nightmare Vision marks only field 1 as not player-controlled. Additional fields
		// follow the same BF-owned policy as field 0, even when they autoplay.
		playerControls = id != 1;
		isPlayer = id != 1;
		player = id;
		this.defaultAuto = defaultAuto;
		underlaySpr = new NightmareVisionFlxSprite().makeGraphic(1, 1, FlxColor.WHITE);
		underlaySpr.color = FlxColor.BLACK;
		underlaySpr.alpha = 0;
		underlaySpr.scrollFactor.set();
		onNoteHit = new FlxTypedSignal<(Dynamic, NightmareVisionPlayFieldView)->Void>();
		onNoteMiss = new FlxTypedSignal<(Dynamic, NightmareVisionPlayFieldView)->Void>();
		onMissPress = new FlxTypedSignal<Int->Void>();
		// Donor PlayField registers its own effect listener before callers can
		// register score listeners or script listeners. Binding never reorders it.
		onNoteHit.add(function(note, field) {
			if (nativeHooks == null || nativeHooks.hit == null) missingHook('hit');
			nativeHooks.hit(note, field);
		});
		onNoteMiss.add(function(note, field) {
			if (nativeHooks == null || nativeHooks.miss == null) missingHook('miss');
			nativeHooks.miss(note, field);
		});
		onMissPress.add(function(key) {
			if (nativeHooks == null || nativeHooks.missPress == null) missingHook('missPress');
			nativeHooks.missPress(key);
		});
	}
	public function bindNativeLifecycle(hooks:NightmareVisionPlayFieldHooks):Void {
		if (destroyed) throw '[nightmare-vision-playfield] Cannot bind a destroyed field';
		nativeHooks = hooks;
	}
	function missingHook(name:String):Void
		throw '[nightmare-vision-playfield] Unbound native lifecycle: ' + name;
	function get_ID():Int return sourceID;
	function set_ID(value:Int):Int {
		var oldID = sourceID;
		sourceID = value;
		if (oldID != value && nativeHooks != null && nativeHooks.idChanged != null)
			nativeHooks.idChanged(this, oldID, value);
		return value;
	}
	function get_notes():Array<Dynamic> return noteMembers;
	function set_inControl(value:Bool):Bool {
		if (!value) for (strum in members) if (strum != null) {
			strum.playAnim('static');
			strum.resetAnim = 0;
		}
		return inControl = value;
	}
	function set_keyCount(value:Int):Int {
		keyCount = value;
		if (members.length > 0) generateReceptors();
		return value;
	}
	function set_alpha(value:Float):Float {
		alpha = Math.max(0, Math.min(1, value));
		if (nativeHooks != null && nativeHooks.alpha != null) nativeHooks.alpha(this, alpha);
		return alpha;
	}
	function set_quants(value:Bool):Bool {
		quants = value;
		if (nativeHooks != null && nativeHooks.quants != null) nativeHooks.quants(this, value);
		return value;
	}
	public function generateReceptors():Void {
		if (nativeHooks == null || nativeHooks.generateReceptors == null) missingHook('generateReceptors');
		nativeHooks.generateReceptors(this);
	}
	public function clearReceptors():Void {
		if (nativeHooks == null || nativeHooks.clearReceptors == null) missingHook('clearReceptors');
		nativeHooks.clearReceptors(this);
	}
	public function fadeIn(skip:Bool = false):Void {
		if (nativeHooks == null || nativeHooks.fadeIn == null) missingHook('fadeIn');
		nativeHooks.fadeIn(this, skip);
	}
	public function changeSkin(skin:NightmareVisionNoteSkin):Void {
		if (nativeHooks == null || nativeHooks.changeSkin == null) missingHook('changeSkin');
		_skin = skin;
		hasChangedSkin = true;
		nativeHooks.changeSkin(this, skin);
	}
	public function addNote(note:Dynamic):Void {
		if (nativeHooks == null || nativeHooks.addNote == null) missingHook('addNote');
		noteMembers.push(note);
		nativeHooks.addNote(this, note);
	}
	public function removeNote(note:Dynamic):Void {
		if (nativeHooks == null || nativeHooks.removeNote == null) missingHook('removeNote');
		noteMembers.remove(note);
		nativeHooks.removeNote(this, note);
	}
	public function disposeNote(note:Dynamic):Void {
		if (nativeHooks == null || nativeHooks.disposeNote == null) missingHook('disposeNote');
		noteMembers.remove(note);
		nativeHooks.disposeNote(this, note);
	}
	public function getNotes(dir:Int, ?get:Dynamic->Bool):Array<Dynamic> {
		var collected:Array<Dynamic> = [];
		for (note in notes) if (note != null && note.alive && note.noteData == dir
			&& !note.wasGoodHit && !note.tooLate && note.canBeHit && (get == null || get(note))) collected.push(note);
		return collected;
	}
	public function getTapNotes(dir:Int):Array<Dynamic>
		return getNotes(dir, function(note) return !note.isSustainNote);
	public function getHoldNotes(dir:Int):Array<Dynamic>
		return getNotes(dir, function(note) return note.isSustainNote);
	public function forEachAliveNote(func:Dynamic->Void):Void {
		for (note in notes) if (note != null && note.exists && note.alive) func(note);
	}
	/** Signals/hooks are view-owned; native sprites and notes remain host-owned. */
	public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		if (nativeHooks != null && nativeHooks.destroy != null) nativeHooks.destroy(this);
		onNoteHit.removeAll(); onNoteHit.destroy();
		onNoteMiss.removeAll(); onNoteMiss.destroy();
		onMissPress.removeAll(); onMissPress.destroy();
		// Match the source field's ownership rule: only its current underlay is
		// destroyed here. Replacing the public field does not destroy the old sprite.
		if (underlaySpr != null) {
			underlaySpr.destroy();
			underlaySpr = null;
		}
		nativeHooks = null;
		defaultAuto = null;
		noteMembers.resize(0);
		owner = null;
		singers.resize(0);
		strumline = null;
		_skin = null;
	}
	function get_members():Array<Strumline.StrumNote>
		return strumline == null ? [] : strumline.members;
	function set_owner(value:Dynamic):Dynamic {
		owner = value;
		if (singers == null) singers = [];
		singers.remove(value);
		singers.unshift(value);
		return value;
	}
	function get_autoPlayed():Bool return autoOverride == null ? defaultAuto != null && defaultAuto() : autoOverride;
	function set_autoPlayed(value:Bool):Bool return autoOverride = value;
	public function canInput():Bool {
		var ownerStunned = owner != null && Reflect.field(owner, 'stunned') == true;
		return !destroyed && inControl && playerControls && !autoPlayed && !ownerStunned;
	}
}
