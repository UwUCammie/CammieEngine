package;

import flixel.FlxBasic;
import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.FlxSubState;
import flixel.addons.transition.FlxTransitionableState;
import flixel.addons.effects.FlxTrail;
import flixel.addons.text.FlxTypeText;
import flixel.addons.display.FlxTiledSprite;
import flixel.addons.display.FlxPieDial;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.math.FlxMath;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.sound.FlxSound;
import flixel.text.FlxText;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
import flixel.util.FlxSort;
import flixel.util.FlxDestroyUtil;
import openfl.display.BitmapData;
import openfl.display.ShaderParameter;
import PsychFlxCameraCompat.PsychFlxGCompat;
import PsychFlxShaderCompat.PsychShaderParameterTypeCompat;

/** Explicit target classes shared by owner-scoped Psych stage modules.
	The binding table mirrors only stable source/import.hx names that this engine
	can host. Owner modules such as objects.BGSprite are still loaded from the
	selected root; unsupported imported classes remain visible loader errors.
*/
class PsychCompiledStageBindings {
	public static function create(ownerRoot:String, ?initialLibrary:String):Map<String, Dynamic> {
		var bindings:Map<String, Dynamic> = new Map();
		// FlxColor and BlendMode are Haxe abstracts, so their type names do not
		// exist as runtime values. Bind the same narrow facades used by the
		// Codename HScript bridge instead.
		var blendModes = CodenameImportBindings.blendModeConstants();
		bind(bindings, 'FlxBasic', FlxBasic);
		bind(bindings, 'flixel.FlxBasic', FlxBasic);
		bind(bindings, 'FlxCamera', FlxCamera);
		bind(bindings, 'flixel.FlxCamera', FlxCamera);
		bind(bindings, 'FlxG', PsychFlxGCompat);
		bind(bindings, 'flixel.FlxG', PsychFlxGCompat);
		bind(bindings, 'Controls', PsychControlsCompat);
		bind(bindings, 'backend.Controls', PsychControlsCompat);
		bind(bindings, 'FlxTransitionableState', FlxTransitionableState);
		bind(bindings, 'flixel.addons.transition.FlxTransitionableState', FlxTransitionableState);
		bind(bindings, 'FlxObject', FlxObject);
		bind(bindings, 'flixel.FlxObject', FlxObject);
		bind(bindings, 'FlxSprite', FlxSprite);
		bind(bindings, 'flixel.FlxSprite', FlxSprite);
		bind(bindings, 'FlxTrail', FlxTrail);
		bind(bindings, 'flixel.addons.effects.FlxTrail', FlxTrail);
		bind(bindings, 'FlxSubState', FlxSubState);
		bind(bindings, 'flixel.FlxSubState', FlxSubState);
		bind(bindings, 'FlxTiledSprite', FlxTiledSprite);
		bind(bindings, 'flixel.addons.display.FlxTiledSprite', FlxTiledSprite);
		bind(bindings, 'FlxPieDial', FlxPieDial);
		bind(bindings, 'flixel.addons.display.FlxPieDial', FlxPieDial);
		bind(bindings, 'FlxGraphic', FlxGraphic);
		bind(bindings, 'flixel.graphics.FlxGraphic', FlxGraphic);
		bind(bindings, 'FlxAtlasFrames', FlxAtlasFrames);
		bind(bindings, 'flixel.graphics.frames.FlxAtlasFrames', FlxAtlasFrames);
		bind(bindings, 'FlxAnimate', PsychFlxAnimateCompat);
		bind(bindings, 'animate.FlxAnimate', PsychFlxAnimateCompat);
		bind(bindings, 'flxanimate.PsychFlxAnimate', PsychFlxAnimateCompat);
		bind(bindings, 'FlxTypedGroup', FlxTypedGroup);
		bind(bindings, 'flixel.group.FlxGroup', FlxTypedGroup);
		bind(bindings, 'flixel.group.FlxGroup.FlxTypedGroup', FlxTypedGroup);
		bind(bindings, 'FlxPoint', PsychFlxPointCompat);
		bind(bindings, 'flixel.math.FlxPoint', PsychFlxPointCompat);
		bind(bindings, 'FlxMath', FlxMath);
		bind(bindings, 'flixel.math.FlxMath', FlxMath);
		bind(bindings, 'FlxSpriteGroup', FlxTypedSpriteGroup);
		bind(bindings, 'flixel.group.FlxSpriteGroup', FlxTypedSpriteGroup);
		bind(bindings, 'FlxSound', FlxSound);
		bind(bindings, 'flixel.sound.FlxSound', FlxSound);
		bind(bindings, 'FlxText', FlxText);
		bind(bindings, 'flixel.text.FlxText', FlxText);
		bind(bindings, 'FlxTypeText', FlxTypeText);
		bind(bindings, 'flixel.addons.text.FlxTypeText', FlxTypeText);
		bind(bindings, 'FlxEase', FlxEase);
		bind(bindings, 'flixel.tweens.FlxEase', FlxEase);
		bind(bindings, 'FlxTween', FlxTween);
		bind(bindings, 'flixel.tweens.FlxTween', FlxTween);
		bind(bindings, 'FlxColor', HxcFlxColorCompat);
		bind(bindings, 'flixel.util.FlxColor', HxcFlxColorCompat);
		bind(bindings, 'FlxTimer', FlxTimer);
		bind(bindings, 'flixel.util.FlxTimer', FlxTimer);
		bind(bindings, 'FlxSort', FlxSort);
		bind(bindings, 'flixel.util.FlxSort', FlxSort);
		bind(bindings, 'FlxDestroyUtil', FlxDestroyUtil);
		bind(bindings, 'flixel.util.FlxDestroyUtil', FlxDestroyUtil);
		// hscript-ex cannot consume ShaderMacro metadata from owner source files.
		// Bind a FlxShader subclass that receives the expanded GLSL and creates
		// OpenFL's normal per-uniform ShaderParameter wrappers at runtime.
		bind(bindings, 'FlxShader', PsychFlxShaderCompat);
		bind(bindings, 'flixel.system.FlxAssets.FlxShader', PsychFlxShaderCompat);
		bind(bindings, 'flixel.graphics.tile.FlxGraphicsShader', PsychFlxShaderCompat);
		bind(bindings, 'BitmapData', BitmapData);
		bind(bindings, 'openfl.display.BitmapData', BitmapData);
		bind(bindings, 'ShaderParameter', ShaderParameter);
		bind(bindings, 'openfl.display.ShaderParameter', ShaderParameter);
		bind(bindings, 'ShaderParameterType', PsychShaderParameterTypeCompat);
		bind(bindings, 'openfl.display.ShaderParameterType', PsychShaderParameterTypeCompat);
		var openFlAssets = PsychOwnerOpenFlAssets.create(ownerRoot);
		bind(bindings, 'Assets', openFlAssets);
		bind(bindings, 'openfl.utils.Assets', openFlAssets);
		// Psych source classes use Lime's static asset API. Capture the selected
		// import root so relative media resolves owner-first without exposing a
		// sibling import's namespace.
		bind(bindings, 'lime.utils.Assets', PsychOwnerLimeAssets.create(ownerRoot));
		bindings.set('CodenameKeyValueIterator', CodenameKeyValueIterator.facade());
		// Native OpenFL requires a Shader, while an interpreted subclass is an
		// owner-scoped ScriptClass proxy. The adapter unwraps only at construction.
		bind(bindings, 'ShaderFilter', PsychShaderFilterCompat);
		bind(bindings, 'openfl.filters.ShaderFilter', PsychShaderFilterCompat);
		bind(bindings, 'BlendMode', blendModes);
		bind(bindings, 'openfl.display.BlendMode', blendModes);
		// Psych source stages commonly reference these abstract enum values as
		// unqualified imports (for example `blend = MULTIPLY`). HScript cannot
		// reflect the enum abstract itself, so expose the full facade alongside
		// its qualified BlendMode name.
		for (constant in Reflect.fields(blendModes))
			bindings.set(constant, Reflect.field(blendModes, constant));
		bindings.set('BOOL', Reflect.field(PsychShaderParameterTypeCompat, 'BOOL'));
		bindings.set('BOOL2', Reflect.field(PsychShaderParameterTypeCompat, 'BOOL2'));
		bindings.set('BOOL3', Reflect.field(PsychShaderParameterTypeCompat, 'BOOL3'));
		bindings.set('BOOL4', Reflect.field(PsychShaderParameterTypeCompat, 'BOOL4'));
		bindings.set('FLOAT', Reflect.field(PsychShaderParameterTypeCompat, 'FLOAT'));
		bindings.set('FLOAT2', Reflect.field(PsychShaderParameterTypeCompat, 'FLOAT2'));
		bindings.set('FLOAT3', Reflect.field(PsychShaderParameterTypeCompat, 'FLOAT3'));
		bindings.set('FLOAT4', Reflect.field(PsychShaderParameterTypeCompat, 'FLOAT4'));
		bindings.set('INT', Reflect.field(PsychShaderParameterTypeCompat, 'INT'));
		bindings.set('INT2', Reflect.field(PsychShaderParameterTypeCompat, 'INT2'));
		bindings.set('INT3', Reflect.field(PsychShaderParameterTypeCompat, 'INT3'));
		bindings.set('INT4', Reflect.field(PsychShaderParameterTypeCompat, 'INT4'));
		bind(bindings, 'Math', Math);
		bind(bindings, 'Std', Std);
		bind(bindings, 'Reflect', Reflect);
		bind(bindings, 'StringTools', StringTools);
		var ownerPaths = PsychOwnerPaths.create(ownerRoot, initialLibrary);
		bind(bindings, 'Paths', ownerPaths);
		bind(bindings, 'backend.Paths', ownerPaths);
		bind(bindings, 'PlayState', PlayState);
		bind(bindings, 'states.PlayState', PlayState);
		var gameOverClass = new PsychGameOverClassCompat(PlayState.instance, PlayState.SONG);
		bind(bindings, 'GameOverSubstate', gameOverClass);
		bind(bindings, 'substates.GameOverSubstate', gameOverClass);
		bind(bindings, 'Character', Character);
		bind(bindings, 'objects.Character', Character);
		bind(bindings, 'Note', Note);
		bind(bindings, 'objects.Note', Note);
		bind(bindings, 'backend.ClientPrefs', PsychClientPrefsCompat);
		bind(bindings, 'ClientPrefs', PsychClientPrefsCompat);
		bind(bindings, 'backend.BaseStage', PsychBaseStageCompat);
		bind(bindings, 'BaseStage', PsychBaseStageCompat);
		bind(bindings, 'backend.BaseStage.Countdown', PsychBaseStageCountdown);
		bind(bindings, 'Countdown', PsychBaseStageCountdown);
		bind(bindings, 'Conductor', Conductor);
		bind(bindings, 'backend.Conductor', Conductor);
		bind(bindings, 'CoolUtil', CoolUtil);
		bind(bindings, 'backend.CoolUtil', CoolUtil);
		bind(bindings, 'haxe.Json', haxe.Json);
		return bindings;
	}

	static function bind(bindings:Map<String, Dynamic>, name:String, value:Dynamic):Void {
		bindings.set(name, value);
	}
}
