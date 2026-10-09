package;

import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;

/** Historical gameObjects.Stage. Foreground is a separate scene-owned group.
 * This explicit source class does not change the modern Stage preset.
 */
@:keep
class NightmareVisionLegacyStage extends FlxTypedGroup<FlxBasic> {
	public var stageScripts:Array<NightmareVisionScriptModule> = [];
	public var hscriptArray:Array<NightmareVisionScriptModule> = [];
	public var curStage:String = "stage1";
	public var stageData:Dynamic;
	public var spriteMap:Map<String, FlxBasic> = [];
	public var foreground:FlxTypedGroup<FlxBasic> = new FlxTypedGroup<FlxBasic>();
	var owner:NightmareVisionStageOwner;

	public function new(?stageName:String = "stage", ?owner:NightmareVisionStageOwner) {
		super();
		this.owner = owner;
		if (stageName != null) curStage = stageName;
		stageData = requiredOwner().stageFile(curStage);
		if (stageData == null) stageData = requiredOwner().template();
	}

	public function buildStage():Void {
		var selected = requiredOwner();
		var file = selected.scriptPath('stages/' + curStage);
		if (file == null || !selected.scriptExists(file)) return;
		if (StringTools.endsWith(file, '.lua')) {
			selected.warn('Legacy Stage Lua construction is not yet supported: ' + file);
			return;
		}
		var script = selected.fromFile(file, null);
		hscriptArray.push(script);
		stageScripts.push(script);
		script.set('add', add);
		script.set('stage', this);
		script.set('foreground', foreground);
		script.call('onLoad', [this, foreground]);
	}

	function requiredOwner():NightmareVisionStageOwner {
		if (owner == null) throw '[nightmare-vision-stage] Missing captured owner';
		owner.requireActive();
		return owner;
	}

	override public function destroy():Void {
		// Source stop releases the interpreter without calling onDestroy.
		// Foreground is mounted and destroyed separately by its scene owner.
		for (script in stageScripts) script.destroy();
		super.destroy();
		owner = null;
	}
}
