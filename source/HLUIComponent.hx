package;

import flixel.FlxBasic;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.math.FlxPoint;
import flixel.util.FlxColor;
import flixel.util.FlxDestroyUtil;

/** Small native implementation of the public HL17 UI component surface.

	The HL17 donor ships window scripts but not the original HLUI framework.
	This component is intentionally limited to methods and fields those scripts
	use. Owner paths and interpreter cleanup are injected by CodenameScriptInterp.
*/
@:keep
class HLUIComponent extends FlxSprite {
	public var componentWidth:Float = 0;
	public var componentHeight:Float = 0;
	public var componentOffset:FlxPoint = FlxPoint.get();
	public var push:FlxPoint = FlxPoint.get();
	public var _components:Array<HLUIComponent> = [];
	public var ownerPaths(default, null):CodenamePaths;
	public var _hovered:Bool = false;
	var parentComponent:Null<HLUIComponent>;
	public var flowOffset:FlxPoint = FlxPoint.get();
	public var claimed:FlxBasic->Void;
	var mountedStates:Map<FlxState, Bool> = new Map();
	var destroyed:Bool = false;
	var hasRealGraphic:Bool = false;

	public function new(?x:Float = 0, ?y:Float = 0) {
		super(x, y);
		antialiasing = true;
	}

	/** Supply owner-local asset and lifecycle hooks after HScript construction. */
	public function bindOwner(paths:CodenamePaths, claim:FlxBasic->Void):Void {
		ownerPaths = paths;
		claimed = claim;
		for (component in _components) if (component != null) component.bindOwner(paths, claim);
	}

	public function addComponent(component:HLUIComponent):HLUIComponent {
		if (component == null || component == this) return component;
		if (_components.indexOf(component) < 0) {
			_components.push(component);
			component.parentComponent = this;
			if (ownerPaths != null) component.bindOwner(ownerPaths, claimed);
			layoutComponents();
		}
		return component;
	}

	public function removeComponent(component:HLUIComponent, destroyChild:Bool = false):HLUIComponent {
		if (component == null) return null;
		_components.remove(component);
		component.parentComponent = null;
		if (destroyChild) component.destroy();
		layoutComponents();
		return component;
	}

	public function forEachComponent(callback:HLUIComponent->Void):Void {
		if (callback == null) return;
		for (component in _components.copy()) if (component != null) callback(component);
	}

	/** Basic horizontal/vertical flow is supplied by HLUIBox. */
	public function layoutComponents():Void {
		for (component in _components) if (component != null) component.syncPosition();
	}

	public function syncPosition():Void {
		if (parentComponent != null) {
			x = parentComponent.x + componentOffset.x + flowOffset.x;
			y = parentComponent.y + componentOffset.y + flowOffset.y;
		}
		setHitArea();
		layoutComponents();
	}

	public function setHitArea():Void {
		if (componentWidth > 0 && componentHeight > 0) setSize(componentWidth, componentHeight);
	}

	public function setTreeVisible(value:Bool):Void {
		visible = value;
		for (component in _components) if (component != null) component.setTreeVisible(value);
	}

	/** Match the common HLUI signature while retaining FlxSprite's bitmap API. */
	override public function makeGraphic(width:Int, height:Int, color:FlxColor = FlxColor.WHITE,
		unique:Bool = false, ?key:String):FlxSprite {
		componentWidth = width;
		componentHeight = height;
		var result = super.makeGraphic(width, height, color, unique, key);
		hasRealGraphic = graphic != null;
		return result;
	}

	override public function loadGraphic(graphic:flixel.system.FlxAssets.FlxGraphicAsset,
		animated:Bool = false, frameWidth:Int = 0, frameHeight:Int = 0,
		unique:Bool = false, ?key:String):FlxSprite {
		var result = super.loadGraphic(graphic, animated, frameWidth, frameHeight, unique, key);
		componentWidth = width;
		componentHeight = height;
		hasRealGraphic = this.graphic != null;
		return result;
	}

	/** Empty layout widgets must not acquire Flixel's debug fallback logo when drawn. */
	override public function draw():Void {
		if (!hasRealGraphic || graphic == null) return;
		super.draw();
	}

	/** Draw the simple theme fills requested by the donor scripts. */
	public function buildUI(?options:Dynamic):Void {
		var background = options != null && Reflect.field(options, 'background') == true;
		var alt = options != null && Reflect.field(options, 'altCol') == true;
		var dark = options != null && Reflect.field(options, 'darkCol') == true;
		if (!background && !alt && !dark) return;
		var fill:FlxColor = dark ? 0xFF252525 : (alt ? 0xFF555555 : 0xFF333333);
		var w = Std.int(Math.max(1, Math.ceil(componentWidth > 0 ? componentWidth : width)));
		var h = Std.int(Math.max(1, Math.ceil(componentHeight > 0 ? componentHeight : height)));
		makeGraphic(w, h, fill);
		updateHitbox();
	}

	public function drawBackground(?options:Dynamic):Void buildUI(options);

	public function addThisAndChildComponentsToState(state:FlxState):Void {
		if (state == null) return;
		if (mountedStates.exists(state)) return;
		mountedStates.set(state, true);
		syncPosition();
		state.add(this);
		if (claimed != null) claimed(this);
		mountExtraSprites(state);
		for (component in _components) if (component != null)
			component.addThisAndChildComponentsToState(state);
	}

	/** Subclasses such as HLUILabel can mount their internal render object here. */
	public function mountExtraSprites(state:FlxState):Void {}

	public function removeThisAndChildComponentsFromState(state:FlxState):Void {
		if (state == null || !mountedStates.exists(state)) return;
		mountedStates.remove(state);
		for (component in _components.copy()) if (component != null)
			component.removeThisAndChildComponentsFromState(state);
		state.remove(this, false);
		if (claimed != null) claimed(this);
	}

	public function center():Void {
		x = Std.int((FlxG.width - componentWidth) / 2);
		y = Std.int((FlxG.height - componentHeight) / 2);
		layoutComponents();
	}

	public function updateHover():Bool {
		_hovered = visible && FlxG.mouse.overlaps(this);
		return _hovered;
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		layoutComponents();
	}

	override public function destroy():Void {
		if (destroyed) return;
		destroyed = true;
		for (component in _components.copy()) if (component != null) component.destroy();
		_components.resize(0);
		componentOffset = FlxDestroyUtil.put(componentOffset);
		push = FlxDestroyUtil.put(push);
		flowOffset = FlxDestroyUtil.put(flowOffset);
		mountedStates = new Map();
		claimed = null;
		ownerPaths = null;
		super.destroy();
	}
}
