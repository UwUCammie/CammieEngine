package;

import flixel.FlxCamera;
import flixel.FlxG;
import flixel.system.frontEnds.CameraFrontEnd;
import haxe.ds.ObjectMap;

private typedef CodenameHostCameraChange = {
	var scope:CodenameCameraFacade;
	var released:Bool;
	var camera:FlxCamera;
	var present:Bool;
	var index:Int;
	var before:FlxCamera;
	var after:FlxCamera;
	var defaultTarget:Bool;
}

/** One script's reversible access to Flixel's process-wide camera frontend. */
class CodenameCameraFacade {
	static var ownedBy:ObjectMap<FlxCamera, CodenameCameraFacade> = new ObjectMap();
	static var hostLease:ObjectMap<FlxCamera, Array<CodenameHostCameraChange>> = new ObjectMap();

	final frontend:CameraFrontEnd;
	final hosts:Array<FlxCamera>;
	final owner:String;
	final owned:Array<FlxCamera> = [];
	final hostChanges:Array<CodenameHostCameraChange> = [];
	var oldMain:FlxCamera = null;
	var mainRecorded = false;
	var selectedMain:FlxCamera = null;
	var released = false;

	public function new(frontend:CameraFrontEnd, hostCameras:Array<FlxCamera>, ?owner:String) {
		this.frontend = frontend;
		this.hosts = hostCameras == null ? [] : hostCameras.copy();
		this.owner = owner;
	}

	/** A snapshot supports contains/indexOf/iteration without exposing the live array. */
	public var list(get, never):Array<FlxCamera>;
	function get_list():Array<FlxCamera> return frontend.list.copy();
	/** Codename stage scripts preserve Flixel's default draw targets while
	 * rebuilding camera order. Return a snapshot so scripts cannot mutate the
	 * process-wide target list without going through this scope. */
	public var defaults(get, never):Array<FlxCamera>;
	function get_defaults():Array<FlxCamera> {
		@:privateAccess var targets = frontend.defaults;
		return targets.copy();
	}

	function checkLive():Void {
		if (released) throw '[codename-camera] Camera scope was released';
	}

	function owns(camera:FlxCamera):Bool return ownedBy.get(camera) == this;

	function rememberMain():Void {
		if (!mainRecorded) {
			oldMain = FlxG.camera;
			mainRecorded = true;
		}
	}

	/** Call from the script constructor hook, including when creation fails
	 * before the camera is added to FlxG.cameras. */
	public function adoptCreated(camera:FlxCamera):FlxCamera {
		checkLive();
		remember(camera);
		return camera;
	}

	function remember(camera:FlxCamera):Void {
		if (camera == null) throw '[codename-camera] Null camera';
		if (hosts.indexOf(camera) >= 0) {
			var leases = hostLease.get(camera);
			if (leases == null) {
				leases = [];
				hostLease.set(camera, leases);
			}
			if (leases.length > 0 && leases[leases.length - 1].scope != this
				&& (owner == null || owner != leases[leases.length - 1].scope.owner))
				throw '[codename-camera] Host camera is being reordered by another script';
			var index = frontend.list.indexOf(camera);
			@:privateAccess var defaults = frontend.defaults;
			var change = {scope:this, released:false, camera:camera, present:index >= 0, index:index,
				before:index > 0 ? frontend.list[index - 1] : null,
				after:index >= 0 && index + 1 < frontend.list.length ? frontend.list[index + 1] : null,
				defaultTarget:defaults.indexOf(camera) >= 0};
			hostChanges.push(change);
			leases.push(change);
		} else {
			var owner = ownedBy.get(camera);
			if (owner != null && owner != this)
				throw '[codename-camera] Camera belongs to another script';
			if (owner == null) {
				if (frontend.list.indexOf(camera) >= 0)
					throw '[codename-camera] Existing unowned camera cannot be claimed';
				ownedBy.set(camera, this);
				owned.push(camera);
			}
		}
	}

	function detach(camera:FlxCamera):Void {
		if (frontend.list.indexOf(camera) >= 0) frontend.remove(camera, false);
	}

	function attachAt<T:FlxCamera>(camera:T, position:Int, defaultDrawTarget:Bool):T {
		if (position >= frontend.list.length)
			return frontend.add(camera, defaultDrawTarget);
		return frontend.insert(camera, position, defaultDrawTarget);
	}

	public function add<T:FlxCamera>(camera:T, defaultDrawTarget:Bool = true):T {
		checkLive();
		remember(camera);
		detach(camera);
		return frontend.add(camera, defaultDrawTarget);
	}

	public function insert<T:FlxCamera>(camera:T, position:Int, defaultDrawTarget:Bool = true):T {
		checkLive();
		remember(camera);
		detach(camera);
		return attachAt(camera, position, defaultDrawTarget);
	}

	public function remove(camera:FlxCamera, destroy:Bool = true):Void {
		checkLive();
		if (camera == null || (hosts.indexOf(camera) < 0 && !owns(camera)))
			throw '[codename-camera] Cannot remove an unowned camera';
		remember(camera);
		detach(camera);
		if (destroy && hosts.indexOf(camera) >= 0)
			trace('[codename-camera] Protected host camera from requested destruction');
		if (destroy && owns(camera)) {
			ownedBy.remove(camera);
			owned.remove(camera);
			camera.destroy();
		}
	}

	public function setDefaultDrawTarget(camera:FlxCamera, value:Bool):Void {
		checkLive();
		if (camera == null || (hosts.indexOf(camera) < 0 && !owns(camera)))
			throw '[codename-camera] Cannot change an unowned camera';
		remember(camera);
		frontend.setDefaultDrawTarget(camera, value);
	}

	public function selectMain(camera:FlxCamera):FlxCamera {
		checkLive();
		if (camera == null || frontend.list.indexOf(camera) < 0)
			throw '[codename-camera] Main camera must already be registered';
		remember(camera);
		rememberMain();
		selectedMain = camera;
		return FlxG.camera = camera;
	}

	/** Native reset destroys every camera. Emulate its visible selection without
	 * destroying host cameras or another script's cameras. */
	public function reset(?newCamera:FlxCamera):Void {
		checkLive();
		for (camera in frontend.list)
			if (hosts.indexOf(camera) < 0 && !owns(camera))
				throw '[codename-camera] reset would remove another script camera';
		if (newCamera == null) newCamera = new FlxCamera();
		remember(newCamera);
		rememberMain();
		for (camera in frontend.list.copy()) {
			remember(camera);
			detach(camera);
		}
		selectedMain = frontend.add(newCamera);
		FlxG.camera = newCamera;
	}

	/** Replay only this scope's host-camera edits; never replace the whole list. */
	public function release():Void {
		if (released) return;
		// Removing an owned camera can update FlxG.camera through frontend listeners.
		// Decide whether this scope owns the current selection before detaching it.
		var restoreMain = mainRecorded && selectedMain != null && FlxG.camera == selectedMain;
		// Flixel's state switch destroys registered cameras before the old
		// state's scripts are released. A host detached by a script may still
		// have a flashSprite, but belongs to that old state just the same.
		var frontendReset = false;
		for (camera in hosts) if (camera.flashSprite == null) frontendReset = true;
		for (camera in owned) if (camera.flashSprite == null) frontendReset = true;
		released = true;
		for (camera in owned) {
			detach(camera);
			ownedBy.remove(camera);
			// FlxGame.switchState resets and destroys all cameras before the old
			// PlayState releases its scripts. A second destroy is unnecessary.
			if (camera.flashSprite != null) camera.destroy();
		}
		owned.resize(0);
		for (i in 0...hostChanges.length) {
			var change = hostChanges[hostChanges.length - 1 - i];
			var camera = change.camera;
			change.released = true;
			var leases = hostLease.get(camera);
			while (leases != null && leases.length > 0 && leases[leases.length - 1].released) {
				var latest = leases.pop();
				detach(camera);
				// A host camera destroyed by Flixel's state-switch reset cannot be
				// reattached: CameraFrontEnd.insert would add a null flashSprite.
				if (latest.present && !frontendReset && camera.flashSprite != null) {
					var index = latest.index;
					if (latest.after != null && frontend.list.indexOf(latest.after) >= 0)
						index = frontend.list.indexOf(latest.after);
					else if (latest.before != null && frontend.list.indexOf(latest.before) >= 0)
						index = frontend.list.indexOf(latest.before) + 1;
					if (index < 0) index = frontend.list.length;
					attachAt(camera, index, latest.defaultTarget);
				}
			}
			if (leases != null && leases.length == 0) hostLease.remove(camera);
		}
		hostChanges.resize(0);
		if (restoreMain) {
			if (oldMain != null && frontend.list.indexOf(oldMain) >= 0)
				FlxG.camera = oldMain;
			else {
				var fallback:FlxCamera = null;
				for (host in hosts)
					if (frontend.list.indexOf(host) >= 0) {
						fallback = host;
						break;
					}
				FlxG.camera = fallback;
				if (oldMain != null)
					trace('[codename-camera] Original main camera was removed; using a registered host camera');
			}
		}
	}
}
