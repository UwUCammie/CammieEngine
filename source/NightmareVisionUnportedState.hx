package;

import flixel.FlxG;
import flixel.text.FlxText;

/** A named native destination can be redirected before create. Missing native
 * contracts remain explicit rather than silently becoming a different menu. */
@:keep
class NightmareVisionUnportedState extends NightmareVisionMusicBeatState {
	public final requestedName:String;
	final session:NightmareVisionStateSession;
	public function new(name:String, session:NightmareVisionStateSession) {
		super(session.stateHost()); this.session = session; requestedName = name;
	}
	public override function create():Void {
		super.create();
		var message = '[nightmare-vision-state-unsupported] Native source state ' + requestedName + ' is not ported yet.';
		trace(message);
		var text = new FlxText(40, 80, FlxG.width - 80, message + '\n\nBack: return to source main menu', 24);
		text.setFormat(session.paths.DEFAULT_FONT, 24, 0xFFFFFFFF);
		add(text);
	}
	public override function update(elapsed:Float):Void {
		if (controls.BACK) session.switchState(session.createStateFactory('MainMenuState'));
		super.update(elapsed);
	}
}
