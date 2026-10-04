package;

import flixel.FlxG;
import flixel.group.FlxGroup;

/** Persistent native driver for one selected NMV package's ModPlugin group. */
@:keep
class NightmareVisionPluginHost extends FlxGroup {
	public static var activeHost(default, null):NightmareVisionPluginHost;
	public final runtime:NightmareVisionPluginRuntime;
	/** Owner assets survive song changes together with persistent plugins. */
	public var assetPaths(default, null):NightmareVisionPaths;
	public var scripts(get, never):NightmareVisionScriptGroup;
	function get_scripts():NightmareVisionScriptGroup return runtime.scripts;
	var released:Bool = false;

	public static function callActive(callback:String, ?args:Array<Dynamic>):Void {
		if (activeHost != null) activeHost.runtime.callOnPlugins(callback, args);
	}

	public static function releaseOtherOwner(root:String):Void {
		if (activeHost == null || activeHost.runtime.canReuseFor(root)) return;
		var previous = activeHost;
		activeHost = null;
		FlxG.plugins.remove(previous);
		previous.destroy();
	}

	public static function mount(root:String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptDiscovery.NightmareVisionScriptEntry->NightmareVisionPluginRuntime->Void,
		?assetPaths:NightmareVisionPaths):NightmareVisionPluginRuntime {
		releaseOtherOwner(root);
		if (activeHost == null) {
			activeHost = new NightmareVisionPluginHost(root, configure, assetPaths);
			FlxG.plugins.addPlugin(activeHost);
			activeHost.runtime.populate();
		}
		return activeHost.runtime;
	}

	function new(root:String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptDiscovery.NightmareVisionScriptEntry->NightmareVisionPluginRuntime->Void,
		?assetPaths:NightmareVisionPaths) {
		super();
		this.assetPaths = assetPaths;
		runtime = new NightmareVisionPluginRuntime(root, this,
			function() return NightmareVisionScriptDiscovery.discoverPlugins(root),
			sys.io.File.getContent, function(interp, entry) configure(interp, entry, runtime),
			function(name, phase, error) trace('[nightmare-vision-script-error] ' + root + '/plugins/' + name + '#' + phase + ': ' + Std.string(error)),
			function() {
				for (member in members) if (member != null) {
					try member.destroy() catch (error:Dynamic)
						trace('[nightmare-vision-plugin-release-error] ' + root + ': ' + Std.string(error));
				}
				clear();
			});
		FlxG.signals.preStateSwitch.add(onStateSwitch);
		FlxG.signals.postStateSwitch.add(onStateSwitchPost);
	}

	function onStateSwitch():Void runtime.callOnPlugins('onStateSwitch', [FlxG.state]);
	function onStateSwitchPost():Void runtime.callOnPlugins('onStateSwitchPost', [FlxG.state]);
	public function populate():Void runtime.populate();
	public function clearScripts(callDestroy:Bool = true):Void runtime.clearScripts(callDestroy);
	public function getPlugin(name:String):NightmareVisionScriptModule return runtime.getPlugin(name);
	public function callOnPlugin(name:String, callback:String, ?args:Array<Dynamic>):Dynamic
		return runtime.callOnPlugin(name, callback, args);
	public function callOnPlugins(callback:String, ?args:Array<Dynamic>):Void runtime.callOnPlugins(callback, args);

	override public function update(elapsed:Float):Void {
		runtime.callOnPlugins('onUpdate', [elapsed]);
		super.update(elapsed);
	}

	override public function destroy():Void {
		if (released) return;
		released = true;
		FlxG.signals.preStateSwitch.remove(onStateSwitch);
		FlxG.signals.postStateSwitch.remove(onStateSwitchPost);
		try runtime.destroy() catch (error:Dynamic)
			trace('[nightmare-vision-plugin-release-error] ' + runtime.ownerRoot + ': ' + Std.string(error));
		// onDestroy callbacks and native plugin objects may still read assets.
		// Release their cache only after those objects have finished teardown.
		if (assetPaths != null) {
			try assetPaths.releaseOwnerAssets() catch (error:Dynamic)
				trace('[nightmare-vision-plugin-release-error] ' + runtime.ownerRoot + ': ' + Std.string(error));
			assetPaths = null;
		}
		if (activeHost == this) activeHost = null;
		super.destroy();
	}
}
