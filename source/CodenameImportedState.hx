package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.util.FlxColor;

/** MusicBeatState materialization for one selected-owner Codename state script. */
class CodenameImportedState extends MusicBeatState {
	public final ownerRoot:String;
	public final scriptPath:String;
	var runtime:CodenameModStateRuntime;
	var exitHint:FlxText;
	var diagnosticPanel:FlxSprite;
	var diagnosticText:FlxText;

	public function new(ownerRoot:String, scriptPath:String) {
		super();
		this.ownerRoot = ownerRoot;
		this.scriptPath = scriptPath;
	}

	override function create():Void {
		CodenameStateSmokeTrace.mark('imported-create-enter', ownerRoot, scriptPath);
		super.create();
		runtime = new CodenameModStateRuntime(this, ownerRoot, scriptPath);
		runtime.create();
		CodenameStateSmokeTrace.mark('imported-create-ready', ownerRoot, scriptPath);
		exitHint = new FlxText(8, FlxG.height - 24, 360, 'F10: exit imported mod', 13);
		exitHint.setFormat(null, 13, 0xFFA0A0A0, LEFT, FlxTextBorderStyle.NONE);
		exitHint.scrollFactor.set();
		exitHint.cameras = [FlxG.camera];
		add(exitHint);
	}

	override public function update(elapsed:Float):Void {
		if (FlxG.keys.justPressed.F10) {
			CodenameModRuntime.exitToNativeMenu();
			return;
		}
		CodenameModRuntime.updateGlobal(elapsed);
		if (runtime != null) runtime.update(elapsed);
		super.update(elapsed);
		// A ModSwitchMenu can replace the active owner while this state's
		// substate updates. Do not run another callback from the outgoing owner.
		if (runtime != null && CodenameModRuntime.isActiveOwner(ownerRoot)) runtime.postUpdate(elapsed);
		// RuntimeSmokeState and PlayState drive the smoke clock while gameplay
		// runs. Once an imported ModState takes over, it must keep the same
		// bounded completion/deadline checks alive without adding a second tick
		// to those already-instrumented states.
		if (RuntimeSmokeHarness.enabled())
			RuntimeSmokeHarness.tick(elapsed);
	}

	override public function stepHit():Void {
		if (runtime != null) runtime.step(curStep);
		super.stepHit();
	}

	override public function beatHit():Void {
		if (runtime != null) runtime.beat(curBeat);
		super.beatHit();
	}

	public function showRuntimeDiagnostic(message:String):Void {
		trace('[codename-state-error] ' + scriptPath + ': ' + message);
		if (diagnosticPanel != null) return;
		diagnosticPanel = new FlxSprite(0, 0).makeGraphic(FlxG.width, FlxG.height, 0xE8000000);
		diagnosticPanel.scrollFactor.set();
		add(diagnosticPanel);
		diagnosticText = new FlxText(40, 36, FlxG.width - 80,
			'Imported state could not run\n' + scriptPath + '\n' + message, 20);
		diagnosticText.setFormat(null, 20, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		diagnosticText.wordWrap = true;
		diagnosticText.fieldHeight = FlxG.height - 72;
		diagnosticText.scrollFactor.set();
		add(diagnosticText);
	}

	override public function destroy():Void {
		if (runtime != null) {
			runtime.destroy();
			runtime = null;
		}
		super.destroy();
	}
}
