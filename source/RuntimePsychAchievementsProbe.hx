package;

#if sys
import flixel.FlxG;
import flixel.util.FlxSave;
import haxe.Json;
import lime.app.Application;
import sys.io.File;

/** Opt-in native component gate over an actually published Psych import.
 * It exercises the real host binding entry points without claiming gameplay
 * or the full source menu/Mods registry is covered by this fixture. */
@:access(PlayState)
@:access(RuntimeSmokeHarness)
@:access(flixel.FlxG)
@:access(PsychAchievementsRuntime)
@:access(PsychAchievementPopup)
class RuntimePsychAchievementsProbe {
	static var phase:Int = 0;
	static var host:PlayState;
	static var root:String;
	static var runtime:PsychAchievementsRuntime;
	static var iris:SourceIrisBridge;
	static var lua:LuaCompatInterp;
	static var sourceRuntime:PsychRuntimeBindings;
	static var capturedGetter:Dynamic;
	static var capturedPopups:Array<PsychAchievementPopup>;
	static var exitPopup:PsychAchievementPopup;
	static var began:Float;
	static var captureStarted:Bool = false;
	static var captured:Bool = false;
	static var rendered:Int = 0;

	public static function enabled():Bool return RuntimeSmokeHarness.enabled()
		&& Sys.getEnv('CAMMIE_PSYCH_ACHIEVEMENTS_SMOKE') == '1';
	static function check(ok:Bool, message:String):Void if (!ok) throw message;

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished) return;
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null,
					'Native achievements gate requires muted isolated saves');
				var imported = resolvePublishedOwner();
				root = imported.root;
				host = new PlayState();
				// Use the real chart's parsed compatibility receipt, not a fabricated
				// owner namespace. No gameplay create/update runs in this component.
				host.cachedCompatScriptManifest = imported.manifest;
				var paths = PsychOwnerPaths.create(root);
				iris = new SourceIrisBridge(host);
				iris.variables.set('Paths', paths);
				iris.variables.set('Reflect', Reflect);
				iris.variables.set('verify', check);
				iris.variables.set('captureGetter', function(value:Dynamic) capturedGetter = value);
				new PsychHscriptSourceBindings(host, iris, null, null).install();
				runtime = PsychAchievementsIntegration.runtimeFor(host, paths, null);
				check(runtime != null && runtime.service.exists('fixture_progress')
					&& runtime.service.exists('fixture_popup'), 'Published owner achievement JSON did not load');
				check(PsychAchievementsIntegration.runtimeFor(host, paths, null) == runtime,
					'Same-owner binding did not retain its runtime');
				lua = new LuaCompatInterp(); lua.variables.set('Paths', paths); lua.variables.set('verify', check);
				sourceRuntime = new PsychRuntimeBindings(host, lua, null); sourceRuntime.install();
				verifySynchronousContracts(paths);
				capturedPopups = runtime.popups.copy();
				check(capturedPopups.length == 2 && capturedPopups[0].intendedY == 170,
					'Native achievement popup stacking differs from source');
				PsychAchievementsRuntime.retainOwners([root]);
				FlxG.bitmap.clearCache();
				for (popup in capturedPopups) check(popup.iconGraphic != null && popup.iconGraphic.bitmap != null
					&& popup.iconGraphic.bitmap.width > 0, 'Same-owner cache clear disposed the popup icon');
				began = Sys.time(); phase = 1;
				return;
			}
			if (phase == 1) {
				check(FlxG.sound.muted, 'Achievement audio unmuted the native gate');
				if (!captureStarted && Sys.time() - began > 0.8) {
					captureStarted = true;
					Application.current.window.onRender.add(onRendered, false, -1000);
				}
				if (runtime.popupCount != 0 || !captured) return;
				for (popup in capturedPopups) checkPopupRetired(popup);
				check(!runtime.service.showingPopups, 'Completed popups remained in source showingPopups');
				runtime.service.startPopup('fixture_popup');
				check(runtime.popupCount == 1, 'Departure test popup was not created');
				exitPopup = runtime.popups[0];
				phase = 2; FlxG.switchState(FreeplayState.new); return;
			}
			if (phase == 2) {
				if (!Std.isOfType(FlxG.state, FreeplayState) || !runtime.released) return;
				checkPopupRetired(exitPopup);
				check(runtime.popupCount == 0, 'Unrelated state retained an owner popup');
				var rejected = false;
				try Reflect.callMethod(null, capturedGetter, ['fixture_progress']) catch (_:Dynamic) rejected = true;
				check(rejected, 'Captured achievement method survived owner release');
				var reloaded = PsychAchievementsIntegration.runtimeFor(host, PsychOwnerPaths.create(root), null);
				check(reloaded != runtime && reloaded.service.getScore('fixture_progress') == 3
					&& reloaded.service.isUnlocked('fixture_progress') && reloaded.service.isUnlocked('fixture_popup'),
					'Native private achievements did not reload their persisted map and unlocks');
				reloaded.release(); sourceRuntime.release(); iris.release();
				RuntimeSmokeHarness.emit('psych_achievements_verified', {hscript:true, lua:true,
					reflected:true, persistence:true, sameOwnerReuse:true, otherOwnerCleanup:true,
					popupLifecycle:true, owner:root, sourceGameplay:false});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('psych-achievements', Std.string(error));
	}

	static function verifySynchronousContracts(paths:Dynamic):Void {
		var original = FlxG.save;
		var counting = new RuntimePsychAchievementCountingSave(original);
		FlxG.save = counting;
		try {
			iris.evaluate("import backend.Achievements; var c = Type.resolveClass('backend.Achievements');"
				+ "verify(c == Achievements, 'source achievement class identity');"
				+ "verify(Reflect.fields(c).indexOf('getScore') >= 0, 'source achievement reflected fields');"
				+ "verify(Achievements.setScore('fixture_progress', 1.25, false) == 1.25, 'source fractional score');"
				+ "Achievements.save(); captureGetter(Reflect.field(c, 'getScore'));",
				'achievement-native-contract.hx');
			check(counting.flushes == 0, 'Source save(false) flushed its native owner backend');
			check(Reflect.isFunction(capturedGetter), 'Source reflected getter did not return a callable handle');
			var converted = LuaCompat.translate("verify(achievementExists('fixture_progress'), 'lua achievement exists')\n"
				+ "verify(addAchievementScore('fixture_progress', 0.75, false) == 2, 'lua shares source score')\n",
				'achievement-native-contract.lua', true);
			check(converted.supported, 'Achievement Lua fixture translation failed');
			lua.execute(new hscript.Parser().parseString(converted.hscript));
			check(counting.flushes == 0, 'Source Lua score(false) flushed its owner backend');
			iris.evaluate("verify(Achievements.setScore('fixture_progress', 3) == 3, 'source threshold score');",
				'achievement-native-threshold.hx');
			check(counting.flushes == 2, 'Source threshold did not preserve unlock and score flush boundaries');
			converted = LuaCompat.translate("verify(unlockAchievement('fixture_popup') == 'fixture_popup', 'lua unlock')\n"
				+ "verify(isAchievementUnlocked('fixture_progress'), 'lua unlock visibility')\n",
				'achievement-native-popup.lua', true);
			check(converted.supported, 'Achievement popup Lua fixture translation failed');
			lua.execute(new hscript.Parser().parseString(converted.hscript));
			check(counting.flushes == 3, 'Source Lua unlock did not flush once');
			var scope = host.psychLuaNativeClassScope(paths);
			var type = scope.resolveClass('backend.Achievements');
			var get = scope.read(type, 'getScore');
			check(Reflect.callMethod(null, get, ['fixture_progress']) == 3, 'Lua reflected class scope differs from HScript');
		} catch (error:Dynamic) {
			FlxG.save = original;
			throw error;
		}
		FlxG.save = original;
		counting.destroy();
	}

	static function resolvePublishedOwner():{root:String, manifest:CompatScriptManifest.CompatScriptManifestData} {
		var categories:Array<Dynamic> = cast FreeplayRegistry.getJson();
		for (category in categories) {
			var songs:Array<Dynamic> = cast Reflect.field(category, 'songs');
			if (songs == null) continue;
			for (row in songs) {
				var folder:String = Std.isOfType(row, String) ? cast row : Reflect.field(row, 'name');
				if (folder == null) continue;
				var root = ImportedModDiscovery.ownerForSong(folder, 'assets/data');
				if (PsychOwnerAssetPath.normalizeOwner(root) == '') continue;
				var path = root + '/data/achievements.json';
				if (!FNFAssets.exists(path)) continue;
				var records:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
				if (!Std.isOfType(records, Array)) continue;
				var keys = [for (record in (cast records:Array<Dynamic>)) Reflect.field(record, 'save')];
				if (!keys.contains('fixture_progress') || !keys.contains('fixture_popup')) continue;
				var manifest = CompatScriptManifest.parse(FNFAssets.getText('assets/data/' + folder + '/' + CompatScriptManifest.FILE_NAME));
				check(CompatScriptManifest.selectedRoot(manifest) == root, 'Registered song owner differs from its published receipt');
				var psych = false;
				for (entry in manifest.roots) if (entry.path == root && entry.engine == ImportEngine.PSYCH) psych = true;
				check(psych, 'Achievement fixture did not publish a Psych source owner');
				RuntimeSmokeHarness.emit('psych_achievements_import_verified', {owner:root, song:folder});
				return {root:root, manifest:manifest};
			}
		}
		throw 'No actually imported Psych achievement fixture in the registered library';
	}

	static function checkPopupRetired(popup:PsychAchievementPopup):Void {
		check(popup.destroyed && !popup.attached && !popup.listeningForResize
			&& !popup.listeningForFrame && popup.bitmaps == null && !FlxG.game.contains(popup),
			'Native achievement popup retained listeners, bitmaps or display membership');
	}
	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (RuntimeSmokeHarness.finished || ++rendered < 3) return;
		Application.current.window.onRender.remove(onRendered);
		try {
			var pixels = Application.current.window.readPixels(); check(pixels != null, 'Native popup framebuffer missing');
			File.saveBytes(Sys.getEnv('CAMMIE_PSYCH_ACHIEVEMENTS_CAPTURE') + '-popup.png', pixels.encode());
			captured = true;
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('psych-achievements-render', Std.string(error));
	}
}

/** Count the actual backend's explicit flush boundaries, forwarding to the
 * already isolated native save. The original FlxG.save is always restored. */
@:access(flixel.util.FlxSave)
private class RuntimePsychAchievementCountingSave extends FlxSave {
	public var flushes:Int = 0;
	final original:FlxSave;
	public function new(original:FlxSave) {super(); this.original = original; data = original.data;}
	override public function flush(minFileSize:Int = 0):Bool {flushes++; return original.flush(minFileSize);}
}
#end
