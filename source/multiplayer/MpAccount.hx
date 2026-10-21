package multiplayer;

import flixel.FlxG;
import haxe.Json;

/** What the account screen shows. */
enum MpAccountStatus {
	SignedOut;
	Starting;
	/** Waiting for the player to approve in the browser; the code is shown in game too. */
	Waiting(code:String, url:String);
	SignedIn(name:String);
	Failed(message:String);
}

typedef MpSavedSession = {
	var id:String;
	var secret:String;
	var name:String;
	var accountId:String;
}

/** The uwucammie.com account: browser-approved sign-in, the remembered game session
 * (in the save, never in options.json) and one-use tickets for each connection. The game
 * never sees the password; the session can be revoked from the website's Sessions list. */
class MpAccount {
	public static inline var HOST:String = 'uwucammie.com';
	public static inline var PROJECT:String = 'cammie-engine';
	static inline var SAVE_FIELD:String = 'uwucammieSession';

	public static var status(default, null):MpAccountStatus = SignedOut;
	static var deviceId:String = '';
	static var deviceSecret:String = '';
	static var pollEvery:Float = 2;
	static var pollAt:Float = 0;
	static var pollUntil:Float = 0;
	static var polling:Bool = false;
	static var clock:Float = 0;

	public static function session():Null<MpSavedSession> {
		var test = MpEndpoint.testSession();
		if (test != null)
			return test;
		var saved:Dynamic = Reflect.field(FlxG.save.data, SAVE_FIELD);
		if (saved == null || !Std.isOfType(saved.id, String) || !Std.isOfType(saved.secret, String))
			return null;
		return {id: saved.id, secret: saved.secret, name: Std.string(saved.name), accountId: Std.string(saved.accountId)};
	}

	public static function refreshStatus():Void {
		var saved = session();
		if (saved != null)
			status = SignedIn(saved.name);
		else if (!status.match(Waiting(_, _) | Starting))
			status = SignedOut;
	}

	public static function signOut():Void {
		Reflect.deleteField(FlxG.save.data, SAVE_FIELD);
		FlxG.save.flush();
		polling = false;
		status = SignedOut;
	}

	static function post(path:String, body:Dynamic):Dynamic {
		var response = MpNative.post(MpEndpoint.site(), path, Json.stringify(body));
		if (response.status < 0)
			throw 'Could not reach uwucammie.com (error ' + (-response.status) + ').';
		var data:Dynamic = null;
		try data = Json.parse(response.body) catch (_:Dynamic) {}
		if (response.status != 200 && response.status != 202) {
			var reason = data != null && Std.isOfType(data.error, String) ? data.error : 'HTTP ' + response.status;
			throw reason;
		}
		return data;
	}

	/** Start the browser sign-in. The verification page is opened in the system browser. */
	public static function beginSignIn():Void {
		if (!MpNative.available()) {
			status = Failed('Online play needs the Windows build.');
			return;
		}
		status = Starting;
		MpTasks.run(function() return post('/api/game-auth/start', {project: PROJECT, version: EngineBranding.version()}),
			function(result:Dynamic) {
				var url = Std.string(result.verification_uri);
				// Only the account page of this site is ever opened.
				if (!StringTools.startsWith(url, 'https://' + HOST + '/account/?device=')) {
					status = Failed('The sign-in page address was not expected.');
					return;
				}
				deviceId = result.device_id;
				deviceSecret = result.device_secret;
				pollEvery = Math.max(1, Std.parseFloat(Std.string(result.interval)));
				var lifetime = Std.parseFloat(Std.string(result.expires_in));
				status = Waiting(result.user_code, url);
				clock = 0;
				pollAt = pollEvery;
				pollUntil = Math.isNaN(lifetime) ? 600 : lifetime;
				polling = true;
				FlxG.openURL(url);
				MpTasks.every(tick);
			}, function(error) status = Failed(error));
	}

	static var inFlight:Bool = false;

	static function tick():Void {
		if (!polling) {
			MpTasks.stop(tick);
			return;
		}
		clock += FlxG.elapsed;
		if (clock >= pollUntil) {
			polling = false;
			status = Failed('The sign-in code expired. Try again.');
			return;
		}
		if (inFlight || clock < pollAt)
			return;
		inFlight = true;
		pollAt = clock + pollEvery;
		MpTasks.run(function() return post('/api/game-auth/poll', {device_id: deviceId, device_secret: deviceSecret}),
			function(result:Dynamic) {
				inFlight = false;
				if (!polling || result == null || result.status != 'approved')
					return;
				polling = false;
				Reflect.setField(FlxG.save.data, SAVE_FIELD, {id: result.session_id, secret: result.session_secret,
					name: result.name, accountId: result.account_id});
				FlxG.save.flush();
				status = SignedIn(result.name);
			}, function(error) {
				inFlight = false;
				polling = false;
				status = Failed(error);
			});
	}

	/** Ask for a one-use connection ticket. `failed` gets "session_revoked" when the player must sign in again. */
	public static function ticket(done:{ticket:String, secret:String, name:String, accountId:String}->Void, failed:String->Void):Void {
		var saved = session();
		if (saved == null) {
			failed('signin_required');
			return;
		}
		MpTasks.run(function() return post('/api/game-auth/resume', {project: PROJECT, version: EngineBranding.version(),
			session_id: saved.id, session_secret: saved.secret}),
			function(result:Dynamic) done({ticket: result.ticket, secret: result.secret, name: result.name, accountId: result.account_id}),
			function(error) {
				if (error == 'session_revoked')
					signOut();
				failed(error);
			});
	}
}
