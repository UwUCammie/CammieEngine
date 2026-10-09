package;

import flixel.FlxG;
import lime.app.Application;

/** Isolated source-call and GPU evidence, enabled only by the runtime smoke harness. */
class RuntimeSmokeLegacySplash {
	public static function verify(note:Note):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_LEGACY_SPLASH_SMOKE') != '1') return;
		var state = PlayState.instance;
		var errors:Array<String> = [];
		var order:Array<String> = [];
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'module'});
		var module = NightmareVisionScriptModule.fromSource('__splash_probe',
			"import gameObjects.NoteSplash; function create() { return new NoteSplash(200,200,0); }"
			+ "function poolCheck(){ return grpNoteSplashes == game.grpNoteSplashes && Reflect.getProperty(game, 'grpNoteSplashes') == grpNoteSplashes; }"
			+ "function invoke(n) { game.spawnNoteSplashOnNote(n); }"
			+ "function reflected() { return Type.createInstance(Type.resolveClass('gameObjects.NoteSplash'),[400,200,1]); }"
			+ "function configure(s) { s.loadAnims('noteSplashes'); s.setupNoteSplash(200,200,0,null,0.25,-0.2,0.4,null); }"
			+ "function noteSplash(offsets) { record('skin'); offsets[0].set(11,13); return 'noteSplashes'; }"
			+ "function quants() { record('quants'); return false; }"
			+ "function spawnNoteSplash(s,d,n,p,l) { record('spawn'); verifySpawn(s,d,n,p,l); }",
			state, null, function(interp) {
				@:privateAccess state.seedNightmareVision(interp, {scope:'smoke',name:'__splash_probe',path:'__splash_probe',relative:'__splash_probe'}, null);
				interp.variables.set('record', function(value:String) order.push(value));
				interp.variables.set('verifySpawn', function(s:NightmareVisionNoteSplash,d:Int,n:Note,p:Bool,l:Bool) {
					if (s.animation.curAnim == null || s.shader != s.colorSwap.shader || d != n.noteData || p != n.mustPress || l)
						throw 'Historical post-setup splash callback payload mismatch';
				});
			}, function(n,p,e) errors.push(p+': '+Std.string(e)));
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'pool'});
		if (module.callValue('poolCheck') != true) throw 'Historical global pool script/reflection identity mismatch';
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'constructors'});
		var direct:NightmareVisionNoteSplash = cast module.callValue('create');
		var reflected:NightmareVisionNoteSplash = cast module.callValue('reflected');
		if (direct == null || reflected == null || !direct.historical || !reflected.historical)
			throw 'Historical splash import/reflection constructor failed: '+errors.join(',');
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'configure'});
		module.callValue('configure',[direct]);
		if (direct.colorSwap.hue != 0.25 || direct.colorSwap.saturation != -0.2 || direct.colorSwap.lightness != 0.4
			|| direct.animation.curAnim == null || direct.textureLoaded != null)
			throw 'Native historical coordinate/HSL setup mismatch';
		var scripts = @:privateAccess state.nightmareVisionScripts;
		var originalSkin = state.noteskinScript;
		state.noteskinScript = module;
		scripts.group.addScript(module);
		var tap:Note = null;
		for (candidate in @:privateAccess state.unspawnNotes) if (candidate != null && !candidate.isSustainNote && candidate.noteData == 0) { tap = candidate; break; }
		if (tap == null) throw 'Native splash probe requires a tap note';
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'rating'});
		var oldRating = tap.rating;var oldRatingMod = tap.ratingMod;
		var judged = @:privateAccess state.judgeSourceNote(tap);
		if (tap.rating != judged.name || tap.ratingMod != judged.ratingMod) throw 'Native historical rating shape mismatch';
		tap.rating = oldRating;tap.ratingMod = oldRatingMod;
		var field:NightmareVisionPlayFieldView = cast note.playField;
		var previousField = tap.playField;tap.playField=field;
		var oldEnabled = field.noteSplashes;
		var prefs = @:privateAccess state.nightmareVisionPrefs.view;
		var oldPreference = prefs.noteSplashes;
		prefs.noteSplashes = true;field.noteSplashes = false;
		var previous = tap.noteSplash;
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'invoke'});
		module.callValue('invoke',[tap]);
		var spawned:NightmareVisionNoteSplash = null;
		for (sprite in state.grpNoteSplashes.members) if (Std.isOfType(sprite,NightmareVisionLegacyNoteSplash) && sprite.alive && sprite.alpha == 1) spawned = cast sprite;
		if (spawned == null || !spawned.historical || order.join(',') != 'skin,quants,spawn')
			throw 'Native historical spawn order mismatch: '+order.join(',');
		@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_probe_phase',{phase:'position'});
		var strum:Strumline.StrumNote = cast field.members[0];
		if (strum.parent != field || Math.abs(spawned.x-(strum.x+11-strum.swagWidth*.95))>0.00001
			|| Math.abs(spawned.y-(strum.y+13-strum.swagWidth*.95))>0.00001)
			throw 'Native historical splash offset or receptor parent mismatch';
		spawned.kill();tap.noteSplash = previous;tap.playField=previousField;field.noteSplashes=oldEnabled;prefs.noteSplashes=oldPreference;
		state.noteskinScript = originalSkin;scripts.group.removeScript(module);module.destroy();
		if (errors.length != 0) throw errors.join(',');
		for (splash in [direct,reflected]) {
			splash.active=false;splash.cameras=[state.camHUD];state.add(splash);
		}
		var frames=0;
		var window=Application.current.window;
		var listener:lime.graphics.RenderContext->Void=null;
		listener=function(_) {
			if (++frames<2) return;
			window.onRender.remove(listener);
			try {
				if (Reflect.field(direct.shader,'glProgram')==null || direct.graphic==null || direct.frames.frames.length==0)
					throw 'Historical native splash shader or atlas missing';
				var path=haxe.io.Path.withoutExtension(@:privateAccess RuntimeSmokeHarness.config().noteRenderPath)+'.splash.png';
				sys.io.File.saveBytes(path,window.readPixels().encode());
				@:privateAccess RuntimeSmokeHarness.emit('legacy_splash_native_verified', {constructors:2,coordinateSetup:true,
					publicSpawn:true,globalMembership:true,scriptPoolIdentity:true,historicalRating:true,modernFieldGatesIgnored:true,sourceHookOrder:order.join(','),hsl:true,frames:direct.frames.frames.length,graphic:direct.graphic.key,capture:path});
			} catch(error:Dynamic) { @:privateAccess RuntimeSmokeHarness.fail('legacy-splash-probe',Std.string(error)); }
			for (splash in [direct,reflected]) {state.remove(splash,true);splash.destroy();}
		};
		window.onRender.add(listener,false,-1001);
		#end
	}
}
