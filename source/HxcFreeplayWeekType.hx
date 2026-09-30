package;

import flixel.FlxSprite;

using StringTools;

/** Native visual slot exposed to the bounded HXC Freeplay display adapter. */
class HxcFreeplayWeekType extends FlxSprite {
	var importedDisplayKey:String = '';

	public function new() {
		super();
		scrollFactor.set();
		visible = false;
	}

	/** Load a manifest-owned capsule atlas once and apply its literal animations. */
	public function applyImportedDisplay(root:String, plan:Dynamic, selectedAnimation:String):Bool {
		if (plan == null || selectedAnimation == null || StringTools.trim(selectedAnimation) == '') {
			visible = false;
			return false;
		}
		var atlas = Std.string(Reflect.field(plan, 'atlas'));
		if (atlas == '' || atlas.indexOf('..') >= 0 || atlas.startsWith('/')) {
			visible = false;
			return false;
		}
		var key = (root == null ? '' : root) + ':' + atlas;
		if (importedDisplayKey != key) {
			var frames = HxcStateAssetScope.sparrowAtlas(root, atlas, null,
				'Imported Freeplay capsule display');
			if (frames == null) {
				visible = false;
				return false;
			}
			animation.destroyAnimations();
			this.frames = frames;
			var definitions:Array<Dynamic> = cast Reflect.field(plan, 'animations');
			if (definitions == null) {
				visible = false;
				return false;
			}
			for (definition in definitions) {
				if (definition == null)
					continue;
				var name = Std.string(Reflect.field(definition, 'name'));
				var prefix = Std.string(Reflect.field(definition, 'prefix'));
				var fps:Float = cast Reflect.field(definition, 'fps');
				var looped = Reflect.field(definition, 'looped') == true;
				if (name == '' || prefix == '' || fps <= 0) {
					animation.destroyAnimations();
					this.frames = null;
					visible = false;
					return false;
				}
				animation.addByPrefix(name, prefix, fps, looped);
			}
			importedDisplayKey = key;
		}
		if (animation.getByName(selectedAnimation) == null) {
			visible = false;
			return false;
		}
		animation.play(selectedAnimation, true);
		visible = true;
		return true;
	}
}
