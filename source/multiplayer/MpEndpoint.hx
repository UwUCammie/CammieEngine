package multiplayer;

/**
	Where the account API and the multiplayer socket live: uwucammie.com and
	play.uwucammie.com over TLS.

	CAMMIE_MP_ENDPOINT=http://127.0.0.1:<port> points both at a local test server instead
	(tools/mp_local_server.py). Only loopback addresses are accepted, so the variable can
	never send a session to another machine.
**/
class MpEndpoint {
	public var host(default, null):String;
	public var port(default, null):Int;
	public var secure(default, null):Bool;

	public function new(host:String, port:Int, secure:Bool) {
		this.host = host;
		this.port = port;
		this.secure = secure;
	}

	public static function site():MpEndpoint {
		var local = loopback();
		return local != null ? local : new MpEndpoint('uwucammie.com', 443, true);
	}

	public static function play():MpEndpoint {
		var local = loopback();
		return local != null ? local : new MpEndpoint('play.uwucammie.com', 443, true);
	}

	/** The local test server from CAMMIE_MP_ENDPOINT, or null. */
	public static function loopback():Null<MpEndpoint> {
		#if sys
		return parse(Sys.getEnv('CAMMIE_MP_ENDPOINT'));
		#else
		return null;
		#end
	}

	/** A game session given to a local test run (CAMMIE_MP_TEST_SESSION), never used with the real servers. */
	public static function testSession():Null<{id:String, secret:String, name:String, accountId:String}> {
		#if sys
		if (loopback() == null)
			return null;
		var raw = Sys.getEnv('CAMMIE_MP_TEST_SESSION');
		if (raw == null || raw == '')
			return null;
		try {
			var data:Dynamic = haxe.Json.parse(raw);
			return {id: Std.string(data.id), secret: Std.string(data.secret), name: Std.string(data.name), accountId: Std.string(data.accountId)};
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	/** The lobby code a local test run joins and readies in by itself (CAMMIE_MP_SMOKE_JOIN). */
	public static function testJoinCode():Null<String> {
		#if sys
		if (loopback() == null)
			return null;
		var code = Sys.getEnv('CAMMIE_MP_SMOKE_JOIN');
		return code == null || code == '' ? null : code;
		#else
		return null;
		#end
	}

	public static function parse(value:Null<String>):Null<MpEndpoint> {
		if (value == null)
			return null;
		var pattern = ~/^http:\/\/(127\.0\.0\.1|localhost|\[::1\]):([0-9]{1,5})\/?$/;
		if (!pattern.match(StringTools.trim(value)))
			return null;
		var port = Std.parseInt(pattern.matched(2));
		if (port == null || port < 1 || port > 65535)
			return null;
		var host = pattern.matched(1);
		return new MpEndpoint(host == '[::1]' ? '::1' : host, port, false);
	}
}
