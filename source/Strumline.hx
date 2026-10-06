package;

import flixel.group.FlxGroup;
import flixel.group.FlxSpriteGroup;
import flixel.FlxSprite;
import flixel.FlxBasic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.math.FlxPoint;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxSignal.FlxTypedSignal;
import Judgement.TUI;
#if desktop
import Sys;
import sys.FileSystem;
#end

class Strumline extends FlxTypedSpriteGroup<StrumNote> {
	public var type:String = 'normal';
	/** A source field draws its underlay immediately before its receptor bank. */
	public var sourceFieldBeforeDraw:Void->Void;
	/** Codename scripts use `playerStrums.onMiss` and `.cpu`; these fields
	 * forward to the matching source line while this remains the native group. */
	var codenameScriptView:CodenameStrumlineScriptView<Character> = new CodenameStrumlineScriptView<Character>();
	@:keep public var onMiss(get, never):FlxTypedSignal<Dynamic->Void>;
	function get_onMiss():FlxTypedSignal<Dynamic->Void>
		return codenameScriptView.onMiss;
	@:keep @:isVar public var cpu(get, set):Bool;
	function get_cpu():Bool return codenameScriptView.cpu;
	function set_cpu(value:Bool):Bool return codenameScriptView.cpu = value;

	@:keep public function bindCodenameInputLine(line:CodenameInputLine<Character>):Void
		codenameScriptView.bind(line);

	@:keep public function unbindCodenameInputLine():Void
		codenameScriptView.unbind();

	/** V-Slice/HXC name for the active note-style descriptor. */
	public var noteStyle:Dynamic;
	/** V-Slice owns scroll speed per strumline. Keep native/global speed as the
	 * default until a source script explicitly resets or changes this line. */
	@:keep public var scrollSpeed(get, set):Float;
	var sourceScrollSpeed:Null<Float> = null;
	function get_scrollSpeed():Float
		return sourceScrollSpeed != null ? sourceScrollSpeed : PlayState.daScrollSpeed;
	function set_scrollSpeed(value:Float):Float {
		if (Math.isFinite(value) && value > 0)
			sourceScrollSpeed = value;
		return get_scrollSpeed();
	}
	@:keep public function hasScrollSpeedOverride():Bool
		return sourceScrollSpeed != null;
	@:keep public function resetScrollSpeed(?newScrollSpeed:Null<Float>):Void {
		var chartSpeed = PlayState.SONG == null ? PlayState.daScrollSpeed : PlayState.SONG.speed;
		scrollSpeed = newScrollSpeed != null ? newScrollSpeed : chartSpeed;
	}
	/** Multiplier authored on a Codename source line. Keeping it on the native
	 * group lets resetStrums/changeType preserve the line's receptor sizing. */
	public var sourceStrumScale:Float = 1;
	/** Source engines can place each receptor by its visual center instead of
	 * the legacy lane's top-left anchor. Keep this policy across skin reloads. */
	public var centerReceptors:Bool = false;
	/**
	 * V-Slice calls the receptor group `strumlineNotes`.  The native fork
	 * already owns that group as this typed sprite group; return the live object
	 * instead of allocating a proxy whose members could drift from the arrows.
	 */
	public var strumlineNotes(get, never):FlxTypedSpriteGroup<StrumNote>;
	function get_strumlineNotes():FlxTypedSpriteGroup<StrumNote>
		return this;
	/** V-Slice keeps gameplay notes and hold sprites in separate live groups. */
	@:keep public var notes(get, never):HxcStrumlineNoteList;
	var hxcNotes:HxcStrumlineNoteList;
	function get_notes():HxcStrumlineNoteList {
		if (hxcNotes == null) hxcNotes = new HxcStrumlineNoteList(this, false);
		return hxcNotes;
	}
	@:keep public var holdNotes(get, never):HxcStrumlineNoteList;
	var hxcHolds:HxcStrumlineNoteList;
	function get_holdNotes():HxcStrumlineNoteList {
		if (hxcHolds == null) hxcHolds = new HxcStrumlineNoteList(this, true);
		return hxcHolds;
	}
	/** V-Slice replaces a scored line when a script selects another chart
	 * variation.  The state owns the actual note queues and performs the swap. */
	@:keep public function applyNoteData(values:Array<Dynamic>):Void {
		if (PlayState.instance != null)
			PlayState.instance.hxcApplyStrumlineNoteData(this, values);
	}
	/** Alias the donor scale view to Flixel's live group scale. */
	public var strumlineScale(get, never):FlxPoint;
	function get_strumlineScale():FlxPoint
		return scale;
	/** V-Slice donor read; this fork keeps one global downscroll option. */
	public var isDownscroll(get, never):Bool;
	function get_isDownscroll():Bool
		return OptionsHandler.options != null && OptionsHandler.options.downscroll;
	/**
	 * Script positions use this fork's lane coordinates. NoteStyleAlignment
	 * maps the donor's `-0.275 * STRUMLINE_SIZE` receptor anchor into render
	 * offsets, so it must not also be added to the host position here.
	 */
	public static var INITIAL_OFFSET:Float = 0;
	/** Per-line splash gate; the global options gate remains owned by PlayState. */
	public var showNotesplash:Bool = true;
	public var noAnims:Bool = false;
	public var currentKey:NoteKeys;
	public var noteSplashes:FlxTypedGroup<NoteSplash>;
	/** V-Slice hold-cover sprites are kept beside, rather than inside, the
	 * receptor group so they can render above notes without changing the old
	 * Strumline member type.  PlayState adds this group to the HUD layer. */
	public var noteHoldCovers:FlxTypedGroup<NoteHoldCover>;
	/**
	 * Donor scripts attach one-off effect sprites (splashes, covers, overlays)
	 * to the strumline container: `strumline.add(effect)`.  In V-Slice the
	 * receptors live in their own subgroup, so those sprites become siblings of
	 * the receptors and are never visited by receptor iteration.  This fork's
	 * Strumline *is* the receptor group, so `add` routes anything that is not a
	 * StrumNote into this attached layer, which this group updates and draws
	 * itself.  The receptor `members` array therefore only ever holds live
	 * receptors, and keyShit's typed receptor closures cannot receive a foreign
	 * sprite (which the native cast would silently null into a SIGSEGV).
	 */
	public var attachedEffects(default, null):FlxTypedGroup<FlxSprite>;
	var noteSpacing:Float = 1;
	public function new(x:Float, y:Float, type:String = 'normal', ?transition:Bool = false,
		?generateReceptors:Bool = true) {
		super(x, y);

		changeType(type, transition, false, generateReceptors);
	}

	public function changeType(type:String = 'normal', ?transition:Bool = false,
		?preserveAttachedEffects:Bool = false, ?generateReceptors:Bool = true) {
		// Splicing while iterating skips every other old receptor. Cancel intro
		// tweens too: the legacy API can replace arrows during the countdown.
		while (this.length > 0) {
			var spr = members[0];
			FlxTween.cancelTweensOf(spr);
			remove(spr, true);
			spr.destroy();
		}

		this.type = type;
		final daType = Reflect.field(Judgement.uiJson, type);
		// Keep a small engine-neutral descriptor for HXC note callbacks. Native
		// charts still use `type`; foreign scripts only need the authored id and
		// pixel flag when selecting generic note graphics.
		noteStyle = {id: type, isPixel: daType.isPixel, uses: daType.uses};
		for (field in Reflect.fields(daType))
			Reflect.setField(noteStyle, field, Reflect.field(daType, field));
		if (currentKey == null)
			currentKey = new NoteKeys(daType.uses);
		else
			currentKey.newKey(daType.uses);

		for (i in 0...(generateReceptors ? Note.NOTE_AMOUNT : 0)) {
			var babyArrow:StrumNote = new StrumNote(Note.swagWidth * i, 0, i, type, currentKey, this);
			if (sourceStrumScale != 1) babyArrow.resetStrumSize();
			add(babyArrow);
			if (babyArrow.codenameCreationEvent != null && PlayState.instance != null) {
				PlayState.instance.dispatchCodenameCreationCallback('onPostStrumCreation',
					babyArrow.codenameCreationEvent);
				PlayState.instance.markCodenameCreationVisual('strum',
					babyArrow.codenameCreationEvent.player, i,
					babyArrow.codenameAtlasApplied ? babyArrow.codenameAppliedAtlasPath
						: babyArrow.codenameCreationEvent.sprite, babyArrow.codenameAtlasApplied,
					0, 0);
			}
		}

		if (noteSplashes == null)
			noteSplashes = new FlxTypedGroup<NoteSplash>();
		else if (!preserveAttachedEffects) {
			for (splash in noteSplashes.members)
				if (splash != null) splash.destroy();
			noteSplashes.clear();
		}
		if (!preserveAttachedEffects) {
			var sploosh = new NoteSplash(0, 0, 0, type);
			noteSplashes.add(sploosh);
		}
		if (noteHoldCovers == null)
			noteHoldCovers = new FlxTypedGroup<NoteHoldCover>();
		else if (!preserveAttachedEffects) {
			for (cover in noteHoldCovers.members)
				if (cover != null) cover.kill();
			noteHoldCovers.clear();
		}
		if (!preserveAttachedEffects)
			clearAttachedEffects();

		if (centerReceptors) resetStrums();
		if (transition)
			transIn();
	}

	/**
	 * Receptor-only add.  Donor effect sprites are routed to `attachedEffects`
	 * with the same child propagation FlxTypedSpriteGroup.preAdd applies, so
	 * they behave like container children (position, alpha, scroll factor and
	 * cameras follow the strumline) without entering the receptor members.
	 * The runtime type is re-checked here because script callers reach `add`
	 * dynamically and the parameter may arrive nulled by a failed cast.
	 */
	override public function add(sprite:StrumNote):StrumNote {
		if (sprite == null) {
			trace('[hxc-strumline-effect] ignored a receptor add that arrived null '
				+ '(foreign sprite rejected by the typed receptor signature)');
			return null;
		}
		if (!Std.isOfType(sprite, StrumNote)) {
			attachEffect(sprite);
			return sprite;
		}
		return super.add(sprite);
	}

	/** Explicit script boundary: FlxSprite reaches this method before a typed
	 * StrumNote parameter can discard it on native targets. */
	public function addScriptSprite(sprite:FlxSprite):FlxSprite {
		if (sprite == null) return null;
		if (Std.isOfType(sprite, StrumNote))
			return add(cast sprite);
		attachEffect(sprite);
		return sprite;
	}

	override public function insert(position:Int, sprite:StrumNote):StrumNote {
		if (sprite != null && !Std.isOfType(sprite, StrumNote)) {
			attachEffect(sprite);
			return sprite;
		}
		return super.insert(position, sprite);
	}

	/** Remove through the same routing `add` used, so effects can leave again. */
	override public function remove(sprite:StrumNote, splice:Bool = false):StrumNote {
		if (sprite != null && attachedEffects != null && !Std.isOfType(sprite, StrumNote)
			&& attachedEffects.members.indexOf(sprite) >= 0) {
			attachedEffects.remove(sprite, splice);
			return sprite;
		}
		return super.remove(sprite, splice);
	}

	/** Apply the container-child propagation for a routed effect sprite. */
	function attachEffect(sprite:FlxSprite):Void {
		if (attachedEffects != null && attachedEffects.members.indexOf(sprite) >= 0)
			return;
		if (attachedEffects == null)
			attachedEffects = new FlxTypedGroup<FlxSprite>();
		sprite.x += x;
		sprite.y += y;
		sprite.alpha *= alpha;
		sprite.scrollFactor.copyFrom(scrollFactor);
		sprite.cameras = cameras;
		attachedEffects.add(sprite);
		trace('[hxc-strumline-effect] non-receptor sprite routed to '
			+ (attachedEffects.members.length) + '-deep attached effects layer ('
			+ Type.getClassName(Type.getClass(sprite)) + ')');
	}

	/**
	 * Live-receptors-only iteration for the native gameplay loops (keyShit,
	 * goodNoteHit, note positioning).  Skips null holes, destroyed/killed
	 * receptors and anything a foreign script smuggled into the members array:
	 * a typed `StrumNote` closure that receives such a member is nulled by the
	 * native cast and the first field read would fault.
	 */
	public function forEachReceptor(functionName:StrumNote->Void):Void {
		for (spr in members) {
			if (spr == null || !spr.exists || spr.animation == null)
				continue;
			if (!Std.isOfType(spr, StrumNote)) {
				// Defensive: a non-receptor member must never reach the typed
				// receptor closures.  Name it so the injecting path can be found.
				trace('[hxc-strumline-effect] skipped a non-receptor member ('
					+ Type.getClassName(Type.getClass(spr)) + ') during receptor iteration');
				continue;
			}
			functionName(spr);
		}
	}

	/** Attached effects update with the line, so scripts never need to add
	 * them to the state themselves. */
	function updateAttachedEffects(elapsed:Float):Void {
		if (attachedEffects != null)
			attachedEffects.update(elapsed);
	}

	/** Draw attached effects above the receptors, matching the donor layout
	 * where container children added after the receptors render on top. */
	function drawAttachedEffects():Void {
		if (attachedEffects != null)
			attachedEffects.draw();
	}

	function clearAttachedEffects():Void {
		if (attachedEffects == null)
			return;
		for (effect in attachedEffects.members)
			if (effect != null)
				effect.destroy();
		attachedEffects.clear();
	}

	public function transIn():Void {
		for (i in 0...this.length)  {
			var arrow = members[i];
			if (arrow.codenameIntroAnimationCancelled)
				continue;
			arrow.y -= 10;
			arrow.alpha = 0;
			FlxTween.tween(arrow, {y: arrow.y + 10, alpha: 1}, 1, {ease: FlxEase.circOut, startDelay: 0.5 + (0.2 * i)});
		}
	}

	public function resetStrums():Void {
		forEach(function(spr:StrumNote) {
			if (centerReceptors) {
				spr.resetStrumSize();
				spr.x = x + Note.swagWidth * (spr.ID + 0.5) - spr.width * 0.5;
				spr.y = y + Note.swagWidth * 0.5 - spr.height * 0.5;
				return;
			}
			spr.x = x + Note.swagWidth * sourceStrumScale * noteSpacing * spr.ID;
			if (Note.NOTE_AMOUNT > 4)
				spr.x -= (10 + 15 * (Note.NOTE_AMOUNT - 4) + (20 + (7 * (Note.NOTE_AMOUNT - 5))) * ID) * noteSpacing;
			spr.y = y + Note.swagWidth * 0.5 - Note.swagWidth * sourceStrumScale * 0.5;
			spr.resetStrumSize();
		});
	}

	/** Store the lane area's top-left origin so ordinary group translations
	 * still work, while receptor widths are centered within their own lanes. */
	public function setCenteredLayout(centerX:Float, centerY:Float):Void {
		centerReceptors = true;
		x = centerX - Note.swagWidth * Note.NOTE_AMOUNT * 0.5;
		y = centerY - Note.swagWidth * 0.5;
		resetStrums();
	}

	/**
	 * V-Slice donor strumline API: the X of one receptor lane relative to this
	 * line's own origin, so `line.x + line.getXPos(direction)` is the lane's
	 * live world position. Imported scripts (Vs Tricky's sign posts, hell-note
	 * splashes) use that pair to place HUD mechanics over the player's arrows;
	 * reading the live receptor keeps mania line counts and spacing moves exact.
	 */
	public function getXPos(direction:Float):Float {
		var count:Int = members.length;
		if (count <= 0)
			return 0;
		var lane:Int = Std.int(direction) % count;
		if (lane < 0)
			lane += count;
		var strum:StrumNote = members[lane];
		return strum == null ? 0 : strum.x - this.x;
	}

	/**
	 * V-Slice donor strumline API: hide and kill one note the donor stream no
	 * longer owns (hell/death note kinds cancel the native callback, so the
	 * engine never removes the sprite itself).
	 */
	public function killNote(note:Dynamic):Void {
		var native = NoteHoldCoverCompat.unwrap(note);
		if (native == null)
			return;
		if (Std.isOfType(native, FlxBasic)) {
			var sprite:FlxBasic = cast native;
			sprite.visible = false;
			sprite.kill();
		}
	}

	/**
	 * Adjust only receptor spacing.  This is safe for the existing four-lane
	 * group, while deliberately not pretending that Strumline owns the chart's
	 * pending-note/hold-note lifecycle used by donor extra-strumlines.
	 */
	public function setNoteSpacing(multiplier:Float = 1):Void {
		if (Math.isNaN(multiplier) || multiplier <= 0)
			return;
		noteSpacing = multiplier;
		resetStrums();
	}

	/** Set a Codename-authored receptor size multiplier while retaining the
	 * native note-style scale for later style swaps and spacing resets. */
	public function setSourceStrumScale(multiplier:Float = 1):Void {
		if (!Math.isFinite(multiplier) || multiplier <= 0)
			multiplier = 1;
		sourceStrumScale = multiplier;
		resetStrums();
		forEachReceptor(function(receptor:StrumNote) receptor.resetStrumSize());
	}

	/** Restore a hidden lane's receptors without changing note ownership. */
	public function fadeInArrows(?duration:Float = 0.2):Void {
		visible = true;
		alpha = 1;
		for (arrow in members) {
			if (arrow == null)
				continue;
			arrow.visible = true;
			FlxTween.cancelTweensOf(arrow);
			if (duration <= 0 || arrow.alpha >= 1)
				arrow.alpha = 1;
			else {
				if (arrow.alpha < 0)
					arrow.alpha = 0;
				FlxTween.tween(arrow, {alpha: 1}, duration);
			}
		}
	}

	public function doSplash(c:Int = 0) {
		var newsplash = noteSplashes.recycle(NoteSplash, () -> new NoteSplash(0, 0, 0, type));
		var playState = PlayState.instance;
		newsplash.nightmareVisionSkin = playState == null ? null
			: playState.nightmareVisionSkinForStrumline(this);
		newsplash.setupNoteSplash(members[c].x, members[c].y, c);
		RuntimeSmokeHarness.markNightmareVisionSplashVisual(newsplash);
		if (newsplash.nightmareVisionSkin != null)
			newsplash.setPosition(members[c].x + (members[c].width - newsplash.width) * 0.5,
				members[c].y + (members[c].height - newsplash.height) * 0.5);
		newsplash.sourceStrumline = this;
		noteSplashes.add(newsplash);
		return newsplash;
	}

	/** Play the authored V-Slice hold-cover layer for one hold note. */
	public function playNoteHoldCover(holdNote:Dynamic):Void {
		var ui:TUI = Reflect.field(Judgement.uiJson, type);
		if (ui == null || ui.holdCoverEnabled != true || holdNote == null)
			return;
		var nativeNote = unwrapHoldNote(holdNote);
		var headNote = resolveHoldHead(nativeNote);
		if (headNote == null)
			return;
		var rawLane:Dynamic = Reflect.field(headNote, 'noteData');
		if (rawLane == null)
			return;
		var lane = Std.int(Math.abs(Std.parseFloat(Std.string(rawLane)))) % Note.NOTE_AMOUNT;
		if (lane < 0 || lane >= members.length)
			return;
		var cover = noteHoldCovers.getFirstAvailable();
		if (cover == null) {
			cover = new NoteHoldCover(type);
			noteHoldCovers.add(cover);
		}
		cover.holdNote = headNote;
		cover.endTime = Reflect.field(headNote, 'strumTime') + Reflect.field(headNote, 'sustainLength');
		// Keep the authored head connected to its pooled effect. Sustain pieces
		// resolve back to this same head when they miss or are cancelled.
		Reflect.setField(headNote, 'cover', cover);
		cover.configurePosition(members[lane], ui);
		cover.playStart(lane);
	}

	/** End a hold cover before its authored sustain duration when a hold is
	 * released or cancelled. */
	public function endNoteHoldCover(holdNote:Dynamic):Void {
		if (holdNote == null || noteHoldCovers == null)
			return;
		var nativeNote = unwrapHoldNote(holdNote);
		var headNote = resolveHoldHead(nativeNote);
		for (cover in noteHoldCovers.members)
			if (cover != null && cover.holdNote == headNote)
				cover.playEnd();
		if (headNote != null && Reflect.hasField(headNote, 'cover'))
			Reflect.setField(headNote, 'cover', null);
	}

	/** End any active cover on a lane when the player releases that lane. */
	public function endNoteHoldCoverAtLane(lane:Int):Void {
		if (noteHoldCovers == null || lane < 0 || lane >= Note.NOTE_AMOUNT)
			return;
		for (cover in noteHoldCovers.members)
			if (cover != null && cover.direction == lane)
				cover.playEnd();
	}

	/** Remove a HXC wrapper and return the native note object it represents. */
	static function unwrapHoldNote(note:Dynamic):Dynamic {
		return NoteHoldCoverCompat.unwrap(note);
	}

	/** Resolve any sustain segment to its authored hold head. */
	static function resolveHoldHead(note:Dynamic):Dynamic {
		return NoteHoldCoverCompat.resolveHead(note);
	}

	/** Keep covers attached when a script moves or scales a strumline. */
	function updateNoteHoldCovers():Void {
		if (noteHoldCovers == null)
			return;
		var ui:TUI = Reflect.field(Judgement.uiJson, type);
		for (cover in noteHoldCovers.members)
			if (cover != null && cover.alive && cover.direction >= 0 && cover.direction < members.length)
				cover.configurePosition(members[cover.direction], ui);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		updateNoteHoldCovers();
		updateAttachedEffects(elapsed);
	}

	override public function draw():Void {
		if (sourceFieldBeforeDraw != null) sourceFieldBeforeDraw();
		super.draw();
		drawAttachedEffects();
	}

	override public function destroy():Void {
		sourceFieldBeforeDraw = null;
		if (attachedEffects != null) {
			attachedEffects.destroy();
			attachedEffects = null;
		}
		super.destroy();
	}
}

class StrumNote extends FlxSprite {
	/** Persistent source scale baseline, refreshed only after source skin loading. */
	var nightmareVisionBaseScalePoint:FlxPoint;
	@:keep public var baseScale(get, never):FlxPoint;
	@:keep public var defScale(get, set):FlxPoint;
	function get_baseScale():FlxPoint {
		if (nightmareVisionBaseScalePoint == null) {
			var currentScale = scale;
			nightmareVisionBaseScalePoint = FlxPoint.get(
				currentScale == null ? 1 : currentScale.x,
				currentScale == null ? 1 : currentScale.y);
		}
		return nightmareVisionBaseScalePoint;
	}
	function set_defScale(value:FlxPoint):FlxPoint {
		if (value == null) throw 'Nightmare Vision baseScale cannot be null';
		var point = get_baseScale();
		if (value != point) point.set(value.x, value.y);
		return point;
	}
	function get_defScale():FlxPoint {
		return get_baseScale();
	}

	/** Authored Nightmare Vision receptor offsets and colors for each animation. */
	public var nightmareVisionOffsets:Map<String, Array<Float>> = null;
	public var nightmareVisionPalette:PsychRGBPalette = null;
	override public function draw():Void {
		if (nightmareVisionRGB != null) nightmareVisionRGB.apply(this);
		super.draw();
	}

	public var nightmareVisionRGB:NightmareVisionRGBGraphics = null;
	/** Marks this receptor as source-owned even when its skin disables coloring. */
	@:keep public var nightmareVisionSource(default, set):Bool = false;
	@:keep public var isQuant:Bool = false;
	public var nightmareVisionQuantPrefs:Dynamic;
	/** Source PlayField keeps the animated alpha target separate from its field multiplier. */
	@:keep public var targetAlpha:Float = 1;
	@:keep public var alphaMult(default, set):Float = 1;
	@:keep public var resetAnim:Float = 0;
	/** Psych confirms use its source timer for autoplay and key release for manual input. */
	public var psychSourceTiming:Bool = false;
	@:keep public var coyoteTime:Float = 0;
	@:keep public var lastNote:Note;
	@:keep public var holding:Bool = false;
	@:keep public var sustainReduce:Bool = true;

	function set_nightmareVisionSource(value:Bool):Bool {
		if (value && !nightmareVisionSource) targetAlpha = alpha;
		nightmareVisionSource = value;
		if (value) super.set_alpha(targetAlpha * alphaMult);
		return value;
	}

	function set_alphaMult(value:Float):Float {
		alphaMult = value;
		if (nightmareVisionSource) super.set_alpha(targetAlpha * alphaMult);
		return value;
	}

	/** Preserve Flixel/Psych alpha writes unless this receptor belongs to NV. */
	override function set_alpha(value:Float):Float {
		if (!nightmareVisionSource) return super.set_alpha(value);
		targetAlpha = value;
		return super.set_alpha(targetAlpha * alphaMult);
	}
	/** Codename receptor scripts inspect the live animation name. */
	public function getAnim():String
		return animation.curAnim == null ? null : animation.curAnim.name;
	/** Invalidates delayed reset callbacks whenever a newer note confirms. */
	public var confirmationGeneration:Int = 0;
	/** Codename onStrumCreation can suppress the later line-entry tween. */
	@:keep public var codenameIntroAnimationCancelled:Bool = false;
	@:keep public function cancelCodenameIntroAnimation():Void
		codenameIntroAnimationCancelled = true;

	/** Psych 0.7.3 logical texture. Empty means the current chart's arrow skin. */
	public var texture(get, set):String;
	var psychTexture:String = '';
	var psychSkinOwner:String = null;
	var psychChartSkin:String = null;
	var psychPixelSkin:Bool = false;
	var psychSkinPostfix:String = '';
	var psychRGBDisabled:Bool = false;
	@:allow(PsychSkinRuntime) public var psychSkinUsesNativeDefaultFallback(default, null):Bool = false;
	var psychSkinConfigured:Bool = false;
	var psychRGBExplicitlyEnabled:Bool = false;
	var psychRGBShader:PsychRGBShaderReference = null;
	/** Psych keeps its typed reference; NV scripts receive the live source RGB view. */
	@:keep public var rgbShader(get, never):Dynamic;
	@:keep function get_rgbShader():Dynamic
		return hasNightmareVisionRGB() ? getNightmareVisionRGB() : psychRGBShader;
	/** Nightmare Vision's donor receptor field name for RGB graphics. */
	@:keep public var rgbGraphics(get, never):NightmareVisionRGBGraphics;
	@:keep function get_rgbGraphics():NightmareVisionRGBGraphics
		return hasNightmareVisionRGB() ? getNightmareVisionRGB() : null;

	function hasNightmareVisionRGB():Bool
		return nightmareVisionSource || nightmareVisionPalette != null || nightmareVisionRGB != null;

	function getNightmareVisionRGB():NightmareVisionRGBGraphics {
		if (nightmareVisionRGB == null)
			nightmareVisionRGB = new NightmareVisionRGBGraphics(nightmareVisionPalette);
		return nightmareVisionRGB;
	}
	/** Match the source receptor's lane/last-note fallback and pressed override. */
	@:keep public function handleColors(anim:String = '', ?note:Note):Void {
		if (!nightmareVisionSource || !useRGBShader) return;
		if (note == null) note = lastNote;
		lastNote = note;
		var graphics = getNightmareVisionRGB();
		if (note != null && note.nightmareVisionRGB != null)
			graphics.setColors(note.nightmareVisionRGB.getColors());
		else if (nightmareVisionPalette != null) graphics.palette.copyValues(nightmareVisionPalette);
		if (isQuant && anim == 'pressed')
			graphics.setColors(NightmareVisionQuantColorCompat.pressedColors(nightmareVisionQuantPrefs));
		graphics.enabled = nightmareVisionPalette != null && anim != 'static';
		graphics.apply(this);
	}
	public var useRGBShader(default, set):Bool = true;
	function set_useRGBShader(value:Bool):Bool {
		useRGBShader = value;
		if (psychSkinConfigured)
			psychRGBExplicitlyEnabled = value;
		refreshPsychRGB();
		return value;
	}
	function get_texture():String return psychTexture;
	function set_texture(value:String):String {
		if (value == null) value = '';
		if (psychSkinOwner == null) return psychTexture = value;
		if (value != psychTexture && PsychSkinRuntime.reloadStrum(this, value, psychSkinOwner,
			psychChartSkin, psychPixelSkin, psychSkinPostfix)) {
			psychTexture = value;
			configurePsychRGBShader();
			refreshPsychRGB();
		}
		return psychTexture;
	}

	/** Use the same cached palette and per-receptor mutation view as notes. */
	function configurePsychRGBShader():Void {
		var palette = PsychRGBPalette.defaultFor(ID, psychPixelSkin);
		if (psychRGBShader == null)
			psychRGBShader = new PsychRGBShaderReference(this, palette);
		else psychRGBShader.usePalette(palette);
	}

	public function configurePsychSkin(ownerRoot:String, arrowSkin:String, disableNoteRGB:Bool,
		pixel:Bool, ?postfix:String = ''):Bool {
		psychSkinConfigured = false;
		psychRGBExplicitlyEnabled = false;
		psychSkinOwner = ownerRoot;
		psychChartSkin = arrowSkin;
		psychPixelSkin = pixel;
		psychSkinPostfix = postfix;
		psychTexture = '';
		psychRGBDisabled = disableNoteRGB;
		useRGBShader = !disableNoteRGB;
		var wasVSlice = usesVSliceGeometry;
		usesVSliceGeometry = false;
		if (!PsychSkinRuntime.reloadStrum(this, '', ownerRoot, arrowSkin, pixel, postfix)) {
			usesVSliceGeometry = wasVSlice;
			return false;
		}
		configurePsychRGBShader();
		refreshPsychRGB();
		psychSkinConfigured = true;
		return true;
	}

	public function refreshPsychRGB():Void {
		if (psychSkinOwner == null) return;
		var hasExplicitRGB = psychRGBExplicitlyEnabled || psychRGBShader != null
			&& (psychRGBShader.hasCustomPalette || psychRGBShader.explicitlyEnabled);
		shader = (!psychSkinUsesNativeDefaultFallback || hasExplicitRGB)
			&& psychRGBShader != null && psychRGBShader.enabled && useRGBShader
			&& animation.curAnim != null && animation.curAnim.name != 'static'
			? psychRGBShader.parent.shader : null;
	}
	public var parentLine:Null<Strumline>;
	@:keep public var codenameCreationEvent:CodenameStrumCreationEvent = null;
	@:keep public var codenameAtlasApplied:Bool = false;
	@:keep public var codenameAppliedAtlasPath:String = null;
	public var type:String = 'normal';
	public var isPixel:Bool = false;
	/** Codename direction override for notes approaching this receptor. */
	@:keep public var noteAngle:Null<Float> = null;
	/** Psych independently controls a receptor's travel direction and scroll side. */
	@:keep public var direction:Float = 90;
	@:keep public var downScroll:Bool = false;
	public var normalSize:Float = 0.7;
	/** V-Slice receptor frame canvases and authored offsets need to be aligned
	 * after every atlas-frame change; classic/Psych receptors keep legacy rules. */
	var usesVSliceGeometry:Bool = false;
	var authoredStyleOffsetX:Float = 0;
	var authoredStyleOffsetY:Float = 0;
	var vSliceSourceFrameWidth:Float = 0;
	var vSliceSourceFrameHeight:Float = 0;
	/** Donor setup hitbox size, retained across static/press/confirm frames. */
	public var vSliceAnchorWidth(default, null):Float = 0;
	public var vSliceAnchorHeight(default, null):Float = 0;
	/** One snapshot per distinct animation canvas, with the receptor owning the
	 * cache so repeated frame updates do not allocate diagnostic payloads. */
	var smokeReceptorStates:Map<String, Bool>;

	/** Resolve the note path direction using Codename's per-note, per-strum, then visual-angle precedence. */
	@:keep public function getNotesAngle(?note:Note):Float {
		return CodenameNoteAngleCompat.resolve(note == null ? null : note.noteAngle, noteAngle, angle);
	}

	public function new(x:Float = 0, y:Float = 0, noteId:Int = 0, type:String = 'normal',
		?currentKey:NoteKeys, ?parentLine:Strumline) {
		super(x, y);
		this.parentLine = parentLine;
		downScroll = OptionsHandler.options != null && OptionsHandler.options.downscroll;

		var daType:Judgement.TUI = Reflect.field(Judgement.uiJson, type);

		if (currentKey == null)
			currentKey = new NoteKeys(type);

		this.ID = noteId;
		this.type = type;
		this.isPixel = daType.isPixel;
		usesVSliceGeometry = daType.vSliceAlias != null
			&& StringTools.trim(Std.string(daType.vSliceAlias)) != '';
		if (usesVSliceGeometry) {
			authoredStyleOffsetX = daType.strumlineOffsetX == null ? 0 : daType.strumlineOffsetX;
			authoredStyleOffsetY = daType.strumlineOffsetY == null ? 0 : daType.strumlineOffsetY;
		}
		var codenameVisualWasCancelled = false;
		var codenameAtlasPath = 'game/notes/default';
		var codenameInitialAnimPrefix = CodenameCreationVisual.strumAnimPrefix(noteId);
		var codenameOwnerActive = PlayState.instance != null
			&& PlayState.instance.codenameCreationOwnerRoot() != '';
		if (PlayState.instance != null
			&& (codenameOwnerActive
				|| PlayState.instance.hasCodenameCreationCallback('onStrumCreation')
				|| PlayState.instance.hasCodenameCreationCallback('onPostStrumCreation'))) {
			var player = PlayState.instance.codenameStrumCreationPlayer(parentLine);
			codenameCreationEvent = new CodenameStrumCreationEvent(this, player,
				noteId, codenameInitialAnimPrefix, codenameAtlasPath);
			PlayState.instance.dispatchCodenameCreationCallback('onStrumCreation', codenameCreationEvent);
			codenameVisualWasCancelled = codenameCreationEvent.cancelled;
			codenameAtlasPath = codenameCreationEvent.sprite;
			var selectedAtlasPath = CodenameCreationVisual.selectedAtlasPath(codenameOwnerActive,
				codenameAtlasPath, codenameVisualWasCancelled);
			if (selectedAtlasPath != null) {
				try {
					var ownerFrames = selectedAtlasPath == 'game/notes/default'
						? PlayState.instance.codenameDefaultNoteAtlasFrames()
						: new CodenamePaths(PlayState.instance.codenameCreationOwnerRoot())
							.getFrames(selectedAtlasPath);
					if (CodenameCreationVisual.applyStrumAtlas(this, ownerFrames,
							codenameCreationEvent.animPrefix,
							daType.strumlineScale == null ? 0.7 : daType.strumlineScale,
							true, PlayState.instance.codenameCreationOwnerRoot(), selectedAtlasPath)) {
						usesVSliceGeometry = false;
						codenameAtlasApplied = true;
						codenameAppliedAtlasPath = selectedAtlasPath;
					}
				} catch (error:Dynamic) {
					trace('[codename-strum-creation] Could not load selected-owner atlas '
						+ selectedAtlasPath + ': ' + Std.string(error));
				}
			}
		}

		var notePic;
		var noteXml:String = null;
		var assetStem = daType.strumlineAsset == null || StringTools.trim(daType.strumlineAsset) == ''
			? (isPixel ? 'arrows-pixels' : 'NOTE_assets') : Std.string(daType.strumlineAsset);
		if (!isPixel) {
			notePic = FNFAssets.getBitmapData('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".png");
			if (FNFAssets.exists('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".xml"))
				noteXml = FNFAssets.getText('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".xml");
		} else {
			notePic = FNFAssets.getBitmapData('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".png");
			if (FNFAssets.exists('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".xml"))
				noteXml = FNFAssets.getText('assets/images/custom_ui/ui_packs/' + daType.uses + '/' + assetStem + ".xml");
		}

		if (codenameVisualWasCancelled) {
			// Cancellable creation scripts own all visual setup after cancel().
		} else if (codenameAtlasApplied) {
			// The selected owner's atlas and metadata are already installed.
		} else if (noteXml != null) {
			frames = FlxAtlasFrames.fromSparrow(notePic, noteXml);
			if (usesVSliceGeometry) {
				// frames starts on the donor's first atlas frame; V-Slice calls
				// updateHitbox here, before switching to a direction's static frame.
				vSliceSourceFrameWidth = frameWidth;
				vSliceSourceFrameHeight = frameHeight;
			}

			final frameRateMult = isPixel ? 0.5 : 1;
			
			final flippedID = PlayState.flippedNotes ? Note.NOTE_AMOUNT - (ID + 1) : ID;
			final currentNote = currentKey.getData(flippedID);
			animation.addByPrefix('static', currentNote.idle, 24 * frameRateMult);
			animation.addByPrefix('pressed', currentNote.pressed, 24 * frameRateMult, false);
			animation.addByPrefix('confirm', currentNote.confirm, 24 * frameRateMult, false);
			if (currentNote.confirmHold != null && StringTools.trim(currentNote.confirmHold) != '')
				animation.addByPrefix('confirmHold', currentNote.confirmHold, 24 * frameRateMult, false);
			animation.play('static');
			
			antialiasing = !isPixel;
			if (usesVSliceGeometry) {
				var styleScale = daType.strumlineScale == null ? 0.7 : daType.strumlineScale;
				scale.set(styleScale, styleScale);
			}
			else if (isPixel)
				setGraphicSize(Std.int(width * 6));
			else
				setGraphicSize(Std.int(width * (daType.strumlineScale == null ? 0.7 : daType.strumlineScale)));
		} else {
			// Legacy pixel packs use a four-column, five-row sheet without XML.
			loadGraphic(notePic, true, 17, 17);
			final lane = ID % 4;
			final pixelID = PlayState.flippedNotes ? 3 - lane : lane;
			animation.add('static', [pixelID]);
			animation.add('pressed', [pixelID + 4, pixelID + 8], 12, false);
			animation.add('confirm', [pixelID + 12, pixelID + 16], 24, false);
			animation.play('static');
			antialiasing = false;
			setGraphicSize(Std.int(width * 6));
		}
		if (!codenameVisualWasCancelled && !codenameAtlasApplied
			&& codenameCreationEvent != null
			&& codenameCreationEvent.animPrefix != codenameInitialAnimPrefix) {
			if (noteXml != null) {
				// The default Sparrow atlas also supports Codename's mutable
				// direction prefix. Rebuild its animation names after native frames
				// are installed so the script's prefix takes effect even without an
				// atlas-path replacement.
				CodenameCreationVisual.setStrumPrefixes(this, codenameCreationEvent.animPrefix);
				if (animation.exists('static')) animation.play('static', true);
			} else if (ID == 0) {
				trace('[codename-strum-creation] animPrefix mutation needs a named-frame atlas; '
					+ 'the selected native pixel sheet has no prefix metadata');
			}
		}
		if (codenameAtlasApplied && animation.exists('static'))
			animation.play('static');

		var legacyResetSize = scale.x;
		if (Note.NOTE_AMOUNT > 4) {
			this.x -= 10 + 15 * (Note.NOTE_AMOUNT - 4) + (20 + (7 * (Note.NOTE_AMOUNT - 5))) * ID;
			if (isPixel) {
				scale.x = scale.x - 0.05 * (Note.NOTE_AMOUNT - 5) * 6;
				scale.y = scale.y - 0.05 * (Note.NOTE_AMOUNT - 5) * 6;
			} else {
				scale.x = scale.x - 0.05 * (Note.NOTE_AMOUNT - 5);
				scale.y = scale.y - 0.05 * (Note.NOTE_AMOUNT - 5);
			}
		} else if (Note.NOTE_AMOUNT < 4) {
			// maybe later
		}

		updateHitbox();
		// Retain the native/Psych size reset. Imported styles reset to their
		// post-mania scale so a spacing change cannot enlarge their receptors.
		normalSize = usesVSliceGeometry ? scale.x : legacyResetSize;
		if (usesVSliceGeometry)
			alignVSliceFrame();
		else if (!isPixel && (daType.strumlineOffsetX != null || daType.strumlineOffsetY != null))
			offset.set(daType.strumlineOffsetX == null ? 0 : daType.strumlineOffsetX,
				daType.strumlineOffsetY == null ? 0 : daType.strumlineOffsetY);
		scrollFactor.set();
	}

	public function playAnim(anim:String, force:Bool = false, reversed:Bool = false, frame:Int = 0) {
		if (parentLine != null && parentLine.noAnims)
			return;

		if (anim == 'confirm' || anim == 'confirmHold')
			confirmationGeneration++;
		animation.play(anim, force, reversed, frame);
		refreshPsychRGB();
		if (nightmareVisionOffsets != null) {
			centerOffsets();
			centerOrigin();
			var authored = nightmareVisionOffsets.get(anim);
			if (authored != null) offset.set(offset.x + authored[0], offset.y + authored[1]);
			handleColors(anim);
			return;
		}
		if (psychSkinOwner != null) {
			centerOffsets();
			centerOrigin();
			return;
		}
		if (usesVSliceGeometry) {
			// Preserve the donor receptor anchor and positive style-position shift
			// across differently sized source animation canvases;
			// the legacy confirm nudge belongs only to the native/Psych atlas path.
			alignVSliceFrame();
			markReceptorVisual();
			return;
		}

		if (animation.curAnim != null && (animation.curAnim.name == 'confirm' || animation.curAnim.name == 'confirmHold') && !isPixel) {
			centerOffsets();
			offset.x -= 13;
			offset.y -= 13;
		} else
			centerOffsets();
	}

	/** Recompute from the active Sparrow source canvas after Flixel changes a
	 * frame. The play call itself may not install its first frame until update. */
	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (nightmareVisionOffsets != null && coyoteTime > 0 && !holding)
			coyoteTime = Math.max(0, coyoteTime - elapsed);
		if (nightmareVisionOffsets != null || psychSourceTiming) {
			if (resetAnim > 0) {
				resetAnim -= elapsed;
				if (resetAnim <= 0) { resetAnim = 0; playAnim('static'); }
			}
		}
		if (usesVSliceGeometry) {
			alignVSliceFrame();
			markReceptorVisual();
		}
	}

	function alignVSliceFrame():Void {
		if (frameWidth <= 0 || frameHeight <= 0)
			return;
		vSliceAnchorWidth = vSliceSourceFrameWidth * Math.abs(scale.x);
		vSliceAnchorHeight = vSliceSourceFrameHeight * Math.abs(scale.y);
		offset.x = NoteStyleAlignment.vSliceReceptorOffsetX(frameWidth * Math.abs(scale.x), origin.x,
			scale.x, Note.swagWidth, authoredStyleOffsetX, vSliceAnchorWidth);
		offset.y = NoteStyleAlignment.vSliceReceptorOffsetY(frameHeight * Math.abs(scale.y), origin.y,
			scale.y, Note.swagWidth, authoredStyleOffsetY, vSliceAnchorHeight);
	}

	function markReceptorVisual():Void {
		if (!RuntimeSmokeHarness.enabled())
			return;
		var current = animation == null ? null : animation.curAnim;
		var animationName = current == null ? '' : current.name;
		var stateKey = animationName + '|' + frameWidth + '|' + frameHeight;
		if (smokeReceptorStates == null)
			smokeReceptorStates = new Map();
		if (smokeReceptorStates.exists(stateKey))
			return;
		smokeReceptorStates.set(stateKey, true);
		RuntimeSmokeHarness.markReceptorVisual(RuntimeSmokeVisuals.receptor(this, Note.swagWidth));
	}

	/** Select V-Slice's distinct held-confirm animation when the style defines one. */
	public function playConfirm(hold:Bool = false, force:Bool = true):Void {
		var target = hold && animation.exists('confirmHold') ? 'confirmHold' : 'confirm';
		playAnim(target, force);
	}

	public function resetStrumSize() {
		var sourceScale = parentLine == null ? 1 : parentLine.sourceStrumScale;
		scale.x = scale.y = normalSize * sourceScale;
		updateHitbox();
		if (usesVSliceGeometry) {
			alignVSliceFrame();
			markReceptorVisual();
		}
	}
}
