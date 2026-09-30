package;

/** Live source window operations. Providers permit isolated native runs and
 * do not retain a PlayState when persistent plugins outlive a chart. */
@:keep
class NightmareVisionWindowUtil {
	var currentWindow:Void->lime.ui.Window;
	var appTitle:Void->String;
	var makePoint:(Float, Float)->Dynamic;
	public function new(currentWindow:Void->lime.ui.Window, appTitle:Void->String, makePoint:(Float, Float)->Dynamic) {
		this.currentWindow = currentWindow;
		this.appTitle = appTitle;
		this.makePoint = makePoint;
	}
	public var monitorResolutionWidth(get, never):Float;
	function get_monitorResolutionWidth():Float return currentWindow().display.bounds.width;
	public var monitorResolutionHeight(get, never):Float;
	function get_monitorResolutionHeight():Float return currentWindow().display.bounds.height;
	public var defaultAppTitle(get, never):String;
	function get_defaultAppTitle():String return appTitle();
	public var windowWidth(get, never):Int;
	function get_windowWidth():Int return currentWindow().width;
	public var windowHeight(get, never):Int;
	function get_windowHeight():Int return currentWindow().height;
	public var windowX(get, set):Int;
	function get_windowX():Int return currentWindow().x;
	function set_windowX(value:Int):Int return currentWindow().x = value;
	public var windowY(get, set):Int;
	function get_windowY():Int return currentWindow().y;
	function set_windowY(value:Int):Int return currentWindow().y = value;
	public var borderless(get, set):Bool;
	function get_borderless():Bool return currentWindow().borderless;
	function set_borderless(value:Bool):Bool return currentWindow().borderless = value;
	public var opacity(get, set):Float;
	function get_opacity():Float return currentWindow().opacity;
	function set_opacity(value:Float):Float return currentWindow().opacity = value;
	public var minimized(get, set):Bool;
	function get_minimized():Bool return currentWindow().minimized;
	function set_minimized(value:Bool):Bool return currentWindow().minimized = value;
	public var maximized(get, set):Bool;
	function get_maximized():Bool return currentWindow().maximized;
	function set_maximized(value:Bool):Bool return currentWindow().maximized = value;
	public function getMonitorResolution():Dynamic return makePoint(monitorResolutionWidth, monitorResolutionHeight);
	public function getWindowPosition():Dynamic return makePoint(windowX, windowY);
	public function getWindowSize():Dynamic return makePoint(windowWidth, windowHeight);
	public function setTitle(?arg:String, append:Bool = false, prepend:Bool = false):Void {
		if (arg == null) arg = defaultAppTitle;
		var window = currentWindow();
		if (prepend) window.title = arg + window.title;
		else if (append) window.title += arg;
		else window.title = arg;
	}
	public function resetTitle():Void currentWindow().title = defaultAppTitle;
	public function setWindowPosition(x:Int, y:Int):Void { windowX = x; windowY = y; }
	public function centerWindow():Void {
		windowX = Std.int((monitorResolutionWidth - windowWidth) / 2);
		windowY = Std.int((monitorResolutionHeight - windowHeight) / 2);
	}
	public function centerWindowOnPoint(?point:Dynamic):Void {
		windowX = Std.int((point == null ? 0 : point.x) - windowWidth / 2);
		windowY = Std.int((point == null ? 0 : point.y) - windowHeight / 2);
	}
	public function getCenterWindowPoint():Dynamic return makePoint(windowX + windowWidth / 2, windowY + windowHeight / 2);
	public function isWindowOnScreen():Bool return windowX >= 0 && windowY >= 0
		&& windowX + windowWidth <= monitorResolutionWidth && windowY + windowHeight <= monitorResolutionHeight;
	public function clampWindowToScreen():Void if (!isWindowOnScreen()) centerWindow();
	public function flash():Void currentWindow().alert('', '');
	public function setGameDimensions(width:Int, height:Int, cameras:Array<Dynamic>):Void
		throw '[nightmare-vision-window-unsupported] setGameDimensions requires the source scale mode';
	public function resetWindow():Void
		throw '[nightmare-vision-window-unsupported] resetWindow requires source startup dimensions and DPI restoration';
}
