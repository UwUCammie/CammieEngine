package;

#if sys
import Discord.DiscordClient;
import flixel.FlxG;

/** Actual importer/binder/native save and RPC marshalling gate. RPC is kept
 * inside the smoke process, with no external Discord client connection. */
@:access(PlayState)
@:access(RuntimeSmokeHarness)
@:access(RuntimePsychAchievementsProbe)
@:access(DiscordClient)
class RuntimePsychStandardProbe {
	static var phase:Int = 0;
	static var iris:SourceIrisBridge;
	static var runtime:PsychRuntimeBindings;
	static var captured:Dynamic;
	static var previous:Dynamic;
	public static function enabled():Bool return Sys.getEnv('CAMMIE_PSYCH_STANDARD_SMOKE') == '1';
	public static function tick():Void {
		if (RuntimeSmokeHarness.finished) return;
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				var imported = RuntimePsychAchievementsProbe.resolvePublishedOwner();
				// Exercise the actual ready-state record without connecting the
				// isolated process to an external SDK client.
				DiscordClient.captureReadyPresence(DiscordClient.menuPresence());
				previous = DiscordClient.getRequestedSnapshot();
				check(previous.hasPresence, 'Native ready-state menu presence was not captured');
				var host = new PlayState(); host.cachedCompatScriptManifest = imported.manifest;
				host.initializePsychClientPrefs(imported.root);
				var paths = PsychOwnerPaths.create(imported.root);
				iris = new SourceIrisBridge(host);
				iris.variables.set('Paths', paths);
				iris.variables.set('ClientPrefs', host.psychClientPrefs);
				iris.variables.set('Reflect', Reflect);
				iris.variables.set('verify', check);
				iris.variables.set('captureMethod', function(value:Dynamic) captured = value);
				new PsychHscriptSourceBindings(host, iris, null, null).install();
				iris.evaluate("import backend.Language; import backend.DiscordClient;"
					+ "verify(Type.resolveClass('backend.Language') == Language, 'native Language class identity');"
					+ "verify(Language.getPhrase('Fixture phrase!', 'wrong', ['wizard']) == 'Hello wizard', 'native source language precedence and interpolation');"
					+ "verify(Language.getPhrase('Shared only') == 'shared layer', 'native shared language source');"
					+ "verify(Language.getFileTranslation(' IMAGES/FIXTURE.PNG ') == 'images/translated.png', 'native source file translation');"
					+ "captureMethod(Reflect.field(Language, 'getPhrase'));"
					+ "DiscordClient.changePresence('Native Psych', 'fixture', 'small', true, 5000, 'large');",
					'psych-standard-native.hx');
				var presence = DiscordClient.getRequestedSnapshot().presence;
				check(presence.details == 'Native Psych' && presence.state == 'fixture'
					&& presence.smallImageKey == 'small' && presence.largeImageKey == 'large'
					&& presence.largeImageText == 'Engine Version: 1.0.4'
					&& presence.endTimestamp - presence.startTimestamp == 5,
					'Native source RPC fields or timestamp units differ');
				var lua = new LuaCompatInterp(); lua.variables.set('Paths', paths); lua.variables.set('verify', check);
				runtime = new PsychRuntimeBindings(host, lua, null); runtime.install();
				var converted = LuaCompat.translate("verify(getTranslationPhrase('Fixture phrase!', 'wrong', {'caster'}) == 'Hello caster', 'native Lua language callback')\n"
					+ "verify(getFileTranslation('images/fixture.png') == 'images/translated.png', 'native Lua file callback')\n"
					+ "changeDiscordClientID()\n"
					+ "changeDiscordPresence('Lua Psych', 'lua', 'small-lua', false, 6000, 'large-lua')\n",
					'psych-standard-native.lua', true);
				check(converted.supported, 'Standard source Lua fixture failed translation');
				lua.execute(new hscript.Parser().parseString(converted.hscript));
				presence = DiscordClient.getRequestedSnapshot().presence;
				check(DiscordClient.getClientId() == '863222024192262205'
					&& presence.details == 'Lua Psych' && presence.startTimestamp == 0 && presence.endTimestamp == 6,
					'Lua source RPC defaults or nil identity reset differ');
				var scope = host.psychLuaNativeClassScope(paths);
				var languageType = scope.resolveClass('backend.Language');
				check(Reflect.callMethod(null, scope.read(languageType, 'getPhrase'), ['Fixture phrase!', 'bad', ['scope']]) == 'Hello scope',
					'Native reflected Language did not share the source runtime');
				iris.evaluate("ClientPrefs.data.language = 'fixture-alt'; Language.reloadPhrases();"
					+ "verify(Language.getPhrase('Fixture phrase!', 'bad', ['reader']) == 'Reloaded reader', 'explicit owner language reload');",
					'psych-standard-reload.hx');
				check(PsychStandardServices.languageFor(host, paths, null).getPhrase('Fixture phrase!', 'bad', ['same']) == 'Reloaded same',
					'Native language runtime was recreated per interpreter');
				phase = 1; FlxG.switchState(FreeplayState.new); return;
			}
			if (phase == 1) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				var released = false;
				try Reflect.callMethod(null, captured, ['Fixture phrase!']) catch (_:Dynamic) released = true;
				check(released, 'Captured Language method survived owner departure');
				var restored = DiscordClient.getRequestedSnapshot();
				check(restored.clientId == previous.clientId && restored.hasPresence == previous.hasPresence,
					'Native RPC identity/presence ownership did not restore');
				if (previous.hasPresence) check(haxe.Json.stringify(restored.presence) == haxe.Json.stringify(previous.presence),
					'Native RPC prior presence differs after release');
				runtime.release(); iris.release();
				RuntimeSmokeHarness.emit('psych_standard_verified', {hscript:true, lua:true, reflected:true,
					languageReload:true, rpcMarshalling:true, ownerCleanup:true, sourceGameplay:false});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('psych-standard-services', Std.string(error));
	}
	static function check(value:Bool, message:String):Void {if (!value) throw message;}
}
#end
