package;

import flixel.FlxSprite;
import flixel.util.FlxColor;
import openfl.display.BlendMode;
import NightmareVisionStageOwner.NightmareVisionStageBopper;
import NightmareVisionStageDataSchema.NightmareVisionStageFile;
import NightmareVisionStageDataSchema.NightmareVisionStageAnimationInfo;


import flixel.group.FlxContainer.FlxTypedContainer;
import flixel.FlxBasic;




/**
 * Primary class holding all `FlxBasic`'s for the background of stage within `PlayState`
 *
 * Besides whatever else is added, it contains the characters as well.
 */
@:keep
@:nullSafety(Strict)
class NightmareVisionStage extends FlxTypedContainer<FlxBasic>
{
	/**
	 * Attached script to the stage
	 */
	public var script:Null<NightmareVisionScriptModule> = null;

	/**
	 * The name of the current stage
	 */
	public var curStage = "stage";

	/**
	 * The json info from the current stage
	 */
	public final stageData:NightmareVisionStageFile;

	/**
	 * Registered objects of the stage.
	 *
	 * Usually populated during the `buildStage` function
	 */
	public final objects:Map<String, FlxSprite> = [];

	public var boppers:Array<NightmareVisionBopper> = [];

	/**
	 * The default camera zoom defined in the stage json.
	 *
	 * Accessor to `stageData.defaultZoom`
	 */
	public var defaultZoom(get, never):Float;

	function get_defaultZoom():Float
	{
		return stageData.defaultZoom;
	}

	public function new(curStage:String = "stage", ?owner:NightmareVisionStageOwner)
	{
		super();
		this.owner = owner;

		this.curStage = curStage;

		stageData = requiredOwner().stageFile(curStage) ?? requiredOwner().template();
	}

	/**
	 *
	 * instantiates any stage objects and attempts to load a script for the stage
	 */
	public function buildStage()
	{
		if (stageData.stageObjects != null)
		{
			for (info in stageData.stageObjects)
			{
				final obj:FlxSprite = resolveStageObject(info.customInstance ?? '');

				if (info.asset == null)
				{
					NightmareVisionSpriteMethods.makeScaledGraphic(obj, 1, 1);
				}
				else
				{
					if (bopperFor(obj) != null)
					{
						@:nullSafety(Off)
						{
							requireBopper(obj).loadAtlas(info.asset);

							if (obj.frames == null) obj.loadGraphic(requiredOwner().paths.image(info.asset));
						}
					}
					else
					{
						@:nullSafety(Off)
						{
							final frames = requiredOwner().paths.getMultiAtlas(info.asset.split(','));
							if (frames != null)
							{
								obj.frames = frames;
							}
							else
							{
								obj.loadGraphic(requiredOwner().paths.image(info.asset));
							}
						}
					}

					loadAnimationToSprite(obj, info.animations);
				}

				if (info.alpha != null) obj.alpha = info.alpha;
				if (info.angle != null) obj.angle = info.angle;
				if (info.flipX != null) obj.flipX = info.flipX;
				if (info.flipY != null) obj.flipY = info.flipY;
				if (info.zIndex != null) @:nullSafety(Off) requiredOwner().setZIndex(obj, info.zIndex);
				if (info.antialiasing != null) obj.antialiasing = info.antialiasing == false ? false : requiredOwner().antialiasing();
				if (info.blend != null) obj.blend = blendFromString(info.blend);

				if (info.colour != null)
				{
					final colour = FlxColor.fromString(info.colour);
					if (colour != null) obj.color = colour;
				}

				if (info.scale != null)
				{
					final scale = correctArray(info.scale, [1, 1]);
					obj.scale.set(scale[0], scale[1]);
				}

				if (info.scrollFactor != null)
				{
					final scrollFactor = correctArray(info.scrollFactor, [1, 1]);
					obj.scrollFactor.set(scrollFactor[0], scrollFactor[1]);
				}

				if (info.position != null)
				{
					final position = correctArray(info.position, [0, 0]);
					obj.setPosition(position[0], position[1]);
				}

				if (info.id != null)
				{
					final objId = info.id ?? ''; // we null checked already but to shut up null safety
					final objToLower = objId.toLowerCase();
					if (objects.exists(objId) || objToLower == 'gf' || objToLower == 'dad' || objToLower == 'boyfriend')
					{
						requiredOwner().warn('Object cannot use id($objId) as it is in use.');
					}
					else
					{
						objects.set(objId, obj);
					}
				}

				obj.updateHitbox();

				if (info.advancedCalls != null)
				{
					for (i in info.advancedCalls)
					{
						final method = Reflect.field(obj, i.method);
						if (method != null && Reflect.isFunction(method))
						{
							Reflect.callMethod(obj, method, i.args ?? []); // todo more powerful utils
						}
					}
				}

				if (info.setProperties != null)
				{
					for (i in info.setProperties)
					{
						try
						{
							requiredOwner().setProperty(obj, i.property, i.value);
						}
						catch (e)
						{
							final objectName = info.id ?? 'object';
							requiredOwner().warn('[$objectName]: could not set ${i.property}');
						}
					}
				}

				add(obj);
			}
		}
	}

	public function runScript(?group:NightmareVisionScriptGroup):Bool
	{
		final baseScriptFile:String = 'data/stages/$curStage/script';

		inline function startScript(scriptFile:String)
		{
			script = requiredOwner().fromFile(scriptFile, group == null ? null : group.sharedFields);
			if (script.parsingFailed())
			{
				script.destroy();
				script = null;
				return;
			}

			@:nullSafety(Off) // trust me bro
			{
				script.set("add", add);
				script.set("stage", this);

				for (id => obj in objects)
					script.set(id, obj);
				if (script.exists('onLoad')) script.call("onLoad");
			}
		}

		inline function tryScript(path:String):Null<String>
		{
			final scriptFile = requiredOwner().scriptPath(path);
			return (requiredOwner().scriptExists(scriptFile) ? scriptFile : null);
		}

		// rlly rlly funny line here but yk what its ok
		final scriptFile = tryScript(baseScriptFile) ?? tryScript('data/stages/$curStage') ?? tryScript('stages/$curStage/script') ?? tryScript('stages/$curStage') ?? tryScript('data/stages/stage');

		if (scriptFile != null)
		{
			@:nullSafety(Off)
			startScript(scriptFile);
		}
		else
		{
			#if VERBOSE_LOGS
			requiredOwner().warn('$curStage is not scripted.');
			#end
		}

		return script != null;
	}

	public function onBeatHit()
	{
		//
	}

	inline function loadAnimationToSprite(spr:FlxSprite, anims:Null<Array<NightmareVisionStageAnimationInfo>>)
	{
		if (anims != null && anims.length != 0) // have to nest here instead of early return cuz null safety is a little dumb..
		{
			var firstAnim:Null<String> = null;

			for (anim in anims)
			{
				final animAnim:String = '' + anim.anim;
				final animName:String = '' + anim.name;
				final animFps:Int = anim.fps;
				final animLoop:Bool = !!anim.loop; // Bruh
				final animIndices:Array<Int> = anim.indices ?? [];

				final flipX = anim.flipX ?? false;
				final flipY = anim.flipY ?? false;

				if (firstAnim == null) firstAnim = animAnim;

				if (animIndices.length > 0)
				{
					if (bopperFor(spr) != null)
					{
						requireBopper(spr).addAnimByIndices(animAnim, animName, animIndices, animFps, animLoop, flipX, flipY);
					}
					else
					{
						spr.animation.addByIndices(animAnim, animName, animIndices, '', animFps, animLoop, flipX, flipY);
					}
				}
				else
				{
					if (bopperFor(spr) != null)
					{
						requireBopper(spr).addAnimByPrefix(animAnim, animName, animFps, animLoop, flipX, flipY);
					}
					else
					{
						spr.animation.addByPrefix(animAnim, animName, animFps, animLoop, flipX, flipY);
					}
				}

				if (bopperFor(spr) != null && anim.offsets != null && anim.offsets.length > 1)
				{
					requireBopper(spr).addOffset(anim.anim, anim.offsets[0], anim.offsets[1]);
				}
			}

			if (bopperFor(spr) != null)
			{
				requireBopper(spr).playAnim(firstAnim);
			}
		}
	}

	function resolveStageObject(objInstance:String):FlxSprite
	{
		if (objInstance.length > 0)
		{
			var cl:Null<Class<Dynamic>> = resolveBuiltinObject(objInstance) ?? requiredOwner().resolveClass(objInstance);

			if (cl != null)
			{
				var instance:Dynamic = requiredOwner().createInstance(cl, []);
				if (!(instance is FlxSprite))
				{
					// if its a flixel or fl object it probably has one of these
					// probably.
					if (Reflect.hasField(instance, 'dispose')) instance.dispose();
					else if (Reflect.hasField(instance, 'destroy')) instance.destroy();

					instance = null;
					throw 'NightmareVisionStage [$curStage] attempted to create a custom instance of $objInstance which is not a FlxSprite.';
				}

				return instance;
			}
		}

		return new NightmareVisionBopper(0, 0, 2, requiredOwner().paths);
	}

 var owner:Null<NightmareVisionStageOwner>;
 function requiredOwner():NightmareVisionStageOwner {
  var selected = owner;
  if (selected == null) throw '[nightmare-vision-stage] Missing captured owner';
  selected.requireActive();
  return selected;
 }
 function bopperFor(sprite:FlxSprite):Null<NightmareVisionStageBopper> {
  if (Std.isOfType(sprite, NightmareVisionBopper)) {
   var b:NightmareVisionBopper = cast sprite;
   return {
    loadAtlas:function(path) {b.loadAtlas(path);},
    addAnimByPrefix:b.addAnimByPrefix, addAnimByIndices:b.addAnimByIndices,
    addOffset:b.addOffset, playAnim:function(name) {@:nullSafety(Off) b.playAnim(name);}
   };
  }
  return requiredOwner().bopper(sprite);
 }
 function requireBopper(sprite:FlxSprite):NightmareVisionStageBopper {
  var operations = bopperFor(sprite);
  if (operations == null) throw '[nightmare-vision-stage] Missing source Bopper operations';
  return operations;
 }
 function resolveBuiltinObject(name:String):Null<Class<Dynamic>> {
  name = name.toLowerCase();
  if (name.indexOf('tiledsprite') >= 0) return flixel.addons.display.FlxTiledSprite;
  else if (name.indexOf('backdrop') >= 0) return flixel.addons.display.FlxBackdrop;
  else if (name.indexOf('character') >= 0) return Character;
  else if (name.indexOf('flxbgsprite') >= 0) return flixel.system.FlxBGSprite;
  return null;
 }
 static function correctArray<T>(input:Array<T>, fallback:Array<T>):Array<T> {
  for (i in 0...input.length) fallback[i] = input[i];
  return fallback;
 }
 static function blendFromString(?blend:String):BlendMode {
  if (blend == null) return BlendMode.NORMAL;
  @:privateAccess return BlendMode.fromString(StringTools.trim(blend.toLowerCase())) ?? BlendMode.NORMAL;
 }
 override public function destroy():Void {
  try {super.destroy();} catch (error:Dynamic) {owner = null;throw error;}
  owner = null;
 }
}
