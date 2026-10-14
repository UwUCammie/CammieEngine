package;

import flixel.FlxG;
import flixel.FlxState;
import lime.graphics.RenderContext;
import openfl.display.Sprite;
import openfl.display.Bitmap;
import openfl.display.BitmapData;
import openfl.filters.GlowFilter;
import openfl.filters.DropShadowFilter;
import openfl.events.UncaughtErrorEvent;
import openfl.text.TextField;
import openfl.text.TextFormat;

/** Native display overlay survives Flixel state destruction and bitmap pruning.
	Preparation stays on the foreground thread. Lime's render callback records
	the rendered overlay; the next game draw occurs after that frame's flip. */
class SongLoadingScreen {
	public static var active(default, null):Bool = false;
	public static var preparing(default, null):Bool = false;
	static var installed:Bool = false;
	static var overlay:Sprite;
	static var design:Sprite;
	static var artwork:Bitmap;
	static var stars:Array<Sprite> = [];
	static var animationStarted:Float = 0;
	static var fill:Sprite;
	static var progress:SongLoadingProgress;
	static var pending:Void->Void;
	static var initialFrameRendered:Bool = false;
	static var readyFrameRendered:Bool = false;
	static var requestNumber:Int = 0;
	static var stateRequested:Bool = false;
	static var viewportWaitLogged:Bool = false;
	static var phaseFrames:Int = 0;
	static var lastWorkPresentation:Float = 0;
	static var presentingWork:Bool = false;
	static var workFrames:Int = 0;
	static var phaseWorkFrames:Int = 0;
	static var enterFrames:Int = 0;
	static var gameUpdates:Int = 0;

	public static function install():Void {
		if (installed || Main.instance == null || FlxG.game == null) return;
		installed = true;
		Main.instance.stage.addEventListener(openfl.events.Event.ENTER_FRAME,
			function(_:openfl.events.Event):Void enterFrames++);
		FlxG.signals.preUpdate.add(function():Void gameUpdates++);
		SongLoadingWork.install(function(kind:String):Void {
			if (active && (kind != 'cleanup' || progress.phase == 'cleanup')) resourceComplete(true);
		});
		// Installed after Main's cleanup listeners. These completions therefore
		// include old-state teardown/cache pruning and dead sound retirement.
		FlxG.signals.preStateCreate.add(function(_state:FlxState):Void {
			if (active) {
				complete(2, progress.label);
				if (!Std.isOfType(_state, PlayState)) beginWork('menu', 1, 0.65, 0.98);
			}
		});
		FlxG.signals.postStateSwitch.add(function():Void {
			if (active) {
				if (Std.isOfType(FlxG.state, PlayState))
					progress.describe('ready', 'Track ready', cast(FlxG.state, PlayState).songLoadingSummary());
				else progress.describe('ready', 'Menu ready', 'Song resources cleared. Menu created.');
				workUnit();
				complete(3, progress.label);
			}
		});
		FlxG.signals.postDraw.add(afterDraw);
		// OpenFL's Stage render listener has priority 0. This listener runs after
		// Stage.__render, unlike Flixel postDraw, which runs during ENTER_FRAME.
		// Lime flips only after all onRender callbacks return. Work is therefore
		// deferred to the next postDraw rather than run inside this callback.
		lime.app.Application.current.window.onRender.add(beforeRender, false, 2147483647);
		lime.app.Application.current.window.onRender.add(afterRender, false, -2147483647);
		openfl.Lib.current.loaderInfo.uncaughtErrorEvents.addEventListener(
			UncaughtErrorEvent.UNCAUGHT_ERROR, function(_event:UncaughtErrorEvent):Void cancel());
	}

	/** Duplicate accepts are ignored; nested calls from the preparation callback
		are the original single state request and execute once. */
	public static function queue(title:String, detail:String, action:Void->Void, chartPreparation:Bool = false):Bool {
		if (preparing) {
			// Chart preparation requests its original transition exactly once,
			// but only after this next action has its own presented frame.
			if (pending != null) return false;
			pending = action;
			initialFrameRendered = false;
			describeWork(title, false);
			redraw(); log('phase-queued');
			return true;
		}
		if (active) return false;
		if (!installed) {action(); return true;}
		requestNumber++; phaseFrames = 0; workFrames = 0; lastWorkPresentation = 0;
		stateRequested = false; viewportWaitLogged = false;
		progress = new SongLoadingProgress();
		if (chartPreparation) progress.beginWork('chart', 1, 0, 0.05);
		describeWork(title, chartPreparation);
		active = true;
		pending = action;
		initialFrameRendered = false;
		readyFrameRendered = false;
		try build(title, detail) catch (error:Dynamic) {cancel(); throw error;}
		log('shown');
		return true;
	}

	static function describeWork(title:String, chartPreparation:Bool):Void {
		if (chartPreparation)
			progress.describe('chart', 'Reading chart', 'Parsing the selected difficulty and its defaults.');
		else if (title == 'LEAVING THE STAGE')
			progress.describe('exit', 'Closing song and opening menu', 'Clearing song resources, then creating the next scene.');
		else
			progress.describe('scene', 'Creating the song scene', SongLoadingProgress.chartDetail(PlayState.SONG));
	}

	static function text(x:Float, y:Float, width:Float, value:String, size:Int, color:Int):TextField {
		var field = new TextField();
		var font = openfl.utils.Assets.getFont(Paths.font('funkin.otf'));
		field.defaultTextFormat = new TextFormat(font.fontName, size, color);
		field.embedFonts = true;
		field.x = x; field.y = y; field.width = width; field.height = size * 5;
		field.wordWrap = true;
		field.selectable = false; field.mouseEnabled = false;
		field.filters = [new GlowFilter(0x1B073C, 1, 3, 3, 4, 1)];
		field.text = value; design.addChild(field);
		return field;
	}

	static function build(title:String, detail:String):Void {
		overlay = new Sprite(); overlay.mouseEnabled = false; overlay.mouseChildren = false;
		design = new Sprite(); overlay.addChild(design);
		design.graphics.beginFill(0x101622); design.graphics.drawRect(0, 0, 1280, 720); design.graphics.endFill();
		buildStars();
		// The official FNF loading lineup and graffiti wordmark, reused intact.
		// Own the bitmap outside Flixel's cache so song-exit pruning cannot
		// destroy the screen while the next scene is being constructed.
		#if sys
		var data = BitmapData.fromFile('assets/images/loading/funkay.png');
		#else
		var data = openfl.utils.Assets.getBitmapData('assets/images/loading/funkay.png').clone();
		#end
		if (data == null) throw 'Loading artwork is unavailable';
		// Cut the lineup out on its own pixels, before any scaling can smear the
		// backdrop into the outlines, then lift it off the background with a shadow.
		// Black would vanish on the navy screen, so the shadow is a deep violet.
		var bounds = new openfl.geom.Rectangle(0, 0, data.width, data.height);
		var pixels = data.getPixels(bounds);
		SongLoadingMatte.apply(pixels, data.width, data.height);
		pixels.position = 0; data.setPixels(bounds, pixels);
		artwork = new Bitmap(data); artwork.smoothing = true;
		artwork.filters = [new DropShadowFilter(16, 55, 0x2A1B63, 0.9, 5, 5, 1, 2)];
		var artScale = 720 / data.height;
		artwork.scaleX = artwork.scaleY = artScale;
		artwork.x = (1280 - data.width * artScale) / 2;
		design.addChild(artwork);
		// Keep track information inside the artwork's empty upper-right area.
		text(812, 102, 392, title == 'LEAVING THE STAGE' ? 'BACK TO THE MENU' : 'UP NEXT', 26, 0xFF16D2);
		text(812, 152, 392, FreeplaySongTitle.display(detail), 34, 0xFFFFFF).height = 142;
		var track = new Sprite(); design.addChild(track);
		track.graphics.beginFill(0x1B073C); track.graphics.drawRect(0, 702, 1280, 18); track.graphics.endFill();
		fill = new Sprite(); design.addChild(fill);
		Main.instance.addChild(overlay);
		layout(); redraw();
	}

	static function buildStars():Void {
		animationStarted = haxe.Timer.stamp();
		var colors = [0xFF66B7, 0x80E3D0, 0x8667E8];
		// A deep field: many small faint stars and a few large bright ones. Size
		// and brightness come from fixed sequences, so the screen never changes.
		for (i in 0...STAR_COUNT) {
			var star = new Sprite();
			var radius = starRadius(i);
			star.graphics.beginFill(colors[i % colors.length]);
			for (point in 0...10) {
				var angle = point * Math.PI / 5 - Math.PI / 2;
				var length = point % 2 == 0 ? radius : radius * 0.45;
				var x = Math.cos(angle) * length, y = Math.sin(angle) * length;
				if (point == 0) star.graphics.moveTo(x, y); else star.graphics.lineTo(x, y);
			}
			star.graphics.endFill();
			design.addChild(star); stars.push(star);
		}
		animateStars();
	}

	public static inline var STAR_COUNT:Int = 84;
	static inline function fraction(value:Float):Float return value - Math.floor(value);
	/** 3 to 27 pixels, weighted towards small stars. */
	public static function starRadius(index:Int):Float {
		var spread = fraction(index * 0.3819660112501051);
		return 3 + spread * spread * 24;
	}
	/** Resting opacity of a star, 0.06 to 0.5, independent of its size. */
	public static function starOpacity(index:Int):Float return 0.06 + fraction(index * 0.6180339887498949 + 0.25) * 0.44;

	static function animateStars():Void {
		var time = haxe.Timer.stamp() - animationStarted;
		for (i in 0...stars.length) {
			var star = stars[i];
			star.x = (i * 173 + time * (8 + i % 7)) % 1400 - 60;
			star.y = (i * 117) % 640 + 30 + Math.sin(time * 0.7 + i) * 12;
			star.rotation = (time * (4 + i % 5) + i * 31) % 360;
			// Each star twinkles around its own brightness.
			star.alpha = starOpacity(i) * (0.75 + 0.25 * Math.sin(time * 1.1 + i));
		}
	}

	static function beforeRender(context:RenderContext):Void {
		if (!active) return;
		layout();
	}

	static function layout():Void {
		if (overlay == null || Main.instance.stage == null) return;
		// The stage can still report its previous size on the first resized
		// frame. Window coordinates match the native renderer's logical size.
		var window = lime.app.Application.current.window;
		var width = window.width;
		var height = window.height;
		var scale = Math.min(width / 1280, height / 720);
		overlay.graphics.clear(); overlay.graphics.beginFill(0x101622);
		overlay.graphics.drawRect(0, 0, width, height); overlay.graphics.endFill();
		design.scaleX = design.scaleY = scale;
		design.x = (width - 1280 * scale) / 2; design.y = (height - 720 * scale) / 2;
	}

	static function redraw():Void {
		fill.graphics.clear();
		if (progress.fraction() > 0) {
			fill.graphics.beginFill(0xFF16D2);
			fill.graphics.drawRect(4, 706, 1272 * progress.fraction(), 10); fill.graphics.endFill();
		}
	}

	/** Called on the foreground thread at existing work boundaries, never from
	 * a timer. Lifecycle callbacks retain their original uninterrupted order. */
	public static function beginWork(name:String, total:Float, start:Float, end:Float):Void {
		if (!active) return;
		phaseWorkFrames = 0;
		progress.beginWork(name, total, start, end);
		redraw();
	}
	public static function workUnit(units:Float = 1):Void {
		if (!active || progress.completed >= 3) return;
		progress.worked(units); presentWork();
	}
	public static function resourceComplete<T>(value:T):T {
		if (active && progress.completed < 3) {progress.worked(1, true); presentWork();}
		return value;
	}
	static function presentWork():Void {
		if (!active || progress.completed >= 3 || presentingWork || progress.workTotal <= 0) return;
		var now = haxe.Timer.stamp();
		if (now - lastWorkPresentation < 1 / 30) return;
		lastWorkPresentation = now;
		layout(); animateStars(); redraw();
		// Native overlay-only presentation is supplied below. No game update,
		// input event, script hook or display-list broadcast is dispatched.
		presentOverlay();
	}
	static function presentOverlay():Void {
		#if (cpp && lime)
		var window = lime.app.Application.current.window;
		if (overlay == null || window.width <= 0 || window.height <= 0 || !renderViewportReady()) return;
		@:privateAccess var renderer = Main.instance.stage.__renderer;
		if (!Std.isOfType(renderer, openfl.display.OpenGLRenderer)) return;
		var gl:openfl.display.OpenGLRenderer = cast renderer;
		@:privateAccess if (gl.__defaultRenderTarget != null || gl.__numClipRects != 0
			|| gl.__stencilReference != 0 || gl.__maskObjects.length != 0) return;
		@:privateAccess var context = gl.__context3D;
		@:privateAccess var rendererCleared = gl.__cleared;
		@:privateAccess var contextCleared = context.__cleared;
		@:privateAccess var contextPresent = context.__present;
		var beforeEnterFrames = enterFrames, beforeGameUpdates = gameUpdates;
		presentingWork = true;
		var restore = function():Void {
			@:privateAccess gl.__cleared = rendererCleared;
			@:privateAccess context.__cleared = contextCleared;
			@:privateAccess context.__present = contextPresent;
			presentingWork = false;
		};
		try {
			// Pinned Lime 8.3.2 only makes this window's context current here.
			// Render this surviving sprite only, never Stage.__render/ENTER_FRAME.
			@:privateAccess window.__backend.render();
			@:privateAccess overlay.__update(false, true);
			context.setRenderToBackBuffer();
			@:privateAccess gl.__clear();
			@:privateAccess gl.__render(overlay);
			workFrames++; phaseWorkFrames++;
			if (enterFrames != beforeEnterFrames || gameUpdates != beforeGameUpdates)
				throw 'Loading repaint dispatched a gameplay update';
			log('work-presented');
			#if sys
			if (Sys.args().indexOf('--profile-song-loading') >= 0 && phaseWorkFrames <= 24)
				capture(progress.phase + '-work-' + workFrames);
			#end
			@:privateAccess window.__backend.contextFlip();
		} catch (error:Dynamic) {restore(); throw error;}
		restore();
		#end
	}

	static function complete(stage:Int, label:String):Void {
		progress.finish(stage, label); redraw(); log('completed');
	}

	static function afterDraw():Void {
		if (!active) return;
		if (authoredOutroStarted()) {cancel(); return;}
		layout();
		// Stage ENTER_FRAME can finish a long synchronous state creation after
		// the early Lime callback. Sample animation time here, before rendering.
		animateStars();
		if (pending != null) {
			if (!initialFrameRendered) return;
			var action = pending; pending = null;
			preparing = true;
			log('work-started');
			try action() catch (error:Dynamic) {cancel(); throw error;}
			preparing = false;
			if (authoredOutroStarted()) {cancel(); return;}
			if (pending != null) {workUnit(); complete(1, progress.label); return;}
			if (!stateRequested) {cancel(); return;}
			if (active) complete(1, progress.label);
			return;
		}
		if (progress.completed == 3) {
			// The new state exists and the overlay still covers it: the best
			// moment to clear out everything loading left behind.
			EngineMemory.collectNow(true, 'loading-handoff', true);
			complete(4, progress.label);
		}
		else if (progress.completed == 4 && readyFrameRendered) {
			log('hidden'); cancel();
		}
	}

	static function afterRender(context:RenderContext):Void {
		if (!active) return;
		if (!renderViewportReady()) {
			if (!viewportWaitLogged) {log('waiting-for-resized-viewport'); viewportWaitLogged = true;}
			return;
		}
		if (pending != null && !initialFrameRendered) {
			capture(phaseFrames++ == 0 ? 'initial' : progress.phase);
			initialFrameRendered = true;
			log('work-phase-rendered');
		} else if (progress.completed == 4 && !readyFrameRendered) {
			capture('ready');
			readyFrameRendered = true;
			log('ready-frame-rendered');
		}
	}

	/** A native window can resize before OpenFL updates its stage, projection
		and backbuffer. Such a rendered frame is still clipped to the old size.
		Only accept the handshake once the actual renderer has caught up. */
	static function renderViewportReady():Bool {
		var stage = Main.instance.stage;
		var window = lime.app.Application.current.window;
		var width = Std.int(window.width * window.scale);
		var height = Std.int(window.height * window.scale);
		#if openfl_dpi_aware
		var logicalWidth = width, logicalHeight = height;
		#else
		var logicalWidth = window.width, logicalHeight = window.height;
		#end
		if (stage.stageWidth != logicalWidth || stage.stageHeight != logicalHeight) return false;
		@:privateAccess var renderer = stage.__renderer;
		if (renderer == null) return false;
		if (Std.isOfType(renderer, openfl.display.OpenGLRenderer)) {
			var gl:openfl.display.OpenGLRenderer = cast renderer;
			@:privateAccess if (gl.__width != width || gl.__height != height
				|| gl.__displayWidth != width || gl.__displayHeight != height) return false;
		}
		if (stage.context3D != null && (stage.context3D.backBufferWidth != logicalWidth
			|| stage.context3D.backBufferHeight != logicalHeight)) return false;
		return true;
	}

	/** Preparation may abort without scheduling a state, for example if import
		readiness changes before the deferred chart read. */
	public static function stateRequestStarted():Void {
		if (active) stateRequested = true;
	}

	static function authoredOutroStarted():Bool {
		var state = FlxG.state == null ? null : FlxG.state.subState;
		while (state != null) {
			if (Std.isOfType(state, CodenameMusicBeatTransition)) return true;
			state = state.subState;
		}
		return false;
	}

	public static function cancel():Void {
		if (overlay != null && overlay.parent != null) overlay.parent.removeChild(overlay);
		if (artwork != null) {
			artwork.filters = [];
			if (artwork.bitmapData != null) artwork.bitmapData.dispose();
		}
		artwork = null; stars.resize(0);
		overlay = null; design = null; fill = null;
		pending = null; preparing = false; active = false;
	}

	/** Read the current rendered window frame after OpenFL Stage.__render,
		before Lime flips it. Opt-in only; preparation waits for the next frame. */
	static function capture(phase:String):Void {
		#if sys
		if (Sys.args().indexOf('--profile-song-loading') < 0) return;
		try {
			var directory = 'tmp/song-loading-captures';
			if (!sys.FileSystem.exists(directory)) sys.FileSystem.createDirectory(directory);
			var image = lime.app.Application.current.window.readPixels();
			if (image == null) throw 'Window framebuffer unavailable';
			var path = directory + '/song-loading-' + requestNumber + '-' + phase + '.png';
			sys.io.File.saveBytes(path, image.encode());
			Sys.println('SONG_LOADING_CAPTURE|' + haxe.Json.stringify({phase:phase,path:path,request:requestNumber}));
		} catch (error:Dynamic) {
			Sys.println('SONG_LOADING_CAPTURE_ERROR|' + Std.string(error));
			throw error;
		}
		#end
	}

	static function log(phase:String):Void {
		#if sys
		if (RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--profile-song-loading') >= 0)
			Sys.println('SONG_LOADING|' + haxe.Json.stringify({phase:phase,
				work:progress.phase, action:progress.label, detail:progress.detail, completed:progress.completed, total:SongLoadingProgress.TOTAL, fraction:progress.fraction(), workCompleted:progress.workCompleted, workTotal:progress.workTotal, enterFrames:enterFrames, gameUpdates:gameUpdates, time:haxe.Timer.stamp()}));
		#end
	}
}
