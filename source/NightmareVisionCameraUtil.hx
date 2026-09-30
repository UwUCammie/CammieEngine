package;

/** Camera stack queries remain live across scripted state transitions. */
@:keep
class NightmareVisionCameraUtil {
	var getCameras:Void->Array<Dynamic>;
	var createCamera:Bool->Dynamic;
	public function new(getCameras:Void->Array<Dynamic>, ?createCamera:Bool->Dynamic) {
		this.getCameras = getCameras;
		this.createCamera = createCamera;
	}
	public var lastCamera(get, never):Dynamic;
	function get_lastCamera():Dynamic {
		var cameras = getCameras();
		return cameras[cameras.length - 1];
	}
	public function quickCreateCam(add:Bool = true):Dynamic {
		if (createCamera == null)
			throw '[nightmare-vision-camera-unsupported] quickCreateCam requires the source FunkinCamera blend renderer';
		return createCamera(add);
	}
}
