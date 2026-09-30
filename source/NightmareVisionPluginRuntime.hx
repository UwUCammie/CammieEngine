package;

import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;

/** Source ModPlugin script ownership, independent of its native group/driver.
	The release PluginsManager spelling aliases the same real plugin calls. */
@:keep
class NightmareVisionPluginRuntime {
	public final ownerRoot:String;
	public final scripts:NightmareVisionScriptGroup;
	public var released(default, null):Bool = false;
	final discover:Void->Array<NightmareVisionScriptEntry>;
	final read:String->String;
	final configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void;
	final report:String->String->Dynamic->Void;
	final clearMembers:Void->Void;

	public function new(ownerRoot:String, parent:Dynamic,
		discover:Void->Array<NightmareVisionScriptEntry>, read:String->String,
		configure:NightmareVisionScriptInterp->NightmareVisionScriptEntry->Void,
		report:String->String->Dynamic->Void, clearMembers:Void->Void) {
		this.ownerRoot = ownerRoot;
		this.discover = discover;
		this.read = read;
		this.configure = configure;
		this.report = report;
		this.clearMembers = clearMembers;
		scripts = new NightmareVisionScriptGroup(parent, report);
	}

	public function canReuseFor(root:String):Bool return !released && root == ownerRoot;

	public function populate():Void {
		if (released) throw '[nightmare-vision-plugin-error] Cannot populate a released plugin owner';
		try clearScripts() catch (error:Dynamic) report('plugins', 'clear', error);
		for (entry in discover()) {
			try {
				scripts.loadSource(entry.name, read(entry.path), function(interp) {
					configure(interp, entry);
				}, null, true);
			} catch (error:Dynamic) report(entry.relative, 'load', error);
		}
	}

	public function getPlugin(name:String):NightmareVisionScriptModule return scripts.getScript(name);

	public function callOnPlugin(name:String, callback:String, ?args:Array<Dynamic>):Dynamic {
		if (released) return null;
		var script = getPlugin(name);
		return script == null ? null : script.call(callback, args);
	}

	public function callPluginFunc(name:String, callback:String, ?args:Array<Dynamic>):Dynamic
		return callOnPlugin(name, callback, args);

	public function callOnPlugins(callback:String, ?args:Array<Dynamic>):Void {
		if (!released) scripts.call(callback, args);
	}

	public function clearScripts(callDestroy:Bool = true):Void {
		if (released) return;
		var failure:Dynamic = null;
		try scripts.clear(callDestroy) catch (error:Dynamic) failure = error;
		try clearMembers() catch (error:Dynamic) {
			if (failure == null) failure = error;
			else report('plugins', 'member-release', error);
		}
		if (failure != null) throw failure;
	}

	public function destroy():Void {
		if (released) return;
		var failure:Dynamic = null;
		try clearScripts() catch (error:Dynamic) failure = error;
		try scripts.destroy() catch (error:Dynamic) {
			if (failure == null) failure = error;
			else report('plugins', 'script-release', error);
		}
		released = true;
		if (failure != null) throw failure;
	}
}
