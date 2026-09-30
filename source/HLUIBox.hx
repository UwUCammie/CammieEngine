package;

import flixel.FlxSprite;
import flixel.math.FlxPoint;

@:keep
class HLUIBox extends HLUIComponent {
	public var layout:Dynamic;

	public function new(?layout:Dynamic = null) {
		super();
		this.layout = layout == null ? CodenameHL17UICompat.VERTICAL : layout;
	}

	override public function layoutComponents():Void {
		var cursor:Float = 0;
		var vertical = layout == CodenameHL17UICompat.VERTICAL
			|| Std.string(layout).toLowerCase() == 'vertical';
		for (component in _components) if (component != null) {
			component.flowOffset.set(vertical ? 0 : cursor, vertical ? cursor : 0);
			component.syncPosition();
			cursor += (vertical ? component.componentHeight : component.componentWidth)
				+ (vertical ? component.push.y : component.push.x);
		}
	}
}
