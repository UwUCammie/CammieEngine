package;

import animate.FlxAnimate;
import flixel.FlxCamera;
import flixel.math.FlxMatrix;
import flixel.math.FlxRect;

/** Historical NV flxanimate constructor over the existing native Animate renderer. */
@:keep
@:access(animate.FlxAnimate)
class NightmareVisionLegacyFlxAnimate extends FlxAnimate {
	public var sourceAnim(default, null):SourceLegacyAnimateController;
	public var showPivot(get, set):Bool;
	public var releaseBinding:Void->Void;
	var assets:Dynamic;
	var ownerNamespace:String;
	var owner:NightmareVisionSpriteOwner;
	var validFrame:Bool = false;
	var destroyed:Bool = false;
	var stageMatrix:FlxMatrix;
	var rendererSymbol:String;

	public function new(x:Float = 0, y:Float = 0, ?path:String, ?settings:Dynamic,
		assets:Dynamic, owner:NightmareVisionSpriteOwner, ownerNamespace:String) {
		super(x, y);
		this.assets = assets; this.owner = owner; this.ownerNamespace = ownerNamespace;
		stageMatrix = new FlxMatrix();
		sourceAnim = new SourceLegacyAnimateController(renderFrame, requireActive, function(message) trace(message));
		if (path != null) loadAtlas(path);
		if (settings != null) {
			if (settings.ButtonSettings != null) throw '[legacy-animate] Button settings are not implemented';
			if (settings.Reversed != null) sourceAnim.reversed = settings.Reversed;
			if (settings.FrameRate != null) sourceAnim.framerate = settings.FrameRate > 0 ? sourceAnim.metadata.frameRate : settings.FrameRate;
			if (settings.OnComplete != null) sourceAnim.onComplete = settings.OnComplete;
			if (settings.ShowPivot != null) showPivot = settings.ShowPivot;
			if (settings.Antialiasing != null) antialiasing = settings.Antialiasing;
			if (settings.ScrollFactor != null) scrollFactor = settings.ScrollFactor;
			if (settings.Offset != null) offset = settings.Offset;
		}
	}
	function requireActive():Void {
		if (destroyed) throw '[legacy-animate] Sprite has been destroyed';
		owner.requireActive();
	}
	public function loadAtlas(path:String):Void {
		requireActive();
		var loaded = SourceAnimateAtlasLoader.load(path, assets, requireActive, ownerNamespace);
		frames = loaded.frames;
		rendererSymbol = null;
		stageMatrix.copyFrom(library.matrix);
		var data:animate.FlxAnimateJson.AnimationJson = cast loaded.data;
		var inventory:Array<{name:String, length:Int}> = [];
		inventory.push({name:data.AN.SN, length:library.timeline.frameCount});
		if (data.SD != null) {
			for (entry in data.SD) {
				var symbol = library.getSymbol(entry.SN);
				if (symbol != null) inventory.push({name:entry.SN, length:symbol.timeline.frameCount});
			}
		}
		origin.set(0, 0);
		if (data.AN.STI != null && data.AN.STI.TRP != null) {
			var point = data.AN.STI.TRP;
			origin.set(point.x, point.y);
		}
		var stage = data.AN.STI;
		// The exported stage can instance another named symbol in the dictionary.
		sourceAnim.load(data.AN.N, library.frameRate, stage == null ? data.AN.SN : stage.SN, inventory,
			stage == null ? 0 : stage.FF, stage == null ? "LP" : stage.LP, stage == null ? "G" : stage.ST);
	}
	function renderFrame(symbol:String, frame:Int):Void {
		validFrame = frame >= 0;
		if (!validFrame) return;
		if (rendererSymbol != symbol) {
			if (symbol == library.timeline.name) anim.addByTimeline('__source', library.timeline, 0, false);
			else anim.addBySymbol('__source', symbol, 0, false);
			anim.play('__source', true);
			anim.pause(); rendererSymbol = symbol;
		}
		anim.curAnim.curFrame = frame;
	}
	override function updateAnimation(elapsed:Float):Void {
		if (sourceAnim != null) sourceAnim.update(elapsed);
	}
	override public function draw():Void {
		if (validFrame) super.draw();
	}
	override function prepareAnimateMatrix(matrix:FlxMatrix, camera:FlxCamera, bounds:FlxRect):Void {
		// Recover authored timeline coordinates before applying the selected source
		// instance transform. Never mutate the shared library stage matrix.
		matrix.translate(bounds.x, bounds.y);
		if (sourceAnim.stageSelected) matrix.concat(stageMatrix);
		else matrix.translate(sourceAnim.instanceX, sourceAnim.instanceY);
		super.prepareAnimateMatrix(matrix, camera, bounds);
	}
	function get_showPivot():Bool return false;
	function set_showPivot(value:Bool):Bool {
		if (value) throw '[legacy-animate] Pivot drawing is not implemented';
		return false;
	}
	override public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		if (releaseBinding != null) {releaseBinding(); releaseBinding = null;}
		if (sourceAnim != null) sourceAnim.destroy();
		assets = null; owner = null; stageMatrix = null;
		super.destroy();
	}
}
