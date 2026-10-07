package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
import haxe.io.Path;
#if cpp
import NightmareVisionVideoSprite;
#end

typedef NightmareVisionSplashStateHost = {
	var paths:NightmareVisionPaths;
	var readOwnerSave:String->Dynamic;
	/** This callback reads and constructs the class currently held by source
		Main.startMeta.initialState when the queued startup closure runs. */
	var initialStateConstructor:Void->FlxState;
	var switchStartup:(Void->FlxState)->Void;
	@:optional var onDisposed:Dynamic->Void;
}

/** Native splash port for the pinned Nightmare Vision Splash state. */
@:keep
class NightmareVisionSplashState extends FlxState {
	final host:NightmareVisionSplashStateHost;
	var cachedAutoPause:Bool = true;
	var startupDelay:FlxTimer;
	var spriteEvents:FlxTimer;
	var animationEvents:FlxTimer;
	var completionDelay:FlxTimer;
	var ownedTweens:Array<FlxTween> = [];
	var logo:FlxSprite;
	var logoScale:Float = 1;
	var completed:Bool = false;
	var resourcesCleaned:Bool = false;
	var audioRestored:Bool = false;
	var disposed:Bool = false;
	#if cpp
	var video:NightmareVisionVideoSprite;
	#end

	public function new(host:NightmareVisionSplashStateHost) {
		super();
		if (host == null || host.paths == null || host.readOwnerSave == null
			|| host.initialStateConstructor == null || host.switchStartup == null)
			throw '[nightmare-vision-splash] Missing captured source host';
		this.host = host;
	}

	public override function create():Void {
		cachedAutoPause = FlxG.autoPause;
		FlxG.autoPause = false;
		startupDelay = FlxTimer.wait(1, function():Void {
			startupDelay = null;
			if (completed) return;
			#if cpp
			var videoPath = host.paths.video('intro');
			if (host.paths.exists(videoPath) && !host.paths.isDirectory(videoPath)) {
				video = new NightmareVisionVideoSprite(this, host.paths);
				if (video.bitmap != null) {
					add(video);
					video.onFormat(function():Void {
						if (completed || video == null) return;
						video.setGraphicSize(0, FlxG.height);
						video.updateHitbox();
						video.screenCenter();
					});
					if (video.load(videoPath, sourceVideoMuted() ? [NightmareVisionVideoSprite.muted] : null)) {
						video.onEnd(finish);
						if (!completed && video != null) video.delayAndStart();
					} else {
						video.destroy();
						video = null;
						logoFunc();
					}
					return;
				}
				video.destroy();
				video = null;
			}
			#end
			logoFunc();
		});
	}

	public override function update(elapsed:Float):Void {
		if (completed) {
			super.update(elapsed);
			return;
		}
		if (logo != null) {
			logo.updateHitbox();
			logo.screenCenter();
		}
		if (FlxG.keys.justPressed.SPACE || FlxG.keys.justPressed.ENTER)
			finish();
		super.update(elapsed);
	}

	function logoFunc():Void {
		if (completed) return;
		var files = host.paths.listAllFilesInDirectory('images/branding/watermarks');
		files = [for (file in files) if (!host.paths.isDirectory(file)) file];
		if (files.length == 0) {
			finish();
			return;
		}
		var selected = FlxG.random.getObject(files);
		if (selected == null) {
			finish();
			return;
		}
		final imgPath:String = Path.withoutDirectory(Path.withoutExtension(selected));
		trace(files);

		logo = new FlxSprite().loadGraphic(host.paths.image('branding/watermarks/' + imgPath));
		logo.screenCenter();
		logo.visible = false;
		add(logo);

		logoScale = Math.min(FlxG.width / logo.width, FlxG.height / logo.height) * 0.8;
		logo.scale.set(logoScale, logoScale);
		logo.antialiasing = !StringTools.endsWith(imgPath, '-pixel');

		spriteEvents = new FlxTimer().start(1, function(_:FlxTimer):Void {
			if (completed) return;
			var step = 0;
			var events = new FlxTimer();
			animationEvents = events.start(0.25, function(timer:FlxTimer):Void {
				if (completed || logo == null) return;
				switch (step++) {
					case 0:
						FlxG.sound.volume = 1;
						FlxG.sound.play(host.paths.sound('intro'));
						logo.visible = true;
						logo.scale.set(0.2 * logoScale, 1.25 * logoScale);
						timer.reset(0.06125);
					case 1:
						logo.scale.set(1.25 * logoScale, 0.5 * logoScale);
						timer.reset(0.06125);
					case 2:
						logo.scale.set(1.125 * logoScale, 1.125 * logoScale);
						ownTween(logo.scale, {x:1 * logoScale, y:1 * logoScale}, 0.25,
							{ease:FlxEase.elasticOut});
						timer.reset(1.25);
					case 3:
						ownTween(logo.scale, {x:0.2 * logoScale, y:0.2 * logoScale}, 1.5,
							{ease:FlxEase.quadIn});
						ownTween(logo, {alpha:0}, 1.5, {
							ease:FlxEase.quadIn,
							onComplete:function(_:FlxTween):Void {
								completionDelay = FlxTimer.wait(0.8, finish);
							}
						});
				}
			});
		});
	}

	function finish():Void {
		if (completed) return;
		completed = true;
		cleanupResources();
		restoreSourceServices();
		host.switchStartup(function():FlxState return host.initialStateConstructor());
	}

	function restoreSourceServices():Void {
		if (audioRestored) return;
		audioRestored = true;
		var savedMute = host.readOwnerSave('mute');
		FlxG.sound.muted = Std.isOfType(savedMute, Bool) ? cast savedMute : false;
		var savedVolume = host.readOwnerSave('volume');
		FlxG.sound.volume = Std.isOfType(savedVolume, Int) || Std.isOfType(savedVolume, Float)
			? cast savedVolume : 1;
		FlxG.autoPause = cachedAutoPause;
	}

	function sourceVideoMuted():Bool {
		var savedMute = host.readOwnerSave('mute');
		return FlxG.sound.muted || (Std.isOfType(savedMute, Bool) && cast savedMute);
	}

	function ownTween(target:Dynamic, properties:Dynamic, duration:Float, options:Dynamic):FlxTween {
		var previous:Dynamic = Reflect.field(options, 'onComplete');
		Reflect.setField(options, 'onComplete', function(tween:FlxTween):Void {
			ownedTweens.remove(tween);
			if (previous != null) Reflect.callMethod(null, previous, [tween]);
		});
		var tween = FlxTween.tween(target, properties, duration, options);
		if (tween != null) ownedTweens.push(tween);
		return tween;
	}

	function cleanupResources():Void {
		if (resourcesCleaned) return;
		resourcesCleaned = true;
		for (timer in [startupDelay, spriteEvents, animationEvents, completionDelay]) {
			if (timer == null) continue;
			timer.cancel();
			timer.destroy();
		}
		startupDelay = null;
		spriteEvents = null;
		animationEvents = null;
		completionDelay = null;
		for (tween in ownedTweens.copy()) if (tween != null) tween.cancel();
		ownedTweens.resize(0);
		#if cpp
		if (video != null) {
			video.stop();
			video.destroy();
			video = null;
		}
		#end
	}

	public override function destroy():Void {
		if (disposed) return;
		disposed = true;
		if (!completed) {
			completed = true;
			cleanupResources();
			restoreSourceServices();
		}
		super.destroy();
		if (host.onDisposed != null) host.onDisposed(this);
	}
}
