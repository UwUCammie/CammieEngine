package;

import haxe.io.Path;
using StringTools;

/** Psych's stage coordinates are character start points. Character.position
 * from the selected donor is added by Psych's startCharacterPos. Built-in
 * definitions live in Psych's own assets rather than most mod exports. */
class PsychCharacterPosition {
	static inline var BASE_POSITIONS = 'assets/data/psych_base_character_positions.json';
	static var basePositions:Dynamic;

	public static function point(value:Dynamic):Null<Array<Float>> {
		if (!Std.isOfType(value, Array) || (cast value:Array<Dynamic>).length < 2)
			return null;
		var values:Array<Dynamic> = cast value;
		var x = Std.parseFloat(Std.string(values[0]));
		var y = Std.parseFloat(Std.string(values[1]));
		return Math.isNaN(x) || Math.isNaN(y) || !Math.isFinite(x) || !Math.isFinite(y)
			? null : [x, y];
	}

	static function positionIn(path:String):Null<Array<Float>> {
		if (!FNFAssets.exists(path))
			return null;
		try {
			var data:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			return point(Reflect.field(data, 'position'));
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function cameraPositionIn(path:String):Null<Array<Float>> {
		if (!FNFAssets.exists(path))
			return null;
		try {
			var data:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			return point(Reflect.field(data, 'camera_position'));
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Preserve Psych's raw camera_position array on Character for Lua/HScript
	 * property access. Other engines and missing/malformed metadata stay neutral. */
	public static function characterCameraPosition(id:String, scopedRoot:String):Array<Float> {
		var name = id == null ? '' : id.trim();
		if (name == '' || !~/^[A-Za-z0-9_-]+$/.match(name) || scopedRoot == null || scopedRoot == '')
			return [0, 0];
		var cameraPosition:Null<Array<Float>> = null;
		for (folder in ['characters', 'shared/characters']) {
			cameraPosition = cameraPositionIn(Path.join([scopedRoot, folder, name + '.json']));
			if (cameraPosition != null)
				break;
		}
		if (cameraPosition == null)
			return [0, 0];
		return cameraPosition;
	}

	/** Return a live raw camera_position in the role's Psych camera convention.
	 * Psych subtracts only BF X; opponent and GF add both coordinates. */
	public static function roleCameraOffset(cameraPosition:Dynamic, role:String):Array<Float> {
		var position = point(cameraPosition);
		if (position == null)
			return [0, 0];
		var normalizedRole = role == null ? '' : role.trim().toLowerCase();
		var cameraX = normalizedRole == 'boyfriend' || normalizedRole == 'bf'
			|| normalizedRole == 'player1'
			? -position[0] : position[0];
		return [cameraX, position[1]];
	}

	static function psychRoleCameraBase(role:String):Array<Float> {
		var normalizedRole = role == null ? '' : role.trim().toLowerCase();
		return switch (normalizedRole) {
			case 'boyfriend' | 'bf' | 'player1': [-100, -100];
			case 'gf' | 'girlfriend' | 'player3': [0, 0];
			default: [150, -100];
		};
	}

	/** Compose the Psych role baseline with live character/stage camera metadata
	 * and only the changes made after native Character.init. Psych's focus is
	 * BF [-100,-100], dad [150,-100], GF [0,0]; native legacy defaults are
	 * intentionally excluded. */
	public static function effectiveCameraOffset(role:String, cameraPosition:Dynamic,
		stageCameraPosition:Dynamic, followDeltaX:Float = 0, followDeltaY:Float = 0):Array<Float> {
		var base = psychRoleCameraBase(role);
		var character = roleCameraOffset(cameraPosition, role);
		var stage = point(stageCameraPosition);
		if (stage == null)
			stage = [0, 0];
		var dx = Math.isNaN(followDeltaX) || !Math.isFinite(followDeltaX) ? 0 : followDeltaX;
		var dy = Math.isNaN(followDeltaY) || !Math.isFinite(followDeltaY) ? 0 : followDeltaY;
		return [base[0] + character[0] + stage[0] + dx,
			base[1] + character[1] + stage[1] + dy];
	}

	/** The donor's own character JSON wins, including an explicit [0, 0].
	 * Native authored offsets win over the packaged base default when a mod
	 * replaces a built-in character without supplying Psych JSON. */
	public static function resolve(id:String, scopedRoot:String, nativeX:Float = 0,
		nativeY:Float = 0):Array<Float> {
		var name = id == null ? '' : id.trim();
		if (name != '' && ~/^[A-Za-z0-9_-]+$/.match(name) && scopedRoot != null && scopedRoot != '') {
			for (folder in ['characters', 'shared/characters']) {
				var scoped = positionIn(Path.join([scopedRoot, folder, name + '.json']));
				if (scoped != null)
					return scoped;
			}
		}
		if (nativeX != 0 || nativeY != 0)
			return [nativeX, nativeY];
		if (basePositions == null) {
			try basePositions = CoolUtil.parseJson(FNFAssets.getText(BASE_POSITIONS))
			catch (_:Dynamic) basePositions = {};
		}
		var builtin = point(Reflect.field(basePositions, name));
		return builtin == null ? [0, 0] : builtin;
	}
}
