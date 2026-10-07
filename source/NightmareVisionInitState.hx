package;

import flixel.FlxState;

/** The source Init state delegates backend startup in its original order. */
@:keep
class NightmareVisionInitState extends FlxState {
	final session:NightmareVisionStateSession;
	public function new(session:NightmareVisionStateSession) {
		super(); this.session = session;
	}
	public override function create():Void {
		new NightmareVisionBootstrap<FlxState>(new NightmareVisionInitHost(session, createNativeBase)).run();
	}
	function createNativeBase():Void super.create();
	public override function destroy():Void {
		super.destroy();
		session.releaseStateResources(this);
	}
}
